from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import unicodedata

from sqlalchemy.orm import Session

from src.ingestion.upload_text_preview import upload_text_preview_service
from src.services.admin_service import admin_service
from src.services.metadata_enrichment_service import metadata_enrichment_service


AI_LEGAL_STATUS_MAP = {
    "active": "active",
    "con-hieu-luc": "active",
    "dang-co-hieu-luc": "active",
    "co-hieu-luc": "active",
    "còn hiệu lực": "active",
    "đang có hiệu lực": "active",
    "có hiệu lực": "active",
    "expired": "expired",
    "het-hieu-luc": "expired",
    "hết hiệu lực": "expired",
    "repealed": "repealed",
    "bi-thay-the-bai-bo": "repealed",
    "bi-thay-the": "repealed",
    "bi-bai-bo": "repealed",
    "bị thay thế/bãi bỏ": "repealed",
    "bị thay thế": "repealed",
    "bị bãi bỏ": "repealed",
    "draft": "draft",
    "du-thao": "draft",
    "dự thảo": "draft",
    "unknown": "unknown",
    "chua-ro": "unknown",
    "khong-ro": "unknown",
    "chưa rõ": "unknown",
    "không rõ": "unknown",
}


class DocumentMetadataInferenceService:
    def extract_document_metadata(
        self,
        file_path: Path,
        source_type: str,
        db: Session,
        preview_text: str | None = None,
    ) -> dict[str, object | None]:
        preview_text = preview_text if preview_text is not None else upload_text_preview_service.extract_preview_text(file_path, source_type)
        if not preview_text:
            return {
                "title": None,
                "legal_domain": self.default_legal_domain(db),
                "authority_level": None,
                "issuing_authority": None,
                "document_code": None,
                "document_type": None,
                "normative_level": None,
                "signed_date": None,
                "summary": None,
                "effective_date": None,
                "expiry_date": None,
                "legal_status": "unknown",
            }

        title = self.guess_title(preview_text)
        document_type = self.guess_document_type(preview_text)
        issuing_authority = self.guess_issuing_authority(preview_text)
        authority_level = self.guess_authority_level(db, issuing_authority)
        signed_date = self.guess_signed_date(preview_text)
        effective_date = self.guess_effective_date(preview_text)
        expiry_date = self.guess_expiry_date(preview_text)
        metadata = {
            "title": title,
            "legal_domain": self.guess_legal_domain(preview_text, db),
            "authority_level": authority_level,
            "issuing_authority": issuing_authority,
            "document_code": self.guess_document_code(preview_text),
            "document_type": document_type,
            "normative_level": self.infer_normative_level(db, document_type),
            "signed_date": signed_date,
            "summary": self.guess_summary(preview_text, title),
            "effective_date": effective_date,
            "expiry_date": expiry_date,
            "legal_status": self.guess_legal_status(preview_text, effective_date, expiry_date),
        }

        allowed_domains = [(category.slug, category.name) for category in admin_service.list_categories(db)]
        allowed_document_types = [(item.slug, item.name) for item in admin_service.list_document_types(db) if item.is_active]
        allowed_authority_levels = [(item.slug, item.name) for item in admin_service.list_authority_levels(db) if item.is_active]
        enriched = metadata_enrichment_service.enrich_document_metadata(
            title=title,
            preview_text=preview_text,
            allowed_domains=allowed_domains,
            allowed_document_types=allowed_document_types,
            allowed_authority_levels=allowed_authority_levels,
            file_name=file_path.name,
            storage_path=str(file_path),
        )
        if not enriched:
            return metadata

        active_document_types = admin_service.get_active_document_type_slugs(db)
        active_authority_levels = admin_service.get_active_authority_level_slugs(db)
        ai_document_type = enriched.get("document_type") if enriched.get("document_type") in active_document_types else None
        ai_authority_level = enriched.get("authority_level") if enriched.get("authority_level") in active_authority_levels else None
        ai_signed_date = self.parse_ai_date(enriched.get("signed_date"))
        ai_effective_date = self.parse_ai_date(enriched.get("effective_date"))
        ai_expiry_date = self.parse_ai_date(enriched.get("expiry_date"))
        resolved_issuing_authority = enriched.get("issuing_authority") or metadata["issuing_authority"]
        resolved_document_type = ai_document_type or metadata["document_type"]
        resolved_authority_level = ai_authority_level or self.guess_authority_level(db, resolved_issuing_authority) or metadata["authority_level"]
        resolved_signed_date = ai_signed_date or metadata["signed_date"]
        resolved_effective_date = ai_effective_date or metadata["effective_date"]
        resolved_expiry_date = ai_expiry_date or metadata["expiry_date"]
        resolved_legal_status = self.normalize_ai_legal_status(enriched.get("legal_status")) or self.guess_legal_status(preview_text, resolved_effective_date, resolved_expiry_date)
        legal_domain = enriched.get("legal_domain") if enriched.get("legal_domain") in {slug for slug, _ in allowed_domains} else None

        return {
            "title": enriched.get("title") or metadata["title"],
            "legal_domain": legal_domain or metadata["legal_domain"],
            "authority_level": resolved_authority_level,
            "issuing_authority": resolved_issuing_authority,
            "document_code": enriched.get("document_code") or metadata["document_code"],
            "document_type": resolved_document_type,
            "normative_level": self.infer_normative_level(db, resolved_document_type),
            "signed_date": resolved_signed_date,
            "summary": enriched.get("summary") or metadata["summary"],
            "effective_date": resolved_effective_date,
            "expiry_date": resolved_expiry_date,
            "legal_status": resolved_legal_status,
        }

    def guess_title(self, preview_text: str) -> str | None:
        lines = [re.sub(r"\s+", " ", line).strip(" :-\t") for line in preview_text.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return None

        normalized_lines = [self.normalize_search_text(line) for line in lines]
        title_markers = {"nghi quyet", "thong tu", "thong tu lien tich", "quyet dinh", "nghi dinh", "luat", "bo luat", "chi thi"}
        skip_prefixes = ("can cu", "phan", "chuong", "muc", "dieu", "khoan", "diem", "so", "ha noi", "tp", "nghi quyet nay", "thong tu nay", "nghi dinh nay", "quyet dinh nay")
        authority_markers = ("toa an nhan dan", "hoi dong tham phan", "quoc hoi", "chinh phu", "bo ", "vien kiem sat", "uy ban")

        for index, normalized_line in enumerate(normalized_lines):
            if normalized_line in title_markers:
                title_lines: list[str] = []
                for candidate_index in range(index + 1, min(index + 4, len(lines))):
                    candidate_line = lines[candidate_index]
                    candidate_normalized = normalized_lines[candidate_index]
                    if any(candidate_normalized.startswith(prefix) for prefix in skip_prefixes):
                        break
                    if any(marker in candidate_normalized for marker in authority_markers):
                        break
                    if len(candidate_line) < 6:
                        continue
                    title_lines.append(candidate_line)
                if title_lines:
                    return " ".join(title_lines)[:500]

        for line, normalized_line in zip(lines, normalized_lines, strict=True):
            if len(line) < 6:
                continue
            if any(normalized_line.startswith(prefix) for prefix in skip_prefixes):
                continue
            if any(marker in normalized_line for marker in authority_markers):
                continue
            return line[:500]
        return None

    def guess_document_code(self, preview_text: str) -> str | None:
        code_patterns = [
            r"Số\s*[:：]\s*([0-9]+/[0-9]{4}/[A-ZĂÂĐÊÔƠƯ\-]+)",
            r"So\s*[:：]\s*([0-9]+/[0-9]{4}/[A-Z\-]+)",
            r"\b([0-9]+/[0-9]{4}/[A-ZĂÂĐÊÔƠƯ\-]{3,})\b",
        ]
        for pattern in code_patterns:
            match = re.search(pattern, preview_text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def guess_document_type(self, preview_text: str) -> str | None:
        lines = [line.strip() for line in preview_text.splitlines() if line.strip()]
        normalized_lines = [self.normalize_search_text(line) for line in lines[:20]]
        type_patterns = [
            ("bo luat", "bo-luat"),
            ("luat", "luat"),
            ("nghi quyet", "nghi-quyet"),
            ("nghi dinh", "nghi-dinh"),
            ("thong tu lien tich", "thong-tu"),
            ("thong tu", "thong-tu"),
            ("quyet dinh", "quyet-dinh"),
            ("chi thi", "chi-thi"),
            ("an le", "an-le"),
        ]
        for marker, value in type_patterns:
            for line in normalized_lines:
                if line == marker or line.startswith(f"{marker} "):
                    return value

        normalized_text = self.normalize_search_text("\n".join(lines[:10]))
        for marker, value in type_patterns:
            if re.search(rf"\b{re.escape(marker)}\b", normalized_text):
                return value
        return "khac"

    def infer_normative_level(self, db: Session, document_type: str | None) -> int | None:
        return admin_service.get_document_type_priority(db, document_type)

    def default_legal_domain(self, db: Session) -> str:
        categories = admin_service.list_categories(db)
        if categories:
            return categories[0].slug
        return "lao-dong"

    def normalize_search_text(self, value: str) -> str:
        lowered = value.lower().replace("đ", "d")
        normalized = unicodedata.normalize("NFD", lowered)
        stripped = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
        return re.sub(r"\s+", " ", stripped).strip()

    def guess_legal_domain(self, preview_text: str, db: Session) -> str:
        normalized_text = self.normalize_search_text(preview_text)
        categories = admin_service.list_categories(db)
        if not categories:
            return "lao-dong"

        slug_hints = {
            "lao-dong": ["lao dong", "hop dong lao dong", "thu viec", "tien luong", "lam them gio", "ky luat lao dong", "sa thai", "bao hiem xa hoi", "tranh chap lao dong", "nghi viec"],
            "hon-nhan-va-gia-dinh": ["hon nhan va gia dinh", "ly hon", "nuoi con", "cap duong", "chia tai san", "ket hon"],
            "dat-dai": ["dat dai", "quyen su dung dat", "thu hoi dat", "boi thuong giai phong mat bang", "so do"],
        }

        best_slug = categories[0].slug
        best_score = -1
        for category in categories:
            score = 0
            for token in [self.normalize_search_text(category.name), self.normalize_search_text(category.description or "")]:
                if token and token in normalized_text:
                    score += 4
            for hint in slug_hints.get(category.slug, []):
                if hint in normalized_text:
                    score += 3
            if score > best_score:
                best_score = score
                best_slug = category.slug

        return best_slug

    def guess_issuing_authority(self, preview_text: str) -> str | None:
        lines = [line.strip() for line in preview_text.splitlines() if line.strip()]
        header_lines: list[str] = []
        for line in lines[:20]:
            normalized_line = self.normalize_search_text(line)
            if normalized_line.startswith("can cu"):
                break
            header_lines.append(line)

        normalized_text = self.normalize_search_text("\n".join(header_lines or lines[:8]))
        authority_patterns = [
            ("hoi dong tham phan toa an nhan dan toi cao", "Hội đồng Thẩm phán Tòa án nhân dân tối cao"),
            ("quoc hoi", "Quốc hội"),
            ("uy ban thuong vu quoc hoi", "Ủy ban Thường vụ Quốc hội"),
            ("chinh phu", "Chính phủ"),
            ("thu tuong chinh phu", "Thủ tướng Chính phủ"),
            ("bo lao dong thuong binh va xa hoi", "Bộ Lao động - Thương binh và Xã hội"),
            ("bo tu phap", "Bộ Tư pháp"),
            ("toa an nhan dan toi cao", "Tòa án nhân dân tối cao"),
            ("vien kiem sat nhan dan toi cao", "Viện kiểm sát nhân dân tối cao"),
            ("tong lien doan lao dong viet nam", "Tổng Liên đoàn Lao động Việt Nam"),
            ("bo y te", "Bộ Y tế"),
        ]

        for pattern, label in authority_patterns:
            if pattern in normalized_text:
                return label
        return None

    def guess_authority_level(self, db: Session, issuing_authority: str | None) -> str | None:
        if not issuing_authority:
            return None
        normalized = self.normalize_search_text(issuing_authority)
        if "quoc hoi" in normalized:
            return "quoc-hoi"
        if "uy ban thuong vu quoc hoi" in normalized:
            return "uy-ban-thuong-vu-quoc-hoi"
        if "thu tuong chinh phu" in normalized:
            return "thu-tuong-chinh-phu"
        if "chinh phu" in normalized:
            return "chinh-phu"
        if "hoi dong tham phan toa an nhan dan toi cao" in normalized:
            return "hoi-dong-tham-phan-tandtc"
        if "toa an nhan dan toi cao" in normalized:
            return "toa-an-nhan-dan-toi-cao"
        if "vien kiem sat nhan dan toi cao" in normalized:
            return "vien-kiem-sat-nhan-dan-toi-cao"
        if normalized.startswith("bo "):
            return "bo"
        if "uy ban nhan dan" in normalized:
            return "uy-ban-nhan-dan"
        active_authority_levels = admin_service.get_active_authority_level_slugs(db)
        return "khac" if "khac" in active_authority_levels else None

    def guess_signed_date(self, preview_text: str):
        for line in preview_text.splitlines()[:30]:
            normalized_line = self.normalize_search_text(line)
            if normalized_line.startswith(("can cu", "dieu ", "khoan ", "muc ", "chuong ")):
                continue
            match = re.search(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", line, flags=re.IGNORECASE)
            if match:
                day, month, year = match.groups()
                try:
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue
            match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", line)
            if match:
                day, month, year = match.groups()
                try:
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        return None

    def guess_effective_date(self, preview_text: str):
        date_patterns = [
            r"co hieu luc(?: thi hanh)?(?: ke tu| tu)? ngay\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            r"hieu luc(?: thi hanh)?(?: ke tu| tu)? ngay\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        ]
        normalized_text = self.normalize_search_text(preview_text)
        for pattern in date_patterns:
            match = re.search(pattern, normalized_text)
            if match:
                raw_value = match.group(1).replace("-", "/")
                try:
                    return datetime.strptime(raw_value, "%d/%m/%Y").date()
                except ValueError:
                    continue
        return None

    def guess_expiry_date(self, preview_text: str):
        normalized_text = self.normalize_search_text(preview_text)
        date_patterns = [
            r"het hieu luc(?: ke tu| tu)? ngay\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            r"co hieu luc den het ngay\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, normalized_text)
            if match:
                raw_value = match.group(1).replace("-", "/")
                try:
                    return datetime.strptime(raw_value, "%d/%m/%Y").date()
                except ValueError:
                    continue
        return None

    def guess_legal_status(self, preview_text: str, effective_date_value, expiry_date_value) -> str:
        header_text = self.normalize_search_text("\n".join(preview_text.splitlines()[:20]))
        if "du thao" in header_text or "lay y kien ve du thao" in header_text:
            return "draft"
        normalized_text = self.normalize_search_text(preview_text)
        if "bi bai bo" in normalized_text or "bai bo" in normalized_text:
            return "repealed"
        if expiry_date_value and expiry_date_value < date.today():
            return "expired"
        if effective_date_value and effective_date_value > date.today():
            return "draft"
        return "active"

    def guess_summary(self, preview_text: str, title: str | None) -> str | None:
        lines = [re.sub(r"\s+", " ", line).strip(" :-\t") for line in preview_text.splitlines()]
        filtered_lines = [line for line in lines if line and line != title and len(line) >= 24]
        summary_lines: list[str] = []
        for line in filtered_lines:
            normalized_line = self.normalize_search_text(line)
            if normalized_line.startswith(("so ", "can cu", "nghi quyet", "thong tu", "quyet dinh", "nghi dinh", "dieu ", "khoan ", "chuong ", "muc ")):
                continue
            summary_lines.append(line)
            if len(" ".join(summary_lines)) >= 260:
                break
        if not summary_lines:
            return None
        return " ".join(summary_lines)[:500]

    def parse_ai_date(self, value: str | None):
        if not value:
            return None
        normalized = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        return None

    def normalize_ai_legal_status(self, value: str | None) -> str | None:
        if not value:
            return None
        normalized = self.normalize_search_text(value).replace("/", "-")
        return AI_LEGAL_STATUS_MAP.get(normalized) or AI_LEGAL_STATUS_MAP.get(value.strip().lower())


document_metadata_inference_service = DocumentMetadataInferenceService()
