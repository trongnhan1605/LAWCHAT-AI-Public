from __future__ import annotations

import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core.config import settings
from src.ingestion.document_metadata_inference import document_metadata_inference_service
from src.ingestion.upload_text_preview import upload_text_preview_service
from src.models.document import Document
from src.schemas.admin_schema import OcrCorrectionSuggestionItem, UploadedDocumentFile
from src.services.admin_service import admin_service
from src.services.knowledge_service import knowledge_service


SUPPORTED_UPLOAD_EXTENSIONS = {".pdf": "pdf", ".txt": "txt", ".docx": "docx"}


@dataclass(frozen=True)
class UploadedIngestionResult:
    uploaded_file: UploadedDocumentFile
    document: Document
    extracted_characters: int
    chunk_count: int


class AdminUploadService:
    def store_uploaded_document_file(self, file: UploadFile, db: Session) -> UploadedDocumentFile:
        original_name = Path(file.filename or "").name
        return self._store_document_source(file.file, original_name=original_name, db=db, import_subdir="uploads")

    def store_local_document_file(self, source_path: Path, db: Session, *, import_subdir: str = "imports") -> UploadedDocumentFile:
        if not source_path.exists() or not source_path.is_file():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Source file not found: {source_path}")
        with source_path.open("rb") as input_stream:
            return self._store_document_source(input_stream, original_name=source_path.name, db=db, import_subdir=import_subdir)

    def _store_document_source(self, input_stream, *, original_name: str, db: Session, import_subdir: str) -> UploadedDocumentFile:
        original_name = Path(original_name or "").name
        suffix = Path(original_name).suffix.lower()
        source_type = SUPPORTED_UPLOAD_EXTENSIONS.get(suffix)
        if not original_name or not source_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

        upload_dir = settings.legal_sources_dir / import_subdir
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_stem = self.slugify_filename(Path(original_name).stem)
        target_name = f"{safe_stem}{suffix}"
        target_path = upload_dir / target_name
        duplicate_index = 1
        while target_path.exists():
            target_name = f"{safe_stem}-{duplicate_index}{suffix}"
            target_path = upload_dir / target_name
            duplicate_index += 1

        with target_path.open("wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)

        extracted_text, ocr_applied, ocr_preview = upload_text_preview_service.extract_full_text(target_path, source_type, knowledge_service=knowledge_service)
        extracted_metadata = document_metadata_inference_service.extract_document_metadata(target_path, source_type, db, extracted_text)
        relative_path = target_path.relative_to(settings.project_root)
        return UploadedDocumentFile(
            title=extracted_metadata.get("title") or self.humanize_filename(Path(original_name).stem),
            file_name=target_name,
            source_type=source_type,
            source_reference=str(relative_path).replace("\\", "/"),
            storage_path=str(target_path),
            extracted_text=extracted_text or None,
            extracted_characters=len(extracted_text),
            ocr_applied=ocr_applied,
            ocr_review_required=bool((ocr_preview or {}).get("review_required", False)),
            ocr_correction_changed_token_count=int((ocr_preview or {}).get("changed_token_count", 0) or 0),
            ocr_suggestions=[OcrCorrectionSuggestionItem.model_validate(item) for item in (ocr_preview or {}).get("suggestions", [])],
            legal_domain=extracted_metadata.get("legal_domain"),
            authority_level=extracted_metadata.get("authority_level"),
            issuing_authority=extracted_metadata.get("issuing_authority"),
            document_code=extracted_metadata.get("document_code"),
            document_type=extracted_metadata.get("document_type"),
            normative_level=extracted_metadata.get("normative_level"),
            signed_date=extracted_metadata.get("signed_date"),
            summary=extracted_metadata.get("summary"),
            effective_date=extracted_metadata.get("effective_date"),
            expiry_date=extracted_metadata.get("expiry_date"),
            legal_status=extracted_metadata.get("legal_status"),
        )

    def upload_and_ingest_document_file(self, file: UploadFile, duplicate_action: str | None, db: Session) -> UploadedIngestionResult:
        uploaded_file = self.store_uploaded_document_file(file, db)
        created_document = None

        try:
            created_document = admin_service.create_document(
                db,
                uploaded_file.title,
                uploaded_file.file_name,
                uploaded_file.source_type,
                uploaded_file.legal_domain or document_metadata_inference_service.default_legal_domain(db),
                uploaded_file.authority_level,
                uploaded_file.issuing_authority,
                uploaded_file.document_code,
                uploaded_file.document_type,
                uploaded_file.normative_level,
                uploaded_file.signed_date,
                uploaded_file.source_reference,
                uploaded_file.storage_path,
                uploaded_file.summary,
                uploaded_file.effective_date,
                uploaded_file.expiry_date,
                uploaded_file.legal_status,
                True,
                duplicate_action,
                metadata_review_status="pending_review",
            )
            ingested_document, extracted_characters, chunk_count = knowledge_service.ingest_document(db, created_document.id)
        except Exception:
            if created_document is not None:
                try:
                    admin_service.delete_document(db, created_document.id)
                except Exception:
                    pass
            self.remove_uploaded_file(uploaded_file.storage_path)
            raise

        return UploadedIngestionResult(uploaded_file=uploaded_file, document=ingested_document, extracted_characters=extracted_characters, chunk_count=chunk_count)

    def slugify_filename(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        safe = "".join(character if character.isalnum() else "-" for character in ascii_value.lower())
        collapsed = "-".join(part for part in safe.split("-") if part)
        return collapsed or "document"

    def humanize_filename(self, value: str) -> str:
        normalized = value.replace("_", " ").replace("-", " ").strip()
        return normalized[:1].upper() + normalized[1:] if normalized else "Document"

    def remove_uploaded_file(self, storage_path: str) -> None:
        try:
            Path(storage_path).unlink(missing_ok=True)
        except OSError:
            pass


admin_upload_service = AdminUploadService()
