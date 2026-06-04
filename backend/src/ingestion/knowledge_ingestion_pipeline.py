from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundException, ValidationException
from src.core.logging import logger
from src.models.citation import Citation
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.ingestion.legal_chunk_builder import legal_chunk_builder
from src.services.document_relation_service import document_relation_service
from src.services.embedding_service import embedding_service
from src.services.ocr_service import ocr_service
from src.services.provision_relation_service import provision_relation_service


@dataclass(frozen=True)
class IngestionResult:
    document: Document
    extracted_character_count: int
    chunk_count: int


class KnowledgeIngestionPipeline:
    def ingest_document(
        self,
        db: Session,
        *,
        document: Document,
        knowledge_service,
        extracted_text_override: str | None = None,
    ) -> IngestionResult:
        source_path = Path(document.storage_path)
        if not source_path.exists():
            raise NotFoundException("Document source file not found on disk")

        extracted_segments, ocr_used, ocr_average_confidence = self._extract_segments_for_ingestion(
            document=document,
            source_path=source_path,
            knowledge_service=knowledge_service,
            extracted_text_override=extracted_text_override,
        )
        extracted_text = "\n".join(extracted_segments)
        if not extracted_text.strip():
            raise ValidationException("Document extraction produced no usable text. This source likely needs OCR or a text-based alternative file")

        knowledge_service._apply_inferred_document_metadata(document, extracted_segments)
        chunk_payloads = legal_chunk_builder.build_chunk_payloads(extracted_segments)
        created_chunks = self._replace_document_chunks(db, document=document, chunk_payloads=chunk_payloads)

        document.summary = knowledge_service._build_summary(extracted_text)
        self._apply_ocr_quality(
            document=document,
            knowledge_service=knowledge_service,
            extracted_segments=extracted_segments,
            chunk_payloads=chunk_payloads,
            ocr_average_confidence=ocr_average_confidence,
            ocr_used=ocr_used,
            override_text=bool((extracted_text_override or "").strip()),
        )
        db.flush()

        provision_count, provision_parser_source = knowledge_service._sync_document_provisions_with_fallback(db, document, extracted_text)
        self._apply_ingestion_quality_gate(
            document=document,
            extracted_text=extracted_text,
            chunk_count=len(chunk_payloads),
            provision_count=provision_count,
            provision_parser_source=provision_parser_source,
        )
        self._index_embeddings(db=db, document=document, created_chunks=created_chunks, provision_count=provision_count, provision_parser_source=provision_parser_source)
        self.sync_relations(db, document=document)

        db.commit()
        db.refresh(document)
        return IngestionResult(document=document, extracted_character_count=len(extracted_text), chunk_count=len(chunk_payloads))

    def refresh_document_metadata_and_relations(self, db: Session, *, document: Document, knowledge_service) -> Document:
        source_path = Path(document.storage_path)
        if not source_path.exists():
            raise NotFoundException("Document source file not found on disk")

        extracted_segments = knowledge_service._extract_segments(document.source_type, source_path)
        if not any(segment.strip() for segment in extracted_segments) and document.source_type == "pdf":
            ocr_result = self._ocr_service().diagnose_pdf(source_path)
            extracted_segments = [item.text.strip() for item in ocr_result.page_results or [] if item.text.strip()]
        if not extracted_segments:
            raise ValidationException("Document extraction produced no usable text for metadata refresh")

        extracted_text = "\n".join(segment.strip() for segment in extracted_segments if segment.strip())
        knowledge_service._apply_inferred_document_metadata(document, extracted_segments)
        provision_count, provision_parser_source = knowledge_service._sync_document_provisions_with_fallback(db, document, extracted_text)
        self._document_relation_service().sync_document_relations(db, document.id)
        self._provision_relation_service().sync_document_relations(db, document.id)
        if provision_count == 0:
            logger.info("Document %s refresh completed without structured legal provisions", document.id)
        elif provision_parser_source == "ai_fallback":
            logger.info("Document %s refresh used AI fallback legal structure parser", document.id)
        db.commit()
        db.refresh(document)
        return document

    def sync_relations(self, db: Session, *, document: Document) -> None:
        try:
            self._document_relation_service().sync_document_relations(db, document.id)
        except Exception as exc:  # pragma: no cover - defensive workflow guard
            logger.warning("Document %s ingested but relation sync failed: %s", document.id, exc)
            self._document_relation_service().mark_relation_sync_failed(db, document.id, str(exc))
        try:
            self._provision_relation_service().sync_document_relations(db, document.id)
        except Exception as exc:  # pragma: no cover - defensive workflow guard
            logger.warning("Document %s ingested but provision relation sync failed: %s", document.id, exc)

    def _extract_segments_for_ingestion(
        self,
        *,
        document: Document,
        source_path: Path,
        knowledge_service,
        extracted_text_override: str | None,
    ) -> tuple[list[str], bool, float | None]:
        override_text = (extracted_text_override or "").strip()
        if override_text:
            return knowledge_service._split_plaintext_segments(override_text), False, None

        extracted_segments = knowledge_service._extract_segments(document.source_type, source_path)
        if any(segment.strip() for segment in extracted_segments) or document.source_type != "pdf":
            return extracted_segments, False, None

        ocr_result = self._ocr_service().diagnose_pdf(source_path)
        ocr_text = knowledge_service.postprocess_legal_ocr_text("\n".join(item.text.strip() for item in ocr_result.page_results or [] if item.text.strip()))
        ocr_segments = knowledge_service._split_plaintext_segments(ocr_text)
        return ocr_segments, bool(ocr_segments), ocr_result.average_confidence

    def _replace_document_chunks(
        self,
        db: Session,
        *,
        document: Document,
        chunk_payloads: list[tuple[str | None, str]],
    ) -> list[DocumentChunk]:
        existing_chunk_ids = select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
        db.execute(delete(DocumentChunkVector).where(DocumentChunkVector.chunk_id.in_(existing_chunk_ids)))
        db.execute(update(Citation).where(Citation.chunk_id.in_(existing_chunk_ids)).values(chunk_id=None))
        db.flush()
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.flush()

        created_chunks: list[DocumentChunk] = []
        for index, payload in enumerate(chunk_payloads, start=1):
            chunk_metadata = legal_chunk_builder.build_chunk_metadata(document, payload[0], payload[1])
            created_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                section_title=payload[0],
                chunk_type=chunk_metadata["chunk_type"],
                citation_label=chunk_metadata["citation_label"],
                hierarchy_path=chunk_metadata["hierarchy_path"],
                article_number=chunk_metadata["article_number"],
                clause_number=chunk_metadata["clause_number"],
                point_number=chunk_metadata["point_number"],
                retrieval_text=chunk_metadata["retrieval_text"],
                content=payload[1],
                metadata_json=chunk_metadata["metadata_json"],
                char_count=len(payload[1]),
            )
            db.add(created_chunk)
            created_chunks.append(created_chunk)
        return created_chunks

    def _apply_ocr_quality(
        self,
        *,
        document: Document,
        knowledge_service,
        extracted_segments: list[str],
        chunk_payloads: list[tuple[str | None, str]],
        ocr_average_confidence: float | None,
        ocr_used: bool,
        override_text: bool,
    ) -> None:
        ocr_quality_score, ocr_quality_label = knowledge_service._derive_ocr_quality(
            document=document,
            segments=extracted_segments,
            chunk_payloads=chunk_payloads,
            ocr_average_confidence=ocr_average_confidence,
            ocr_used=ocr_used,
        )
        document.ocr_quality_score = ocr_quality_score
        document.ocr_quality_label = ocr_quality_label
        if ocr_used:
            document.metadata_review_status = "pending_review"
            confidence_text = f" Avg OCR confidence: {ocr_average_confidence}." if ocr_average_confidence is not None else ""
            document.metadata_review_notes = f"OCR extraction was used for this PDF. Human review is recommended before relying on metadata or citations.{confidence_text}"[:2000]
            if (ocr_quality_score or 0) < 85:
                document.metadata_review_notes = (
                    f"{document.metadata_review_notes} OCR quality is below the preferred threshold for reliable legal citation."
                )[:2000]
        elif override_text:
            document.metadata_review_status = "reviewed"
            document.metadata_review_notes = "Chunking used the reviewer-edited extracted text instead of the raw source file."[:2000]

    def _apply_ingestion_quality_gate(
        self,
        *,
        document: Document,
        extracted_text: str,
        chunk_count: int,
        provision_count: int,
        provision_parser_source: str,
    ) -> None:
        issues: list[str] = []
        blocking_issues: list[str] = []
        ocr_quality_score = float(document.ocr_quality_score) if document.ocr_quality_score is not None else None

        if len(extracted_text.strip()) < 200:
            blocking_issues.append("extracted_text_too_short")
        if chunk_count == 0:
            blocking_issues.append("no_chunks")
        if ocr_quality_score is not None and ocr_quality_score < 75:
            blocking_issues.append("ocr_quality_below_blocking_threshold")
        elif ocr_quality_score is not None and ocr_quality_score < 85:
            issues.append("ocr_quality_requires_review")
        if provision_count == 0:
            issues.append("no_structured_provisions")
        if provision_parser_source == "ai_fallback":
            issues.append("ai_fallback_parser_used")
        if document.metadata_review_status != "reviewed":
            issues.append("metadata_pending_review")

        if blocking_issues:
            document.ingestion_quality_status = "blocked"
            document.retrieval_visibility = "blocked"
        elif issues:
            document.ingestion_quality_status = "review_required"
            document.retrieval_visibility = "indexed_unreviewed"
        else:
            document.ingestion_quality_status = "passed"
            document.retrieval_visibility = "indexed_verified" if document.metadata_review_status == "reviewed" else "indexed_unreviewed"

        all_issues = [*blocking_issues, *issues]
        document.ingestion_quality_notes = "; ".join(all_issues)[:2000] if all_issues else "Ingestion quality gate passed."

    def _index_embeddings(
        self,
        *,
        db: Session,
        document: Document,
        created_chunks: list[DocumentChunk],
        provision_count: int,
        provision_parser_source: str,
    ) -> None:
        if document.retrieval_visibility == "blocked":
            logger.warning("Document %s failed ingestion quality gate; embedding index skipped", document.id)
            return
        embedding_result = self._embedding_service().index_document_chunks(db, created_chunks)
        if embedding_result.status == "failed":
            logger.warning("Document %s ingested but embedding failed for %s chunks", document.id, embedding_result.failed_count)
        if provision_count == 0:
            logger.info("Document %s ingested without structured legal provisions", document.id)
        elif provision_parser_source == "ai_fallback":
            logger.info("Document %s ingested using AI fallback legal structure parser", document.id)

    def _legacy_knowledge_module(self):
        return sys.modules.get("src.services.knowledge_service")

    def _ocr_service(self):
        module = self._legacy_knowledge_module()
        return getattr(module, "ocr_service", ocr_service) if module is not None else ocr_service

    def _embedding_service(self):
        module = self._legacy_knowledge_module()
        return getattr(module, "embedding_service", embedding_service) if module is not None else embedding_service

    def _document_relation_service(self):
        module = self._legacy_knowledge_module()
        return getattr(module, "document_relation_service", document_relation_service) if module is not None else document_relation_service

    def _provision_relation_service(self):
        module = self._legacy_knowledge_module()
        return getattr(module, "provision_relation_service", provision_relation_service) if module is not None else provision_relation_service


knowledge_ingestion_pipeline = KnowledgeIngestionPipeline()
