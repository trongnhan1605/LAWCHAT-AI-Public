from __future__ import annotations

from dataclasses import asdict, dataclass

from src.models.document import Document
from src.tools.check_validity import evaluate_document_validity
from src.tools.get_related_articles import RelatedArticleResult
from src.tools.search_law import SearchLawResult


@dataclass(frozen=True)
class ReasoningArtifact:
    issue_summary: str
    reasoning_graph: dict
    evidence_summary: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class LegalReasoningBuilder:
    def build_artifact(
        self,
        *,
        content: str,
        domain_name: str,
        domain_slug: str,
        intent: str,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        related_articles: list[RelatedArticleResult],
        conflict_result,
        semantic_graph: dict | None = None,
    ) -> ReasoningArtifact:
        issue_summary = f"Yêu cầu thuộc nhóm {domain_name}, intent {intent}: {content.strip()}"
        evidence_summary = self._build_evidence_summary(search_results, evidence_documents, related_articles, semantic_graph)
        reasoning_graph = self._build_reasoning_graph(
            domain_slug=domain_slug,
            intent=intent,
            search_results=search_results,
            related_articles=related_articles,
            conflict_result=conflict_result,
            semantic_graph=semantic_graph,
        )
        return ReasoningArtifact(
            issue_summary=issue_summary,
            reasoning_graph=reasoning_graph,
            evidence_summary=evidence_summary,
        )

    def _build_evidence_summary(
        self,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        related_articles: list[RelatedArticleResult],
        semantic_graph: dict | None,
    ) -> list[dict]:
        summary: list[dict] = []
        for result in search_results:
            document = evidence_documents.get(result.document_id)
            validity = evaluate_document_validity(document) if document is not None else None
            summary.append(
                {
                    "document_id": result.document_id,
                    "document_title": result.document_title,
                    "citation_label": result.citation_label,
                    "score": result.score,
                    "legal_status": result.legal_status,
                    "validity": validity.to_dict() if validity else None,
                }
            )

        if related_articles:
            summary.append(
                {
                    "related_articles": [item.to_dict() for item in related_articles],
                }
            )
        if semantic_graph:
            summary.append(
                {
                    "semantic_graph": {
                        "matched_concepts": semantic_graph.get("matched_concepts", []),
                        "edge_count": len(semantic_graph.get("edges", [])),
                        "anchor_count": len(semantic_graph.get("anchors", [])),
                    }
                }
            )
        return summary

    def _build_reasoning_graph(
        self,
        *,
        domain_slug: str,
        intent: str,
        search_results: list[SearchLawResult],
        related_articles: list[RelatedArticleResult],
        conflict_result,
        semantic_graph: dict | None,
    ) -> dict:
        nodes = [{"id": "issue", "type": "issue", "label": domain_slug}]
        edges: list[dict] = []

        for result in search_results[:3]:
            node_id = f"evidence:{result.document_id}:{result.chunk_id}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "evidence",
                    "label": result.citation_label or result.document_title,
                    "document_id": result.document_id,
                    "chunk_id": result.chunk_id,
                }
            )
            edges.append({"from": "issue", "to": node_id, "type": "SUPPORTED_BY"})

        for article in related_articles[:4]:
            node_id = f"related:{article.document_id}:{article.chunk_id}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "related_article",
                    "label": article.citation_label or article.document_title,
                    "document_id": article.document_id,
                    "chunk_id": article.chunk_id,
                }
            )
            edges.append({"from": "issue", "to": node_id, "type": article.relation_type.upper()})

        graph = {
            "domain": domain_slug,
            "intent": intent,
            "nodes": nodes,
            "edges": edges,
        }
        if semantic_graph:
            graph["semantic_path"] = {
                "matched_concepts": semantic_graph.get("matched_concepts", []),
                "nodes": semantic_graph.get("nodes", []),
                "edges": semantic_graph.get("edges", []),
                "anchors": semantic_graph.get("anchors", []),
            }
        if conflict_result is not None:
            graph["conflict_resolution"] = conflict_result.to_dict()
        return graph


legal_reasoning_builder = LegalReasoningBuilder()