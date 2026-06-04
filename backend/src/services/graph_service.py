from __future__ import annotations

import json
from collections import deque

from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundException
from src.models.document import Document
from src.models.document_relation import DocumentRelation
from src.models.legal_case import LegalCase
from src.models.provision_relation import ProvisionRelation
from src.models.reasoning_run import ReasoningRun


class GraphService:
    def get_document_graph(self, db: Session, document_id: int, *, depth: int = 1) -> dict:
        root_document = db.query(Document).filter(Document.id == document_id).first()
        if root_document is None:
            raise NotFoundException("Document not found")

        max_depth = max(1, min(depth, 3))
        visited = {document_id}
        queue = deque([(document_id, 0)])
        documents_by_id: dict[int, Document] = {document_id: root_document}
        edge_map: dict[tuple[int, int, str], dict] = {}

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= max_depth:
                continue

            relations = (
                db.query(DocumentRelation)
                .filter(
                    (DocumentRelation.source_document_id == current_id)
                    | (DocumentRelation.target_document_id == current_id)
                )
                .all()
            )

            for relation in relations:
                source_id = relation.source_document_id
                target_id = relation.target_document_id
                other_id = target_id if source_id == current_id else source_id
                metadata_payload: dict[str, object] = {}
                if relation.metadata_json:
                    try:
                        parsed_metadata = json.loads(relation.metadata_json)
                        if isinstance(parsed_metadata, dict):
                            metadata_payload = parsed_metadata
                    except json.JSONDecodeError:
                        metadata_payload = {}
                evidence = metadata_payload.get("evidence", {})
                if not isinstance(evidence, dict):
                    evidence = {}
                edge_key = (source_id, target_id, relation.relation_type)
                if edge_key not in edge_map:
                    edge_map[edge_key] = {
                        "id": f"relation:{relation.id}",
                        "source": source_id,
                        "target": target_id,
                        "relation_type": relation.relation_type,
                        "relation_label": relation.relation_label,
                        "confidence_score": float(relation.confidence_score) if relation.confidence_score is not None else None,
                        "legal_basis": relation.legal_basis,
                        "metadata_json": relation.metadata_json,
                        "target_anchor": evidence.get("target_anchor"),
                        "target_excerpt": evidence.get("target_excerpt"),
                        "provision_relation_count": 0,
                        "provision_relation_types": [],
                        "provision_relation_samples": [],
                    }

                if other_id not in documents_by_id:
                    document = db.query(Document).filter(Document.id == other_id).first()
                    if document is not None:
                        documents_by_id[other_id] = document

                if other_id not in visited:
                    visited.add(other_id)
                    queue.append((other_id, current_depth + 1))

        document_ids = list(documents_by_id.keys())
        provision_relations = (
            db.query(ProvisionRelation)
            .filter(
                ((ProvisionRelation.source_document_id.in_(document_ids)) & (ProvisionRelation.target_document_id.in_(document_ids)))
            )
            .filter(ProvisionRelation.is_active.is_(True))
            .order_by(ProvisionRelation.id.asc())
            .all()
        )
        provision_relations_by_pair: dict[tuple[int, int], list[ProvisionRelation]] = {}
        for provision_relation in provision_relations:
            pair_key = (provision_relation.source_document_id, provision_relation.target_document_id)
            provision_relations_by_pair.setdefault(pair_key, []).append(provision_relation)

        for edge_key, edge_payload in edge_map.items():
            source_id, target_id, _relation_type = edge_key
            related_provisions = provision_relations_by_pair.get((source_id, target_id), [])
            relation_types = sorted({item.relation_type for item in related_provisions})
            edge_payload["provision_relation_count"] = len(related_provisions)
            edge_payload["provision_relation_types"] = relation_types
            edge_payload["provision_relation_samples"] = [
                {
                    "id": item.id,
                    "relation_type": item.relation_type,
                    "relation_label": item.relation_label,
                    "source_provision_id": item.source_provision_id,
                    "target_provision_id": item.target_provision_id,
                    "source_excerpt": item.source_excerpt,
                    "target_excerpt": item.target_excerpt,
                    "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                    "extraction_method": item.extraction_method,
                    "metadata_json": item.metadata_json,
                }
                for item in related_provisions[:5]
            ]

        nodes = [
            {
                "id": f"document:{document.id}",
                "document_id": document.id,
                "label": document.document_code or document.title,
                "title": document.title,
                "document_code": document.document_code,
                "document_type": document.document_type,
                "legal_status": document.legal_status,
                "ocr_quality_score": float(document.ocr_quality_score) if document.ocr_quality_score is not None else None,
                "ocr_quality_label": document.ocr_quality_label,
                "is_root": document.id == document_id,
            }
            for document in documents_by_id.values()
        ]
        edges = list(edge_map.values())

        return {
            "graph_type": "document_relations",
            "root_document_id": document_id,
            "depth": max_depth,
            "nodes": sorted(nodes, key=lambda item: (not item["is_root"], item["document_id"])),
            "edges": sorted(edges, key=lambda item: (item["source"], item["target"], item["relation_type"])),
        }

    def get_case_reasoning_graph(self, db: Session, case_id: int) -> dict:
        legal_case = db.query(LegalCase).filter(LegalCase.id == case_id).first()
        if legal_case is None:
            raise NotFoundException("Legal case not found")

        reasoning_run = (
            db.query(ReasoningRun)
            .filter(ReasoningRun.case_id == case_id)
            .order_by(ReasoningRun.updated_at.desc(), ReasoningRun.id.desc())
            .first()
        )
        if reasoning_run is None or not reasoning_run.reasoning_graph_json:
            return {
                "graph_type": "reasoning",
                "case_id": case_id,
                "case_title": legal_case.title,
                "nodes": [],
                "edges": [],
                "status": "empty",
            }

        try:
            parsed = json.loads(reasoning_run.reasoning_graph_json)
        except json.JSONDecodeError:
            return {
                "graph_type": "reasoning",
                "case_id": case_id,
                "case_title": legal_case.title,
                "nodes": [],
                "edges": [],
                "status": "invalid_json",
            }

        if not isinstance(parsed, dict):
            parsed = {}

        return {
            "graph_type": "reasoning",
            "case_id": case_id,
            "case_title": legal_case.title,
            "reasoning_run_id": reasoning_run.id,
            "status": "ready",
            "nodes": parsed.get("nodes", []),
            "edges": parsed.get("edges", []),
            "conflict_resolution": parsed.get("conflict_resolution"),
            "domain": parsed.get("domain"),
            "intent": parsed.get("intent"),
        }


graph_service = GraphService()
