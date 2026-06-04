from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from src.core.logging import logger


@dataclass(slots=True)
class OcrPageResult:
    page: int
    text: str
    average_confidence: float | None


@dataclass(slots=True)
class OcrDiagnosticResult:
    available: bool
    engine: str | None
    reason: str | None = None
    page_results: list[OcrPageResult] | None = None

    @property
    def extracted_characters(self) -> int:
        return sum(len((item.text or "").strip()) for item in self.page_results or [])

    @property
    def average_confidence(self) -> float | None:
        values = [item.average_confidence for item in self.page_results or [] if item.average_confidence is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 3)


class OcrService:
    ENGINE_NAME = "tesseract"
    WINDOWS_TESSERACT_CANDIDATES = (
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    )

    def _resolve_tesseract_binary(self) -> str | None:
        resolved = shutil.which(self.ENGINE_NAME)
        if resolved:
            return resolved

        for candidate in self.WINDOWS_TESSERACT_CANDIDATES:
            if candidate.exists():
                return str(candidate)
        return None

    def _resolve_local_tessdata_dir(self) -> Path | None:
        candidate = Path(__file__).resolve().parents[2] / "tessdata"
        if candidate.exists():
            return candidate
        return None

    def _language_available_in_dir(self, tessdata_dir: Path | None, language: str) -> bool:
        if tessdata_dir is None:
            return False
        required = [part.strip() for part in language.split("+") if part.strip()]
        if not required:
            return False
        return all((tessdata_dir / f"{part}.traineddata").exists() for part in required)

    def is_available(self) -> tuple[bool, str | None]:
        if self._resolve_tesseract_binary() is None:
            return False, "Tesseract OCR binary is not installed or not available on PATH."

        try:
            import pytesseract  # noqa: F401
            import pypdfium2  # noqa: F401
        except Exception as exc:
            return False, f"OCR Python dependencies are unavailable: {exc}"

        return True, None

    def diagnose_pdf(self, pdf_path: Path, *, max_pages: int | None = None) -> OcrDiagnosticResult:
        available, reason = self.is_available()
        if not available:
            return OcrDiagnosticResult(available=False, engine=self.ENGINE_NAME, reason=reason, page_results=[])

        try:
            page_results = self._ocr_pdf(pdf_path, max_pages=max_pages)
        except Exception as exc:  # pragma: no cover - defensive guard around local OCR runtime
            logger.warning("OCR failed for %s: %s", pdf_path, exc)
            return OcrDiagnosticResult(available=False, engine=self.ENGINE_NAME, reason=str(exc), page_results=[])

        return OcrDiagnosticResult(available=True, engine=self.ENGINE_NAME, reason=None, page_results=page_results)

    def extract_pdf_segments(self, pdf_path: Path) -> list[str]:
        result = self.diagnose_pdf(pdf_path)
        if not result.available:
            return []
        return [item.text.strip() for item in result.page_results or [] if item.text.strip()]

    def _ocr_pdf(self, pdf_path: Path, *, max_pages: int | None = None) -> list[OcrPageResult]:
        import pytesseract
        import pypdfium2 as pdfium

        binary_path = self._resolve_tesseract_binary()
        if binary_path:
            pytesseract.pytesseract.tesseract_cmd = binary_path

        tessdata_dir = self._resolve_local_tessdata_dir()
        if tessdata_dir is not None:
            os.environ.setdefault("TESSDATA_PREFIX", str(tessdata_dir))

        pdf = pdfium.PdfDocument(str(pdf_path))
        page_results: list[OcrPageResult] = []
        try:
            total_pages = len(pdf)
            target_pages = min(total_pages, max_pages) if max_pages is not None else total_pages
            for page_index in range(target_pages):
                page = pdf[page_index]
                bitmap = page.render(scale=2)
                image = bitmap.to_pil()
                text, confidence = self._extract_text_from_image(image, pytesseract)
                page_results.append(OcrPageResult(page=page_index + 1, text=text, average_confidence=confidence))
        finally:
            pdf.close()

        return page_results

    def _extract_text_from_image(self, image, pytesseract_module) -> tuple[str, float | None]:
        pytesseract = pytesseract_module
        tessdata_dir = self._resolve_local_tessdata_dir()
        output = None
        for language in ("vie+eng", "vie", "eng"):
            config_candidates = []
            if self._language_available_in_dir(tessdata_dir, language):
                config_candidates.append(f'--tessdata-dir "{tessdata_dir}"')
            config_candidates.append("")
            for extra_config in config_candidates:
                try:
                    output = pytesseract.image_to_data(
                        image,
                        lang=language,
                        config=extra_config,
                        output_type=pytesseract.Output.DICT,
                    )
                    break
                except pytesseract.TesseractError:
                    continue
            if output is not None:
                break

        if output is None:
            raise RuntimeError("Tesseract OCR could not process the page with available language packs.")

        tokens: list[str] = []
        confidences: list[float] = []
        for token, confidence in zip(output.get("text", []), output.get("conf", []), strict=False):
            normalized_token = str(token or "").strip()
            if not normalized_token:
                continue
            tokens.append(normalized_token)
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                continue
            if confidence_value >= 0:
                confidences.append(confidence_value)

        average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
        return " ".join(tokens).strip(), average_confidence


ocr_service = OcrService()
