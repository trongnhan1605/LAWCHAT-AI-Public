from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation


@dataclass(frozen=True)
class DocumentQualityMetrics:
    chunk_count: int
    provision_count: int
    indexed_chunk_count: int
    document_relation_count: int
    provision_relation_count: int
    missing_document_relation_evidence_count: int
    missing_provision_relation_evidence_count: int


class CorpusQualityReportService:
    def build_report(self, db: Session, *, include_reviewed: bool = True) -> dict[str, object]:
        query = db.query(Document).order_by(Document.created_at.desc(), Document.id.desc())
        if not include_reviewed:
            query = query.filter(Document.metadata_review_status != "reviewed")
        documents = query.all()
        metrics_by_document = self._load_metrics(db, [document.id for document in documents])
        items = [self._build_document_item(document, metrics_by_document.get(document.id, self._empty_metrics())) for document in documents]

        risk_counts = Counter(str(item["risk_level"]) for item in items)
        review_counts = Counter(str(item["metadata_review_status"]) for item in items)
        issue_counts = Counter(issue for item in items for issue in item["issue_codes"])

        return {
            "summary": {
                "total_documents": len(items),
                "pending_review_documents": review_counts.get("pending_review", 0),
                "reviewed_documents": review_counts.get("reviewed", 0),
                "high_risk_documents": risk_counts.get("high", 0),
                "medium_risk_documents": risk_counts.get("medium", 0),
                "low_risk_documents": risk_counts.get("low", 0),
                "total_chunks": sum(int(item["chunk_count"]) for item in items),
                "total_provisions": sum(int(item["provision_count"]) for item in items),
                "total_document_relations": sum(int(item["document_relation_count"]) for item in items),
                "total_provision_relations": sum(int(item["provision_relation_count"]) for item in items),
                "relations_missing_evidence": sum(int(item["missing_relation_evidence_count"]) for item in items),
                "issue_counts": dict(sorted(issue_counts.items())),
            },
            "items": items,
        }

    def _load_metrics(self, db: Session, document_ids: list[int]) -> dict[int, DocumentQualityMetrics]:
        if not document_ids:
            return {}

        chunk_counts = self._count_by_document(db.query(DocumentChunk.document_id, func.count(DocumentChunk.id)).filter(DocumentChunk.document_id.in_(document_ids)).group_by(DocumentChunk.document_id).all())
        provision_counts = self._count_by_document(db.query(LegalProvision.document_id, func.count(LegalProvision.id)).filter(LegalProvision.document_id.in_(document_ids)).group_by(LegalProvision.document_id).all())
        indexed_counts = self._count_by_document(
            db.query(DocumentChunk.document_id, func.count(DocumentChunkVector.id))
            .join(DocumentChunkVector, DocumentChunkVector.chunk_id == DocumentChunk.id)
            .filter(DocumentChunk.document_id.in_(document_ids))
            .filter(DocumentChunkVector.embedding_status == "indexed")
            .group_by(DocumentChunk.document_id)
            .all()
        )
        document_relation_counts = self._count_by_document(
            db.query(DocumentRelation.source_document_id, func.count(DocumentRelation.id))
            .filter(DocumentRelation.source_document_id.in_(document_ids))
            .group_by(DocumentRelation.source_document_id)
            .all()
        )
        provision_relation_counts = self._count_by_document(
            db.query(ProvisionRelation.source_document_id, func.count(ProvisionRelation.id))
            .filter(ProvisionRelation.source_document_id.in_(document_ids))
            .group_by(ProvisionRelation.source_document_id)
            .all()
        )
        missing_document_relation_evidence = self._count_by_document(
            db.query(DocumentRelation.source_document_id, func.count(DocumentRelation.id))
            .filter(DocumentRelation.source_document_id.in_(document_ids))
            .filter((DocumentRelation.legal_basis.is_(None)) | (func.length(func.trim(DocumentRelation.legal_basis)) == 0))
            .group_by(DocumentRelation.source_document_id)
            .all()
        )
        missing_provision_relation_evidence = self._count_by_document(
            db.query(ProvisionRelation.source_document_id, func.count(ProvisionRelation.id))
            .filter(ProvisionRelation.source_document_id.in_(document_ids))
            .filter((ProvisionRelation.source_excerpt.is_(None)) | (func.length(func.trim(ProvisionRelation.source_excerpt)) == 0))
            .group_by(ProvisionRelation.source_document_id)
            .all()
        )

        return {
            document_id: DocumentQualityMetrics(
                chunk_count=chunk_counts.get(document_id, 0),
                provision_count=provision_counts.get(document_id, 0),
                indexed_chunk_count=indexed_counts.get(document_id, 0),
                document_relation_count=document_relation_counts.get(document_id, 0),
                provision_relation_count=provision_relation_counts.get(document_id, 0),
                missing_document_relation_evidence_count=missing_document_relation_evidence.get(document_id, 0),
                missing_provision_relation_evidence_count=missing_provision_relation_evidence.get(document_id, 0),
            )
            for document_id in document_ids
        }

    def _build_document_item(self, document: Document, metrics: DocumentQualityMetrics) -> dict[str, object]:
        issues: list[str] = []
        recommendations: list[str] = []

        if document.metadata_review_status != "reviewed":
            issues.append("metadata_pending_review")
            recommendations.append("Legal reviewer should verify metadata before using this document as ground truth.")
        if document.ingestion_quality_status == "blocked":
            issues.append("ingestion_blocked")
            recommendations.append("Do not use this document for RAG until extraction/OCR/chunking issues are fixed.")
        elif document.ingestion_quality_status == "review_required":
            issues.append("ingestion_review_required")
            recommendations.append("Review ingestion quality notes before promoting this document to verified retrieval.")
        if document.retrieval_visibility == "blocked":
            issues.append("retrieval_blocked")
        elif document.retrieval_visibility == "indexed_unreviewed":
            issues.append("retrieval_unreviewed")
        for field_name in ("document_code", "document_type", "authority_level", "issuing_authority", "legal_status"):
            if not getattr(document, field_name):
                issues.append(f"missing_{field_name}")
        if document.legal_status in {None, "unknown", "draft"}:
            issues.append("legal_status_not_authoritative")
        if metrics.chunk_count == 0:
            issues.append("no_chunks")
            recommendations.append("Re-ingest or inspect text extraction because no RAG chunks were produced.")
        if metrics.provision_count == 0:
            issues.append("no_structured_provisions")
            recommendations.append("Inspect parser diagnostics or run fallback parser for structure prelabel.")
        if metrics.chunk_count and metrics.provision_count and metrics.provision_count > metrics.chunk_count * 3:
            issues.append("provision_chunk_ratio_high")
            recommendations.append("Review chunking/provision parse quality; parser may be over-splitting clauses or points.")
        missing_relation_evidence = metrics.missing_document_relation_evidence_count + metrics.missing_provision_relation_evidence_count
        if missing_relation_evidence:
            issues.append("relation_missing_evidence")
            recommendations.append("Do not promote relation edges until evidence excerpt/legal basis is reviewed.")
        if self._document_code_year_mismatches_filename(document):
            issues.append("document_code_year_mismatch_filename")
            recommendations.append("Check whether AI/rule parser copied a cited document code instead of the current document code.")
        if document.ocr_quality_score is not None and float(document.ocr_quality_score) < 85:
            issues.append("low_ocr_quality")
            recommendations.append("Review OCR output before relying on citations.")

        risk_level = self._risk_level(issues)
        if not recommendations and issues:
            recommendations.append("Review issue codes before marking this document as reviewed.")
        if not recommendations:
            recommendations.append("No obvious quality issue detected by automated checks.")

        return {
            "document_id": document.id,
            "title": document.title,
            "file_name": document.file_name,
            "source_reference": document.source_reference,
            "storage_path": document.storage_path,
            "document_code": document.document_code,
            "document_type": document.document_type,
            "legal_domain": document.legal_domain,
            "authority_level": document.authority_level,
            "issuing_authority": document.issuing_authority,
            "signed_date": document.signed_date.isoformat() if document.signed_date else None,
            "effective_date": document.effective_date.isoformat() if document.effective_date else None,
            "expiry_date": document.expiry_date.isoformat() if document.expiry_date else None,
            "legal_status": document.legal_status,
            "metadata_review_status": document.metadata_review_status,
            "content_sha256": document.content_sha256,
            "source_identity": document.source_identity,
            "ingestion_quality_status": document.ingestion_quality_status,
            "ingestion_quality_notes": document.ingestion_quality_notes,
            "retrieval_visibility": document.retrieval_visibility,
            "ocr_quality_label": document.ocr_quality_label,
            "ocr_quality_score": float(document.ocr_quality_score) if document.ocr_quality_score is not None else None,
            "chunk_count": metrics.chunk_count,
            "provision_count": metrics.provision_count,
            "indexed_chunk_count": metrics.indexed_chunk_count,
            "document_relation_count": metrics.document_relation_count,
            "provision_relation_count": metrics.provision_relation_count,
            "missing_relation_evidence_count": missing_relation_evidence,
            "risk_level": risk_level,
            "issue_codes": issues,
            "recommendations": recommendations,
        }

    def _document_code_year_mismatches_filename(self, document: Document) -> bool:
        if not document.document_code:
            return False
        filename_years = set(re.findall(r"(19\d{2}|20\d{2})", Path(document.file_name).stem))
        code_years = set(re.findall(r"(19\d{2}|20\d{2})", document.document_code))
        return bool(filename_years and code_years and filename_years.isdisjoint(code_years))

    def _risk_level(self, issues: list[str]) -> str:
        high_risk = {"no_chunks", "relation_missing_evidence", "low_ocr_quality", "ingestion_blocked", "retrieval_blocked"}
        medium_risk = {"metadata_pending_review", "no_structured_provisions", "document_code_year_mismatch_filename", "legal_status_not_authoritative", "ingestion_review_required", "retrieval_unreviewed"}
        if any(issue in high_risk for issue in issues):
            return "high"
        if any(issue in medium_risk or issue.startswith("missing_") for issue in issues):
            return "medium"
        return "low"

    def _count_by_document(self, rows: list[tuple[int, int]]) -> dict[int, int]:
        return {int(document_id): int(count or 0) for document_id, count in rows}

    def _empty_metrics(self) -> DocumentQualityMetrics:
        return DocumentQualityMetrics(
            chunk_count=0,
            provision_count=0,
            indexed_chunk_count=0,
            document_relation_count=0,
            provision_relation_count=0,
            missing_document_relation_evidence_count=0,
            missing_provision_relation_evidence_count=0,
        )


corpus_quality_report_service = CorpusQualityReportService()
