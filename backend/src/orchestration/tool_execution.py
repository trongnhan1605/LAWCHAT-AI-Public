from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.document import Document
from src.services.legal_semantic_graph_service import legal_semantic_graph_service
from src.tools.get_related_articles import RelatedArticleResult, get_related_articles
from src.tools.resolve_conflict import ConflictResolutionResult, resolve_document_conflict
from src.tools.search_law import SearchLawResult, search_law


@dataclass(frozen=True)
class LegalToolExecutionResult:
    search_results: list[SearchLawResult]
    related_articles: list[RelatedArticleResult]
    evidence_documents: dict[int, Document]
    semantic_graph: dict[str, object]
    conflict_result: ConflictResolutionResult | None
    unresolved_conflict: bool


class LegalToolExecutor:
    def execute(
        self,
        db: Session,
        *,
        content: str,
        preferred_terms: list[str],
        legal_domain: str | None = None,
    ) -> LegalToolExecutionResult:
        search_results = search_law(db, content, limit=5, preferred_terms=preferred_terms, legal_domain=legal_domain, allow_unreviewed=True)
        related_articles = get_related_articles(db, search_results, limit=4)
        evidence_documents = self.load_evidence_documents(db, search_results)
        semantic_graph = legal_semantic_graph_service.explain_query(db, content, depth=3)
        conflict_result, unresolved_conflict = self.resolve_conflict(search_results, evidence_documents)
        return LegalToolExecutionResult(
            search_results=search_results,
            related_articles=related_articles,
            evidence_documents=evidence_documents,
            semantic_graph=semantic_graph,
            conflict_result=conflict_result,
            unresolved_conflict=unresolved_conflict,
        )

    def load_evidence_documents(self, db: Session, search_results: list[SearchLawResult]) -> dict[int, Document]:
        if not search_results:
            return {}
        document_ids = sorted({result.document_id for result in search_results})
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        return {document.id: document for document in documents}

    def resolve_conflict(
        self,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
    ) -> tuple[ConflictResolutionResult | None, bool]:
        if len(search_results) < 2:
            return None, False

        first_document = evidence_documents.get(search_results[0].document_id)
        second_document = evidence_documents.get(search_results[1].document_id)
        if first_document is None or second_document is None:
            return None, False

        conflict_result = resolve_document_conflict(first_document, second_document)
        return conflict_result, conflict_result.winner_document_id is None


legal_tool_executor = LegalToolExecutor()
