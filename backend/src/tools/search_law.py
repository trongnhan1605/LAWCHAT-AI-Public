from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from src.retrieval.legal_retrieval import legal_retrieval_service
from src.services.knowledge_service import knowledge_service


@dataclass(frozen=True)
class SearchLawResult:
    document_id: int
    chunk_id: int | None
    document_title: str
    citation_label: str | None
    hierarchy_path: str | None
    legal_status: str | None
    source_reference: str | None
    score: int
    excerpt: str

    def to_dict(self) -> dict:
        return asdict(self)


def search_law(
    db: Session,
    query: str,
    *,
    limit: int = 5,
    preferred_terms: list[str] | None = None,
    legal_domain: str | None = None,
    allow_unreviewed: bool = False,
) -> list[SearchLawResult]:
    if allow_unreviewed:
        matches = legal_retrieval_service.search_chunks(db, query, limit=limit, preferred_terms=preferred_terms, legal_domain=legal_domain, allow_unreviewed=True)
    else:
        matches = legal_retrieval_service.search_chunks(db, query, limit=limit, preferred_terms=preferred_terms, legal_domain=legal_domain)
    results: list[SearchLawResult] = []
    for document, chunk, score in matches:
        compact_excerpt = " ".join(chunk.content.split())
        results.append(
            SearchLawResult(
                document_id=document.id,
                chunk_id=chunk.id,
                document_title=document.title,
                citation_label=chunk.citation_label,
                hierarchy_path=chunk.hierarchy_path,
                legal_status=document.legal_status,
                source_reference=document.source_reference,
                score=score,
                excerpt=compact_excerpt[:320].rstrip() + ("..." if len(compact_excerpt) > 320 else ""),
            )
        )
    return results
