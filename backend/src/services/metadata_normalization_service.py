import re
import unicodedata
from collections.abc import Mapping


LEGAL_STATUS_ALIASES = {
    "active": "active",
    "con-hieu-luc": "active",
    "co-hieu-luc": "active",
    "dang-co-hieu-luc": "active",
    "expired": "expired",
    "het-hieu-luc": "expired",
    "repealed": "repealed",
    "bi-bai-bo": "repealed",
    "bi-thay-the": "repealed",
    "bi-thay-the-bai-bo": "repealed",
    "draft": "draft",
    "du-thao": "draft",
    "unknown": "unknown",
    "chua-ro": "unknown",
    "khong-ro": "unknown",
}

ISSUING_AUTHORITY_ALIASES = {
    "quoc hoi": "Quoc hoi",
    "uy ban thuong vu quoc hoi": "Uy ban Thuong vu Quoc hoi",
    "chinh phu": "Chinh phu",
    "thu tuong chinh phu": "Thu tuong Chinh phu",
    "bo lao dong thuong binh va xa hoi": "Bo Lao dong - Thuong binh va Xa hoi",
    "bo tu phap": "Bo Tu phap",
    "toa an nhan dan toi cao": "Toa an nhan dan toi cao",
}


class MetadataNormalizationService:
    def normalize_document_payload(self, payload: Mapping[str, object | None]) -> dict[str, object | None]:
        normalized = dict(payload)
        normalized["title"] = self._normalize_sentence_case(payload.get("title"))
        normalized["file_name"] = self._normalize_file_name(payload.get("file_name"))
        normalized["source_type"] = self._normalize_simple_slug(payload.get("source_type"))
        normalized["legal_domain"] = self._normalize_simple_slug(payload.get("legal_domain"))
        normalized["authority_level"] = self._normalize_simple_slug(payload.get("authority_level"))
        normalized["issuing_authority"] = self._normalize_issuing_authority(payload.get("issuing_authority"))
        normalized["document_code"] = self._normalize_document_code(payload.get("document_code"))
        normalized["document_type"] = self._normalize_simple_slug(payload.get("document_type"))
        normalized["source_reference"] = self._normalize_whitespace(payload.get("source_reference"))
        normalized["storage_path"] = self._normalize_whitespace(payload.get("storage_path"))
        normalized["summary"] = self._normalize_whitespace(payload.get("summary"))
        normalized["legal_status"] = self._normalize_legal_status(payload.get("legal_status"))
        normalized["metadata_review_notes"] = self._normalize_whitespace(payload.get("metadata_review_notes"))
        return normalized

    def _normalize_document_code(self, value: object | None) -> str | None:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return None
        compact = re.sub(r"\s+", " ", normalized.upper())
        return compact.replace(" / ", "/").replace("- ", "-").replace(" -", "-")

    def _normalize_issuing_authority(self, value: object | None) -> str | None:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return None
        plain = self._slug_text(normalized).replace("-", " ")
        return ISSUING_AUTHORITY_ALIASES.get(plain, self._normalize_sentence_case(normalized))

    def _normalize_legal_status(self, value: object | None) -> str:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return "unknown"
        slug = self._slug_text(normalized)
        return LEGAL_STATUS_ALIASES.get(slug, "unknown")

    def _normalize_file_name(self, value: object | None) -> str | None:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return None
        return normalized.replace("\\", "/").split("/")[-1]

    def _normalize_simple_slug(self, value: object | None) -> str | None:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return None
        return self._slug_text(normalized).replace("_", "-")

    def _normalize_sentence_case(self, value: object | None) -> str | None:
        normalized = self._normalize_whitespace(value)
        if not normalized:
            return None
        return normalized[:1].upper() + normalized[1:]

    def _normalize_whitespace(self, value: object | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", " ", str(value)).strip()
        return normalized or None

    def _slug_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        lowered = ascii_value.lower()
        collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
        return collapsed


metadata_normalization_service = MetadataNormalizationService()