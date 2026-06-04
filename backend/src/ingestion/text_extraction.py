from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from src.core.exceptions import ValidationException
from src.services.legal_provision_parser_service import legal_provision_parser_service


class DocumentTextExtractor:
    def extract_text(self, source_type: str, source_path: Path) -> str:
        return "\n".join(self.extract_segments(source_type, source_path))

    def extract_segments(self, source_type: str, source_path: Path) -> list[str]:
        if source_type == "pdf":
            reader = PdfReader(str(source_path))
            segments: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                segments.extend(self.split_plaintext_segments(page_text))
            return segments

        if source_type == "txt":
            return self.split_plaintext_segments(source_path.read_text(encoding="utf-8"))

        if source_type == "docx":
            document = DocxDocument(str(source_path))
            return [self.normalize_segment(paragraph.text) for paragraph in document.paragraphs if self.normalize_segment(paragraph.text)]

        raise ValidationException("Unsupported document type for ingestion")

    def split_plaintext_segments(self, text: str) -> list[str]:
        return [self.normalize_segment(line) for line in text.splitlines() if self.normalize_segment(line)]

    def normalize_segment(self, value: str) -> str:
        return legal_provision_parser_service.normalize_structure_segment(value)


document_text_extractor = DocumentTextExtractor()
