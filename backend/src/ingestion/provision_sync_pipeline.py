from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging import logger
from src.models.document import Document
from src.services.legal_provision_ai_fallback_service import legal_provision_ai_fallback_service
from src.services.legal_provision_parser_service import legal_provision_parser_service
from src.services.legal_provision_service import legal_provision_service


class ProvisionSyncPipeline:
    def should_attempt_ai_structure_fallback(self, text: str, *, knowledge_service) -> bool:
        if not text.strip():
            return False
        diagnostics = knowledge_service._analyze_structure_diagnostics(text)
        score = float(diagnostics["structure_quality_score"] or 0)
        return diagnostics["parser_status"] == "failed" or score < float(settings.legal_structure_ai_fallback_threshold)

    def sync_document_provisions_with_fallback(
        self,
        db: Session,
        *,
        document: Document,
        extracted_text: str,
        knowledge_service,
    ) -> tuple[int, str]:
        deterministic_payloads = legal_provision_parser_service.build_document_payloads(document_id=document.id, text=extracted_text)
        deterministic_count = len(deterministic_payloads)
        selected_payloads = deterministic_payloads
        parser_source = "deterministic"

        if self.should_attempt_ai_structure_fallback(extracted_text, knowledge_service=knowledge_service):
            try:
                fallback_payloads = legal_provision_ai_fallback_service.parse_text(document_id=document.id, text=extracted_text)
            except Exception as exc:  # pragma: no cover - defensive network fallback
                logger.warning("AI fallback parser failed for document %s: %s", document.id, exc)
                fallback_payloads = []

            if fallback_payloads and len(fallback_payloads) > deterministic_count:
                selected_payloads = fallback_payloads
                parser_source = "ai_fallback"

        provision_count = legal_provision_service.sync_document_provisions_from_payloads(db, document, selected_payloads)
        if parser_source == "ai_fallback" and provision_count > 0:
            document.metadata_review_status = "pending_review"
            fallback_note = "AI fallback parser generated legal structure for this document. Human review is recommended before relying on provision hierarchy or provision relations."
            existing_notes = (document.metadata_review_notes or "").strip()
            document.metadata_review_notes = f"{existing_notes} {fallback_note}".strip()[:2000]
        return provision_count, parser_source


provision_sync_pipeline = ProvisionSyncPipeline()
