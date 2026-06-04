from __future__ import annotations

from functools import lru_cache
import json
from typing import Any

from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.exceptions import AppException, NotFoundException
from src.models.document_relation import DocumentRelation
from src.services.legal_metadata_parser_service import legal_metadata_parser_service
from src.services.legal_semantic_graph_service import legal_semantic_graph_service


class Neo4jGraphUnavailable(AppException):
    pass


class Neo4jGraphService:
    def is_configured(self) -> bool:
        return bool(settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password)

    def is_enabled(self) -> bool:
        return settings.graph_backend == "neo4j"

    def is_available(self) -> bool:
        if not self.is_configured():
            return False
        try:
            self._driver()
        except Exception:
            return False
        return True

    def get_document_graph(self, db: Session, document_id: int, *, depth: int = 1) -> dict[str, Any]:
        self._ensure_neo4j_ready()
        max_depth = max(1, min(depth, 3))
        driver = self._driver()
        with driver.session(database=settings.neo4j_database) as session:
            root = session.run(
                """
                MATCH (d:Document {document_id: $document_id})
                RETURN d.document_id AS document_id
                """,
                document_id=document_id,
            ).single()
            if root is None:
                raise NotFoundException("Document not found")

            node_rows = session.run(
                f"""
                MATCH (root:Document {{document_id: $document_id}})
                MATCH path=(root)-[:RELATES_TO*0..{max_depth}]-(d:Document)
                WITH d, min(length(path)) AS distance
                RETURN DISTINCT
                    d.document_id AS document_id,
                    d.title AS title,
                    d.document_code AS document_code,
                    d.document_type AS document_type,
                    d.legal_status AS legal_status,
                    distance AS distance
                ORDER BY d.document_id
                """,
                document_id=document_id,
            ).data()

            document_ids = [int(row["document_id"]) for row in node_rows]
            distances = {int(row["document_id"]): int(row.get("distance") or 0) for row in node_rows}
            edge_rows = []
            provision_rows = []
            if document_ids:
                edge_rows = session.run(
                    """
                    MATCH (source:Document)-[r:RELATES_TO]->(target:Document)
                    WHERE source.document_id IN $document_ids AND target.document_id IN $document_ids
                    RETURN
                        source.document_id AS source_document_id,
                        target.document_id AS target_document_id,
                        r.relation_id AS relation_id,
                        r.relation_type AS relation_type,
                        r.relation_label AS relation_label,
                        r.legal_basis AS legal_basis,
                        r.confidence_score AS confidence_score
                    ORDER BY source.document_id, target.document_id, r.relation_type
                    """,
                    document_ids=document_ids,
                ).data()
                provision_rows = session.run(
                    """
                    MATCH (source:Provision)-[r:PROVISION_RELATES_TO]->(target:Provision)
                    WHERE source.document_id IN $document_ids AND target.document_id IN $document_ids
                    RETURN
                        source.document_id AS source_document_id,
                        target.document_id AS target_document_id,
                        source.provision_id AS source_provision_id,
                        target.provision_id AS target_provision_id,
                        r.relation_id AS relation_id,
                        r.relation_type AS relation_type,
                        r.relation_label AS relation_label,
                        r.confidence_score AS confidence_score,
                        r.extraction_method AS extraction_method
                    ORDER BY source.document_id, target.document_id, r.relation_id
                    """,
                    document_ids=document_ids,
                ).data()

        allowed_edge_rows = [
            item
            for item in edge_rows
            if min(
                distances.get(int(item["source_document_id"]), max_depth + 1),
                distances.get(int(item["target_document_id"]), max_depth + 1),
            )
            < max_depth
        ]

        provision_relations_by_pair: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for item in provision_rows:
            pair_key = (int(item["source_document_id"]), int(item["target_document_id"]))
            provision_relations_by_pair.setdefault(pair_key, []).append(item)

        nodes = [
            {
                "id": f"document:{int(item['document_id'])}",
                "document_id": int(item["document_id"]),
                "label": item.get("document_code") or item.get("title") or f"Document {item['document_id']}",
                "title": item.get("title"),
                "document_code": item.get("document_code"),
                "document_type": item.get("document_type"),
                "legal_status": item.get("legal_status"),
                "ocr_quality_score": None,
                "ocr_quality_label": None,
                "is_root": int(item["document_id"]) == document_id,
            }
            for item in node_rows
        ]

        edges = []
        relation_metadata_by_id: dict[int, dict[str, Any]] = {}
        if db is not None:
            relation_ids = [int(item["relation_id"]) for item in allowed_edge_rows if item.get("relation_id") is not None]
            if relation_ids:
                relation_rows = (
                    db.query(DocumentRelation)
                    .filter(DocumentRelation.id.in_(relation_ids))
                    .all()
                )
                for relation in relation_rows:
                    metadata_payload: dict[str, Any] = {}
                    if relation.metadata_json:
                        try:
                            parsed_metadata = json.loads(relation.metadata_json)
                            if isinstance(parsed_metadata, dict):
                                metadata_payload = parsed_metadata
                        except json.JSONDecodeError:
                            metadata_payload = {}
                    relation_metadata_by_id[relation.id] = metadata_payload

        for item in allowed_edge_rows:
            source_id = int(item["source_document_id"])
            target_id = int(item["target_document_id"])
            related_provisions = provision_relations_by_pair.get((source_id, target_id), [])
            relation_id = int(item["relation_id"])
            metadata_payload = relation_metadata_by_id.get(relation_id, {})
            evidence = metadata_payload.get("evidence", {}) if isinstance(metadata_payload.get("evidence"), dict) else {}
            edges.append(
                {
                    "id": f"relation:{relation_id}",
                    "source": source_id,
                    "target": target_id,
                    "relation_type": item["relation_type"],
                    "relation_label": item.get("relation_label"),
                    "confidence_score": float(item["confidence_score"]) if item.get("confidence_score") is not None else None,
                    "legal_basis": item.get("legal_basis"),
                    "metadata_json": json.dumps(metadata_payload, ensure_ascii=False) if metadata_payload else None,
                    "target_anchor": evidence.get("target_anchor"),
                    "target_excerpt": evidence.get("target_excerpt"),
                    "provision_relation_count": len(related_provisions),
                    "provision_relation_types": sorted({str(rel["relation_type"]) for rel in related_provisions}),
                    "provision_relation_samples": [
                        {
                            "id": int(rel["relation_id"]),
                            "relation_type": rel["relation_type"],
                            "relation_label": rel.get("relation_label"),
                            "source_provision_id": int(rel["source_provision_id"]),
                            "target_provision_id": int(rel["target_provision_id"]),
                            "source_excerpt": None,
                            "target_excerpt": None,
                            "confidence_score": float(rel["confidence_score"]) if rel.get("confidence_score") is not None else None,
                            "extraction_method": rel.get("extraction_method"),
                            "metadata_json": None,
                        }
                        for rel in related_provisions[:5]
                    ],
                }
            )

        return {
            "graph_type": "document_relations",
            "root_document_id": document_id,
            "depth": max_depth,
            "nodes": sorted(nodes, key=lambda item: (not item["is_root"], item["document_id"])),
            "edges": sorted(edges, key=lambda item: (item["source"], item["target"], item["relation_type"])),
        }

    def get_concept_graph(self, db: Session, concept_id: int, *, depth: int = 2) -> dict[str, Any]:
        self._ensure_neo4j_ready()
        return self._build_concept_graph(concept_ids=[concept_id], depth=depth, query=None)

    def explain_query(self, db: Session, query: str, *, depth: int = 2) -> dict[str, Any]:
        self._ensure_neo4j_ready()
        matched = self._match_concepts_via_neo4j(query, limit=8)
        if not matched:
            matched = legal_semantic_graph_service.match_concepts(db, query)
        if not matched:
            return {
                "graph_type": "legal_semantic_graph",
                "query": query,
                "depth": max(1, min(depth, 4)),
                "root_concept_id": None,
                "nodes": [],
                "edges": [],
                "anchors": [],
                "matched_concepts": [],
            }

        graph = self._build_concept_graph(
            concept_ids=[int(item["concept"].id) for item in matched],
            depth=depth,
            query=query,
        )
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

    def backend_overview(self) -> dict[str, Any]:
        return {
            "provider": "neo4j",
            "configured": self.is_configured(),
            "enabled": self.is_enabled(),
            "available": self.is_available(),
            "database": settings.neo4j_database,
            "sync_enabled": settings.neo4j_sync_enabled,
        }

    def _ensure_neo4j_ready(self) -> None:
        if not self.is_configured():
            raise Neo4jGraphUnavailable("Neo4j is not configured. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD first.")
        self._driver()

    @lru_cache(maxsize=1)
    def _driver(self):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise Neo4jGraphUnavailable("Neo4j Python driver is not installed. Add `neo4j` to backend dependencies.") from exc
        driver_uri = self._normalize_driver_uri(settings.neo4j_uri or "")
        return GraphDatabase.driver(driver_uri, auth=(settings.neo4j_user, settings.neo4j_password))

    def _normalize_driver_uri(self, uri: str) -> str:
        if not settings.neo4j_trust_all_certificates:
            return uri
        if uri.startswith("neo4j+s://"):
            return "neo4j+ssc://" + uri.removeprefix("neo4j+s://")
        if uri.startswith("bolt+s://"):
            return "bolt+ssc://" + uri.removeprefix("bolt+s://")
        return uri

    def _build_concept_graph(self, *, concept_ids: list[int], depth: int, query: str | None) -> dict[str, Any]:
        max_depth = max(1, min(depth, 4))
        root_ids = sorted(set(int(item) for item in concept_ids))
        if not root_ids:
            return {
                "graph_type": "legal_semantic_graph",
                "query": query,
                "depth": max_depth,
                "root_concept_id": None,
                "nodes": [],
                "edges": [],
                "anchors": [],
            }

        driver = self._driver()
        with driver.session(database=settings.neo4j_database) as session:
            root_rows = session.run(
                """
                MATCH (c:Concept)
                WHERE c.concept_id IN $concept_ids
                RETURN c.concept_id AS concept_id
                ORDER BY c.concept_id
                """,
                concept_ids=root_ids,
            ).data()
            found_root_ids = [int(item["concept_id"]) for item in root_rows]
            if not found_root_ids:
                raise NotFoundException("Legal concept not found")

            node_rows = session.run(
                f"""
                MATCH (root:Concept)
                WHERE root.concept_id IN $concept_ids
                MATCH path=(root)-[:SEMANTIC_RELATES_TO*0..{max_depth}]-(c:Concept)
                WITH c, min(length(path)) AS distance
                RETURN DISTINCT
                    c.concept_id AS concept_id,
                    c.slug AS slug,
                    c.canonical_name AS canonical_name,
                    c.concept_type AS concept_type,
                    c.legal_domain AS legal_domain,
                    c.description AS description,
                    c.is_seed AS is_seed,
                    distance AS distance
                ORDER BY c.concept_id
                """,
                concept_ids=found_root_ids,
            ).data()
            concept_ids_in_graph = [int(item["concept_id"]) for item in node_rows]
            edge_rows = []
            anchor_rows = []
            if concept_ids_in_graph:
                edge_rows = session.run(
                    """
                    MATCH (source:Concept)-[r:SEMANTIC_RELATES_TO]->(target:Concept)
                    WHERE source.concept_id IN $concept_ids AND target.concept_id IN $concept_ids
                    RETURN
                        r.edge_id AS edge_id,
                        source.concept_id AS source_concept_id,
                        target.concept_id AS target_concept_id,
                        r.edge_type AS edge_type,
                        r.label AS label,
                        r.legal_effect AS legal_effect,
                        r.confidence_score AS confidence_score,
                        r.metadata_json AS metadata_json
                    ORDER BY source.concept_id, target.concept_id, r.edge_type
                    """,
                    concept_ids=concept_ids_in_graph,
                ).data()
                anchor_rows = session.run(
                    """
                    MATCH (d:Document)-[r:MENTIONS_CONCEPT]->(c:Concept)
                    WHERE c.concept_id IN $concept_ids
                    RETURN
                        r.anchor_id AS anchor_id,
                        c.concept_id AS concept_id,
                        d.document_id AS document_id,
                        r.chunk_id AS chunk_id,
                        r.relation_role AS relation_role,
                        r.confidence_score AS confidence_score,
                        d.title AS document_title,
                        d.document_code AS document_code,
                        d.legal_status AS legal_status,
                        r.metadata_json AS metadata_json
                    ORDER BY d.document_id, r.anchor_id
                    """,
                    concept_ids=concept_ids_in_graph,
                ).data()

        nodes = [
            {
                "id": f"concept:{int(item['concept_id'])}",
                "concept_id": int(item["concept_id"]),
                "slug": item["slug"],
                "label": item["canonical_name"],
                "concept_type": item["concept_type"],
                "legal_domain": item.get("legal_domain"),
                "description": item.get("description"),
                "is_root": int(item["concept_id"]) in found_root_ids,
            }
            for item in node_rows
        ]
        edges = [
            {
                "id": f"concept-edge:{int(item['edge_id'])}",
                "source": f"concept:{int(item['source_concept_id'])}",
                "target": f"concept:{int(item['target_concept_id'])}",
                "edge_type": item["edge_type"],
                "label": item.get("label"),
                "legal_effect": item.get("legal_effect"),
                "confidence_score": float(item["confidence_score"]) if item.get("confidence_score") is not None else None,
                "metadata_json": item.get("metadata_json"),
            }
            for item in edge_rows
        ]
        anchors = []
        for item in anchor_rows:
            metadata_payload = {}
            if item.get("metadata_json"):
                try:
                    parsed = json.loads(item["metadata_json"])
                    if isinstance(parsed, dict):
                        metadata_payload = parsed
                except json.JSONDecodeError:
                    metadata_payload = {}
            anchors.append(
                {
                    "id": f"anchor:{int(item['anchor_id'])}",
                    "concept_id": int(item["concept_id"]),
                    "document_id": int(item["document_id"]),
                    "chunk_id": int(item["chunk_id"]) if item.get("chunk_id") is not None else None,
                    "relation_role": item["relation_role"],
                    "confidence_score": float(item["confidence_score"]) if item.get("confidence_score") is not None else None,
                    "document_title": item.get("document_title"),
                    "document_code": item.get("document_code"),
                    "legal_status": item.get("legal_status"),
                    "citation_label": metadata_payload.get("citation_label"),
                    "metadata_json": item.get("metadata_json"),
                    "source_excerpt": metadata_payload.get("source_excerpt"),
                }
            )

        return {
            "graph_type": "legal_semantic_graph",
            "query": query,
            "depth": max_depth,
            "root_concept_id": found_root_ids[0] if len(found_root_ids) == 1 else None,
            "nodes": sorted(nodes, key=lambda item: (not item["is_root"], item["label"])),
            "edges": sorted(edges, key=lambda item: (item["source"], item["target"], item["edge_type"])),
            "anchors": anchors,
        }

    def _match_concepts_via_neo4j(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        normalized_query = legal_metadata_parser_service.normalize_search_text(query)
        if not normalized_query:
            return []

        driver = self._driver()
        with driver.session(database=settings.neo4j_database) as session:
            rows = session.run(
                """
                MATCH (c:Concept)
                WITH c,
                     CASE
                         WHEN c.canonical_name_normalized = $normalized_query THEN 1.0
                         WHEN any(alias IN coalesce(c.aliases_normalized, []) WHERE alias = $normalized_query) THEN 0.98
                         WHEN any(alias IN coalesce(c.aliases_normalized, []) WHERE $normalized_query CONTAINS alias) THEN 0.78
                         WHEN c.canonical_name_normalized IS NOT NULL AND $normalized_query CONTAINS c.canonical_name_normalized THEN 0.72
                         ELSE 0.0
                     END AS match_score,
                     CASE
                         WHEN c.canonical_name_normalized = $normalized_query THEN c.canonical_name
                         WHEN any(alias IN coalesce(c.aliases_normalized, []) WHERE alias = $normalized_query)
                             THEN coalesce(head(c.aliases), c.canonical_name)
                         WHEN any(alias IN coalesce(c.aliases_normalized, []) WHERE $normalized_query CONTAINS alias)
                             THEN coalesce(head(c.aliases), c.canonical_name)
                         ELSE c.canonical_name
                     END AS matched_alias
                WHERE match_score > 0
                RETURN
                    c.concept_id AS concept_id,
                    c.slug AS slug,
                    c.canonical_name AS canonical_name,
                    c.concept_type AS concept_type,
                    c.legal_domain AS legal_domain,
                    matched_alias AS matched_alias,
                    match_score AS match_score
                ORDER BY match_score DESC, c.canonical_name ASC
                LIMIT $limit
                """,
                normalized_query=normalized_query,
                limit=limit,
            ).data()

        return [
            {
                "concept": _SimpleConceptRecord(
                    concept_id=int(item["concept_id"]),
                    slug=item["slug"],
                    canonical_name=item["canonical_name"],
                    concept_type=item["concept_type"],
                    legal_domain=item.get("legal_domain"),
                ),
                "matched_alias": item.get("matched_alias") or item["canonical_name"],
                "match_score": round(float(item["match_score"]), 4),
            }
            for item in rows
        ]


neo4j_graph_service = Neo4jGraphService()


class _SimpleConceptRecord:
    def __init__(self, *, concept_id: int, slug: str, canonical_name: str, concept_type: str, legal_domain: str | None) -> None:
        self.id = concept_id
        self.slug = slug
        self.canonical_name = canonical_name
        self.concept_type = concept_type
        self.legal_domain = legal_domain
