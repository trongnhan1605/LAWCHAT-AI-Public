from __future__ import annotations

import json
from collections import deque

from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundException
from src.models.article_concept_link import ArticleConceptLink
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_concept import LegalConcept
from src.models.legal_concept_alias import LegalConceptAlias
from src.models.legal_concept_edge import LegalConceptEdge
from src.services.legal_metadata_parser_service import legal_metadata_parser_service


class LegalSemanticGraphService:
    def list_concepts(self, db: Session) -> list[LegalConcept]:
        return db.query(LegalConcept).filter(LegalConcept.is_active.is_(True)).order_by(LegalConcept.canonical_name.asc()).all()

    def get_concept_graph(self, db: Session, concept_id: int, *, depth: int = 2) -> dict[str, object]:
        root = db.query(LegalConcept).filter(LegalConcept.id == concept_id, LegalConcept.is_active.is_(True)).first()
        if root is None:
            raise NotFoundException("Legal concept not found")

        return self._build_semantic_graph(db, [root], depth=depth, query=None)

    def explain_query(self, db: Session, query: str, *, depth: int = 2) -> dict[str, object]:
        matched = self.match_concepts(db, query)
        matched_concepts = [item["concept"] for item in matched]
        graph = self._build_semantic_graph(db, matched_concepts, depth=depth, query=query)
        graph["matched_concepts"] = [
            {
                "concept_id": item["concept"].id,
                "slug": item["concept"].slug,
                "canonical_name": item["concept"].canonical_name,
                "concept_type": item["concept"].concept_type,
                "legal_domain": item["concept"].legal_domain,
                "matched_alias": item["matched_alias"],
                "match_score": item["match_score"],
            }
            for item in matched
        ]
        return graph

    def match_concepts(self, db: Session, query: str, *, limit: int = 8) -> list[dict[str, object]]:
        normalized_query = legal_metadata_parser_service.normalize_search_text(query)
        if not normalized_query:
            return []

        concepts = self.list_concepts(db)
        aliases = db.query(LegalConceptAlias).order_by(LegalConceptAlias.id.asc()).all()
        aliases_by_concept_id: dict[int, list[LegalConceptAlias]] = {}
        for alias in aliases:
            aliases_by_concept_id.setdefault(alias.concept_id, []).append(alias)

        matches: list[dict[str, object]] = []
        for concept in concepts:
            candidates = [concept.canonical_name]
            candidates.extend(alias.alias_text for alias in aliases_by_concept_id.get(concept.id, []))
            best_alias: str | None = None
            best_score = 0.0
            for candidate in candidates:
                normalized_candidate = legal_metadata_parser_service.normalize_search_text(candidate)
                if not normalized_candidate:
                    continue
                if normalized_candidate == normalized_query:
                    score = 1.0
                elif normalized_candidate in normalized_query:
                    score = min(0.98, 0.6 + (len(normalized_candidate) / max(len(normalized_query), 1)) * 0.4)
                elif all(token in normalized_query for token in normalized_candidate.split()):
                    score = 0.55
                else:
                    continue
                if score > best_score:
                    best_score = score
                    best_alias = candidate
            if best_alias is not None:
                matches.append(
                    {
                        "concept": concept,
                        "matched_alias": best_alias,
                        "match_score": round(best_score, 4),
                    }
                )

        matches.sort(key=lambda item: (-float(item["match_score"]), item["concept"].canonical_name))
        return matches[:limit]

    def _build_semantic_graph(
        self,
        db: Session,
        root_concepts: list[LegalConcept],
        *,
        depth: int,
        query: str | None,
    ) -> dict[str, object]:
        max_depth = max(1, min(depth, 4))
        root_ids = {concept.id for concept in root_concepts}
        concept_by_id: dict[int, LegalConcept] = {concept.id: concept for concept in root_concepts}
        queue = deque((concept.id, 0) for concept in root_concepts)
        visited = set(root_ids)
        edge_map: dict[tuple[int, int, str], dict[str, object]] = {}

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= max_depth:
                continue

            edges = (
                db.query(LegalConceptEdge)
                .filter(
                    LegalConceptEdge.is_active.is_(True),
                    (LegalConceptEdge.source_concept_id == current_id) | (LegalConceptEdge.target_concept_id == current_id),
                )
                .all()
            )
            for edge in edges:
                source_id = edge.source_concept_id
                target_id = edge.target_concept_id
                if source_id not in concept_by_id:
                    source_concept = db.query(LegalConcept).filter(LegalConcept.id == source_id).first()
                    if source_concept is not None:
                        concept_by_id[source_id] = source_concept
                if target_id not in concept_by_id:
                    target_concept = db.query(LegalConcept).filter(LegalConcept.id == target_id).first()
                    if target_concept is not None:
                        concept_by_id[target_id] = target_concept

                edge_key = (source_id, target_id, edge.edge_type)
                if edge_key not in edge_map:
                    edge_map[edge_key] = {
                        "id": f"concept-edge:{edge.id}",
                        "source": f"concept:{source_id}",
                        "target": f"concept:{target_id}",
                        "edge_type": edge.edge_type,
                        "label": edge.label,
                        "legal_effect": edge.legal_effect,
                        "confidence_score": float(edge.confidence_score) if edge.confidence_score is not None else None,
                        "metadata_json": edge.metadata_json,
                    }

                for next_id in (source_id, target_id):
                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, current_depth + 1))

        anchors = self._build_anchor_payloads(db, list(concept_by_id.keys()))
        nodes = [
            {
                "id": f"concept:{concept.id}",
                "concept_id": concept.id,
                "slug": concept.slug,
                "label": concept.canonical_name,
                "concept_type": concept.concept_type,
                "legal_domain": concept.legal_domain,
                "description": concept.description,
                "is_root": concept.id in root_ids,
            }
            for concept in concept_by_id.values()
        ]

        return {
            "graph_type": "legal_semantic_graph",
            "query": query,
            "depth": max_depth,
            "root_concept_id": root_concepts[0].id if len(root_concepts) == 1 else None,
            "nodes": sorted(nodes, key=lambda item: (not item["is_root"], item["label"])),
            "edges": sorted(edge_map.values(), key=lambda item: (item["source"], item["target"], item["edge_type"])),
            "anchors": anchors,
        }

    def _build_anchor_payloads(self, db: Session, concept_ids: list[int]) -> list[dict[str, object]]:
        if not concept_ids:
            return []

        links = (
            db.query(ArticleConceptLink)
            .filter(ArticleConceptLink.concept_id.in_(concept_ids), ArticleConceptLink.is_active.is_(True))
            .order_by(ArticleConceptLink.document_id.asc(), ArticleConceptLink.id.asc())
            .all()
        )
        anchors: list[dict[str, object]] = []
        for link in links:
            document = db.query(Document).filter(Document.id == link.document_id).first()
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == link.chunk_id).first() if link.chunk_id else None
            metadata_payload: dict[str, object] = {}
            if link.metadata_json:
                try:
                    parsed = json.loads(link.metadata_json)
                    if isinstance(parsed, dict):
                        metadata_payload = parsed
                except json.JSONDecodeError:
                    metadata_payload = {}
            anchors.append(
                {
                    "id": f"anchor:{link.id}",
                    "concept_id": link.concept_id,
                    "document_id": link.document_id,
                    "chunk_id": link.chunk_id,
                    "relation_role": link.relation_role,
                    "confidence_score": float(link.confidence_score) if link.confidence_score is not None else None,
                    "document_title": document.title if document is not None else None,
                    "document_code": document.document_code if document is not None else None,
                    "legal_status": document.legal_status if document is not None else None,
                    "citation_label": chunk.citation_label if chunk is not None else None,
                    "metadata_json": link.metadata_json,
                    "source_excerpt": metadata_payload.get("source_excerpt"),
                }
            )
        return anchors


legal_semantic_graph_service = LegalSemanticGraphService()