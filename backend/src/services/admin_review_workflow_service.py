from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.models.validation_run import ValidationRun
from src.services.benchmark_history_service import benchmark_history_service


class AdminReviewWorkflowService:
    QUEUES = (
        "ocr_text_quality",
        "metadata_review",
        "provision_review",
        "relation_review",
        "validation_failures",
        "benchmark_failures",
    )

    def build_queues(self, db: Session, *, limit_per_queue: int = 20) -> dict[str, object]:
        queues = {
            "ocr_text_quality": self._ocr_text_quality_items(db, limit_per_queue),
            "metadata_review": self._metadata_review_items(db, limit_per_queue),
            "provision_review": self._provision_review_items(db, limit_per_queue),
            "relation_review": self._relation_review_items(db, limit_per_queue),
            "validation_failures": self._validation_failure_items(db, limit_per_queue),
            "benchmark_failures": benchmark_history_service.list_failure_items(limit=limit_per_queue),
        }
        return {
            "summary": {
                queue_name: {
                    "count": len(items),
                    "high": sum(1 for item in items if item["severity"] == "high"),
                    "medium": sum(1 for item in items if item["severity"] == "medium"),
                    "low": sum(1 for item in items if item["severity"] == "low"),
                }
                for queue_name, items in queues.items()
            },
            "queues": queues,
        }

    def _ocr_text_quality_items(self, db: Session, limit: int) -> list[dict[str, object]]:
        documents = (
            db.query(Document)
            .filter((Document.ingestion_quality_status == "blocked") | (Document.ocr_quality_score < 85))
            .order_by(Document.updated_at.desc(), Document.id.desc())
            .limit(limit)
            .all()
        )
        return [
            self._document_item(
                queue="ocr_text_quality",
                document=document,
                status=document.ingestion_quality_status,
                severity="high",
                detail=document.ingestion_quality_notes or f"OCR quality score={float(document.ocr_quality_score or 0)}",
                action="Review extraction/OCR output before allowing this document into verified retrieval.",
            )
            for document in documents
        ]

    def _metadata_review_items(self, db: Session, limit: int) -> list[dict[str, object]]:
        documents = (
            db.query(Document)
            .filter(Document.metadata_review_status != "reviewed")
            .order_by(Document.updated_at.desc(), Document.id.desc())
            .limit(limit)
            .all()
        )
        return [
            self._document_item(
                queue="metadata_review",
                document=document,
                status=document.metadata_review_status,
                severity="medium",
                detail="Document metadata has not been human reviewed.",
                action="Verify title, code, type, authority, effective date, legal status, and domain.",
            )
            for document in documents
        ]

    def _provision_review_items(self, db: Session, limit: int) -> list[dict[str, object]]:
        rows = (
            db.query(Document, func.count(LegalProvision.id).label("provision_count"))
            .outerjoin(LegalProvision, LegalProvision.document_id == Document.id)
            .filter(Document.is_active == True)
            .group_by(Document.id)
            .having(func.count(LegalProvision.id) == 0)
            .order_by(Document.updated_at.desc(), Document.id.desc())
            .limit(limit)
            .all()
        )
        return [
            self._document_item(
                queue="provision_review",
                document=document,
                status="needs_review",
                severity="medium",
                detail="No structured provisions were parsed for this document.",
                action="Inspect parser output and rerun deterministic/AI fallback parser before review.",
            )
            for document, _count in rows
        ]

    def _relation_review_items(self, db: Session, limit: int) -> list[dict[str, object]]:
        document_rows = (
            db.query(DocumentRelation)
            .filter((DocumentRelation.legal_basis.is_(None)) | (func.length(func.trim(DocumentRelation.legal_basis)) == 0))
            .order_by(DocumentRelation.updated_at.desc(), DocumentRelation.id.desc())
            .limit(limit)
            .all()
        )
        provision_rows = (
            db.query(ProvisionRelation)
            .filter((ProvisionRelation.source_excerpt.is_(None)) | (func.length(func.trim(ProvisionRelation.source_excerpt)) == 0))
            .order_by(ProvisionRelation.updated_at.desc(), ProvisionRelation.id.desc())
            .limit(max(limit - len(document_rows), 0))
            .all()
        )
        items: list[dict[str, object]] = [
            {
                "queue": "relation_review",
                "source_type": "document_relation",
                "source_id": str(relation.id),
                "title": f"Document relation {relation.relation_type}",
                "status": "needs_evidence",
                "severity": "high",
                "detail": "Document relation is missing legal_basis evidence.",
                "action": "Attach source excerpt/legal basis or reject the candidate relation.",
                "created_at": relation.created_at.isoformat() if relation.created_at else None,
            }
            for relation in document_rows
        ]
        items.extend(
            {
                "queue": "relation_review",
                "source_type": "provision_relation",
                "source_id": str(relation.id),
                "title": f"Provision relation {relation.relation_type}",
                "status": "needs_evidence",
                "severity": "high",
                "detail": "Provision relation is missing source_excerpt evidence.",
                "action": "Attach source excerpt/target excerpt or reject the candidate relation.",
                "created_at": relation.created_at.isoformat() if relation.created_at else None,
            }
            for relation in provision_rows
        )
        return items

    def _validation_failure_items(self, db: Session, limit: int) -> list[dict[str, object]]:
        validation_runs = (
            db.query(ValidationRun)
            .filter((ValidationRun.validation_status.in_(["needs_review", "failed"])) | (ValidationRun.escalation_recommended == True))
            .order_by(ValidationRun.updated_at.desc(), ValidationRun.id.desc())
            .limit(limit)
            .all()
        )
        items: list[dict[str, object]] = []
        for run in validation_runs:
            findings = self._load_findings(run.findings_json)
            items.append(
                {
                    "queue": "validation_failures",
                    "source_type": "validation_run",
                    "source_id": str(run.id),
                    "title": f"Validation run {run.id}",
                    "status": run.validation_status,
                    "severity": "high" if run.escalation_recommended else "medium",
                    "detail": "; ".join(findings[:2]) if findings else run.error_message or "Validation requires review.",
                    "action": "Open the legal case audit trail and resolve citation/status/conflict findings.",
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "case_id": run.case_id,
                }
            )
        return items

    def _document_item(
        self,
        *,
        queue: str,
        document: Document,
        status: str,
        severity: str,
        detail: str,
        action: str,
    ) -> dict[str, object]:
        return {
            "queue": queue,
            "source_type": "document",
            "source_id": str(document.id),
            "title": document.title,
            "status": status,
            "severity": severity,
            "detail": detail,
            "action": action,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "document_id": document.id,
        }

    def _load_findings(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(data, list):
            return [str(item) for item in data]
        return [str(data)]


admin_review_workflow_service = AdminReviewWorkflowService()
