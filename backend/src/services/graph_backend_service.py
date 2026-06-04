from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.config import settings
from src.services.graph_service import graph_service
from src.services.legal_semantic_graph_service import legal_semantic_graph_service
from src.services.neo4j_graph_service import neo4j_graph_service


class GraphBackendService:
    def get_document_graph(self, db: Session, document_id: int, *, depth: int = 1) -> dict[str, Any]:
        if settings.graph_backend == "neo4j":
            return neo4j_graph_service.get_document_graph(db, document_id, depth=depth)
        return graph_service.get_document_graph(db, document_id, depth=depth)

    def get_concept_graph(self, db: Session, concept_id: int, *, depth: int = 2) -> dict[str, Any]:
        if settings.graph_backend == "neo4j":
            return neo4j_graph_service.get_concept_graph(db, concept_id, depth=depth)
        return legal_semantic_graph_service.get_concept_graph(db, concept_id, depth=depth)

    def explain_query(self, db: Session, query: str, *, depth: int = 2) -> dict[str, Any]:
        if settings.graph_backend == "neo4j":
            return neo4j_graph_service.explain_query(db, query, depth=depth)
        return legal_semantic_graph_service.explain_query(db, query, depth=depth)

    def backend_overview(self) -> dict[str, Any]:
        relational = {
            "provider": "relational",
            "configured": True,
            "enabled": settings.graph_backend == "relational",
            "available": True,
            "sync_enabled": True,
        }
        neo4j = neo4j_graph_service.backend_overview()
        return {
            "default_backend": settings.graph_backend,
            "relational": relational,
            "neo4j": neo4j,
        }


graph_backend_service = GraphBackendService()
