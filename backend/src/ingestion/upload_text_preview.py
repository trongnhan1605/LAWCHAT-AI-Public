from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument

from src.services.ocr_service import ocr_service


class UploadTextPreviewService:
    def extract_preview_text(self, file_path: Path, source_type: str) -> str:
        try:
            if source_type == "docx":
                document = DocxDocument(file_path)
                paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text and paragraph.text.strip()]
                return "\n".join(paragraphs[:80])

            if source_type == "txt":
                return file_path.read_text(encoding="utf-8", errors="ignore")[:12000]
        except Exception:
            return ""

        return ""

    def extract_full_text(self, file_path: Path, source_type: str, *, knowledge_service) -> tuple[str, bool, dict[str, object] | None]:
        try:
            segments = knowledge_service._extract_segments(source_type, file_path)
            if not any(segment.strip() for segment in segments) and source_type == "pdf":
                ocr_result = ocr_service.diagnose_pdf(file_path)
                raw_ocr_text = "\n".join(item.text.strip() for item in ocr_result.page_results or [] if item.text.strip())
                ocr_preview = knowledge_service.preview_legal_ocr_correction(raw_ocr_text)
                return str(ocr_preview.get("corrected_text", "")).strip(), True, ocr_preview
            raw_text = "\n".join(segment for segment in segments if segment).strip()
            return raw_text, False, None
        except Exception:
            return self.extract_preview_text(file_path, source_type), False, None


upload_text_preview_service = UploadTextPreviewService()
