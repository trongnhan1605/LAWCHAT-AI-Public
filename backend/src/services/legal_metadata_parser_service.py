from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path


CODE_PATTERNS = (
    re.compile(
        r"(?:số|so)\s*[:：]?\s*([0-9]{1,4}\s*/\s*[0-9]{4}\s*/\s*[A-ZĂÂĐÊÔƠƯ][A-ZĂÂĐÊÔƠƯ0-9]*(?:[ ._-]+[A-ZĂÂĐÊÔƠƯ][A-ZĂÂĐÊÔƠƯ0-9]*)*)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b([0-9]{1,4}\s*/\s*[0-9]{4}\s*/\s*[A-ZĂÂĐÊÔƠƯ][A-ZĂÂĐÊÔƠƯ0-9]*(?:[ ._-]+[A-ZĂÂĐÊÔƠƯ][A-ZĂÂĐÊÔƠƯ0-9]*)*)\b",
        flags=re.IGNORECASE,
    ),
)

FILENAME_CODE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,4})[\s._-]+(\d{4})[\s._-]+([A-Z]{1,16}[A-Z0-9]*(?:[\s._-]+[A-Z]{1,16}[A-Z0-9]*)*)(?![A-Z0-9])",
    flags=re.IGNORECASE,
)

CANONICAL_CODE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,4})\s*/\s*(\d{4})\s*/\s*([A-Z]{1,16}[A-Z0-9]*(?:[ ._-]+[A-Z]{1,16}[A-Z0-9]*)*)(?![A-Z0-9])",
    flags=re.IGNORECASE,
)

DATE_PATTERNS = (
    re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", flags=re.IGNORECASE),
    re.compile(r"ngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})", flags=re.IGNORECASE),
    re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})"),
)
MAX_DOCUMENT_TITLE_CHARS = 240
MAX_DOCUMENT_TITLE_WORDS = 28

DOCUMENT_TYPE_PREFIXES = {
    "bo-luat": "Bo luat",
    "luat": "Luat",
    "nghi-quyet": "Nghi quyet",
    "nghi-dinh": "Nghi dinh",
    "thong-tu": "Thong tu",
    "thong-tu-lien-tich": "Thong tu lien tich",
    "quyet-dinh": "Quyet dinh",
    "chi-thi": "Chi thi",
    "van-ban-hop-nhat": "Van ban hop nhat",
    "an-le": "An le",
}


class LegalMetadataParserService:
    def infer_document_metadata(self, *, file_name: str | None, preview_text: str) -> dict[str, object | None]:
        document_code = self._guess_document_code(preview_text, file_name)
        document_type = self._guess_document_type(preview_text, document_code)
        document_title = self._guess_document_title(preview_text, document_type)
        issuing_authority = self._guess_issuing_authority(preview_text, document_code)
        authority_level = self._guess_authority_level(issuing_authority, document_code)
        signed_date = self._guess_signed_date(preview_text)
        return {
            "document_title": document_title,
            "document_code": document_code,
            "document_type": document_type,
            "issuing_authority": issuing_authority,
            "authority_level": authority_level,
            "signed_date": signed_date,
        }

    def code_aliases_for_document(self, *, file_name: str | None, document_code: str | None) -> list[str]:
        aliases: list[str] = []
        if document_code:
            aliases.append(self.normalize_code(document_code))
        inferred_from_file = self._guess_document_code("", file_name)
        if inferred_from_file:
            aliases.append(self.normalize_code(inferred_from_file))
        deduped: list[str] = []
        for alias in aliases:
            if alias and alias not in deduped:
                deduped.append(alias)
        return deduped

    def extract_citation_code_mentions(self, value: str) -> list[dict[str, int | str]]:
        mentions: list[dict[str, int | str]] = []
        seen: set[tuple[str, int]] = set()
        for pattern in CODE_PATTERNS:
            for match in pattern.finditer(value):
                normalized_code = self.normalize_code(match.group(1))
                if not normalized_code:
                    continue
                key = (normalized_code, match.start())
                if key in seen:
                    continue
                seen.add(key)
                mentions.append(
                    {
                        "code": normalized_code,
                        "raw": match.group(1),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )
        mentions.sort(key=lambda item: int(item["start"]))
        return mentions

    def clean_document_title(self, title: str | None) -> str | None:
        if not title:
            return None
        cleaned = re.sub(r"\s*\[[^\]]+\]\s*$", "", title).strip()
        return cleaned or None

    def looks_like_placeholder_title(self, title: str | None, file_name: str | None) -> bool:
        cleaned_title = self.clean_document_title(title)
        if not cleaned_title:
            return True
        if title and cleaned_title != title.strip():
            return True
        if not file_name:
            return False

        normalized_title = self._normalize_title_fingerprint(cleaned_title)
        normalized_stem = self._normalize_title_fingerprint(Path(file_name).stem)
        if normalized_title and normalized_title == normalized_stem:
            return True

        token_count = len(re.findall(r"[A-Za-z0-9]+", cleaned_title))
        digit_count = sum(character.isdigit() for character in cleaned_title)
        if normalized_stem and normalized_stem in normalized_title and digit_count >= 4:
            return True
        return token_count <= 2 and digit_count >= 4

    def normalize_search_text(self, value: str) -> str:
        lowered = value.lower().replace("đ", "d")
        normalized = unicodedata.normalize("NFD", lowered)
        stripped = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
        return re.sub(r"\s+", " ", stripped).strip()

    def normalize_code(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        upper_value = ascii_value.upper()

        canonical_match = CANONICAL_CODE_PATTERN.search(upper_value)
        if canonical_match:
            number, year, suffix = canonical_match.groups()
            return f"{number}/{year}/{self._canonicalize_suffix(suffix)}"

        compact = re.sub(r"[^A-Za-z0-9/._ -]+", " ", upper_value)
        compact = re.sub(r"\s+", " ", compact).strip(" ./-_")
        return compact.replace(".", "").replace("--", "-")

    def _guess_document_code(self, preview_text: str, file_name: str | None) -> str | None:
        for pattern in CODE_PATTERNS:
            match = pattern.search(preview_text)
            if match:
                return self.normalize_code(match.group(1))

        if not file_name:
            return None

        stem = Path(file_name).stem
        ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii").upper()
        match = FILENAME_CODE_PATTERN.search(ascii_stem)
        if match is None:
            return None
        number, year, suffix = match.groups()
        return self.normalize_code(f"{number}/{year}/{suffix}")

    def _guess_document_title(self, preview_text: str, document_type: str | None) -> str | None:
        lines = [self._clean_title_line(line) for line in preview_text.splitlines()]
        meaningful_lines = [line for line in lines if line]
        if not meaningful_lines:
            return None

        for index, line in enumerate(meaningful_lines[:25]):
            normalized_line = self.normalize_search_text(line)
            if self._is_header_noise_line(normalized_line):
                continue

            candidate_title = self._normalize_document_title_text(line)
            if not candidate_title:
                continue

            prefixed_title = self._prefix_title_with_document_type(candidate_title, document_type)
            if prefixed_title:
                return prefixed_title

            if index > 8:
                break

        return None

    def _guess_document_type(self, preview_text: str, document_code: str | None) -> str | None:
        lines = [line.strip() for line in preview_text.splitlines() if line.strip()]
        normalized_lines = [self.normalize_search_text(line) for line in lines[:20]]
        type_patterns = [
            ("bo luat", "bo-luat"),
            ("luat", "luat"),
            ("nghi quyet", "nghi-quyet"),
            ("nghi dinh", "nghi-dinh"),
            ("thong tu lien tich", "thong-tu-lien-tich"),
            ("thong tu", "thong-tu"),
            ("quyet dinh", "quyet-dinh"),
            ("chi thi", "chi-thi"),
            ("van ban hop nhat", "van-ban-hop-nhat"),
            ("an le", "an-le"),
        ]
        for marker, value in type_patterns:
            for line in normalized_lines:
                if line == marker or line.startswith(f"{marker} "):
                    return value

        code_upper = self.normalize_code(document_code or "")
        if "/ND-" in code_upper:
            return "nghi-dinh"
        if "/TTLT-" in code_upper:
            return "thong-tu-lien-tich"
        if "/TT-" in code_upper:
            return "thong-tu"
        if "/QD-" in code_upper:
            return "quyet-dinh"
        if "/CT-" in code_upper:
            return "chi-thi"
        if "/VBHN-" in code_upper:
            return "van-ban-hop-nhat"
        if "/NQ-" in code_upper:
            return "nghi-quyet"
        if "/QH" in code_upper or code_upper.endswith("/QH14") or code_upper.endswith("/QH15"):
            return "luat"
        return "khac"

    def _guess_issuing_authority(self, preview_text: str, document_code: str | None) -> str | None:
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
            ("van phong quoc hoi", "Văn phòng Quốc hội"),
            ("quoc hoi", "Quốc hội"),
            ("uy ban thuong vu quoc hoi", "Ủy ban Thường vụ Quốc hội"),
            ("chinh phu", "Chính phủ"),
            ("thu tuong chinh phu", "Thủ tướng Chính phủ"),
            ("bo tai nguyen va moi truong", "Bộ Tài nguyên và Môi trường"),
            ("bo nong nghiep va moi truong", "Bộ Nông nghiệp và Môi trường"),
            ("bo nong nghiep va phat trien nong thon", "Bộ Nông nghiệp và Phát triển nông thôn"),
            ("bo tai chinh", "Bộ Tài chính"),
            ("bo tu phap", "Bộ Tư pháp"),
            ("toa an nhan dan toi cao", "Tòa án nhân dân tối cao"),
            ("vien kiem sat nhan dan toi cao", "Viện kiểm sát nhân dân tối cao"),
        ]

        for pattern, label in authority_patterns:
            if pattern in normalized_text:
                return label

        code_upper = self.normalize_code(document_code or "")
        if "VBHN-VPQH" in code_upper:
            return "Văn phòng Quốc hội"
        if code_upper.endswith("/QH14") or code_upper.endswith("/QH15") or "/QH" in code_upper:
            return "Quốc hội"
        if "UBTVQH" in code_upper:
            return "Ủy ban Thường vụ Quốc hội"
        if code_upper.endswith("ND-CP") or "/ND-CP" in code_upper:
            return "Chính phủ"
        if code_upper.endswith("QD-TTG") or code_upper.endswith("CT-TTG"):
            return "Thủ tướng Chính phủ"
        if "-BTNMT" in code_upper:
            return "Bộ Tài nguyên và Môi trường"
        if "-BNNMT" in code_upper:
            return "Bộ Nông nghiệp và Môi trường"
        if "-BNNPTNT" in code_upper:
            return "Bộ Nông nghiệp và Phát triển nông thôn"
        if "-BTC" in code_upper:
            return "Bộ Tài chính"
        if "-BTP" in code_upper:
            return "Bộ Tư pháp"
        return None

    def _guess_authority_level(self, issuing_authority: str | None, document_code: str | None) -> str | None:
        normalized = self.normalize_search_text(issuing_authority or "")
        code_upper = self.normalize_code(document_code or "")
        if "van phong quoc hoi" in normalized or "VBHN-VPQH" in code_upper:
            return "van-phong-quoc-hoi"
        if "quoc hoi" in normalized or "/QH" in code_upper:
            return "quoc-hoi"
        if "uy ban thuong vu quoc hoi" in normalized or "UBTVQH" in code_upper:
            return "uy-ban-thuong-vu-quoc-hoi"
        if "thu tuong chinh phu" in normalized or code_upper.endswith("QD-TTG") or code_upper.endswith("CT-TTG"):
            return "thu-tuong-chinh-phu"
        if "chinh phu" in normalized or "/ND-CP" in code_upper:
            return "chinh-phu"
        if normalized.startswith("bo ") or re.search(r"/(TT|TTLT|QD)-B[A-Z]+", code_upper):
            return "bo"
        if "toa an nhan dan toi cao" in normalized:
            return "toa-an-nhan-dan-toi-cao"
        if "vien kiem sat nhan dan toi cao" in normalized:
            return "vien-kiem-sat-nhan-dan-toi-cao"
        return None

    def _canonicalize_suffix(self, suffix: str) -> str:
        tokens = re.findall(r"[A-Z0-9]+", suffix.upper())
        return "-".join(tokens)

    def _clean_title_line(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.strip(" -:\t"))
        return cleaned.strip()

    def _is_header_noise_line(self, normalized_line: str) -> bool:
        if not normalized_line:
            return True
        if any(pattern.search(normalized_line) for pattern in DATE_PATTERNS):
            return True
        if normalized_line.startswith(("so ", "so:", "số ", "số:", "ngay ", "ngay,", "ngay ")):
            return True
        if normalized_line.startswith(("can cu", "dieu ", "khoan ", "muc ", "chuong ", "phan ", "noi nhan", "kinh gui")):
            return True
        if normalized_line in {
            "quoc hoi",
            "van phong quoc hoi",
            "uy ban thuong vu quoc hoi",
            "chinh phu",
            "thu tuong chinh phu",
            "bo luat",
            "luat",
            "nghi quyet",
            "nghi dinh",
            "thong tu",
            "thong tu lien tich",
            "quyet dinh",
            "chi thi",
            "van ban hop nhat",
            "an le",
        }:
            return True
        if self._guess_document_code(normalized_line, None):
            return True
        return False

    def _normalize_document_title_text(self, value: str) -> str | None:
        candidate = re.sub(r"^[Vv]e\s+", "ve ", value.strip())
        candidate = re.sub(r"\s+", " ", candidate).strip(" .:-")
        if not candidate:
            return None
        if len(candidate) > MAX_DOCUMENT_TITLE_CHARS:
            return None
        if len(candidate.split()) > MAX_DOCUMENT_TITLE_WORDS:
            return None

        if candidate.upper() == candidate:
            candidate = candidate[:1].upper() + candidate[1:].lower()
        else:
            candidate = candidate[:1].upper() + candidate[1:]

        return candidate

    def _prefix_title_with_document_type(self, candidate_title: str, document_type: str | None) -> str | None:
        normalized_candidate = self.normalize_search_text(candidate_title)
        prefix = DOCUMENT_TYPE_PREFIXES.get(document_type or "")
        if not prefix:
            return candidate_title
        if normalized_candidate.startswith(self.normalize_search_text(prefix)):
            return candidate_title
        return f"{prefix} {candidate_title[:1].lower() + candidate_title[1:]}" if candidate_title else prefix

    def _normalize_title_fingerprint(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        lowered = ascii_value.lower()
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", lowered)).strip()

    def _guess_signed_date(self, preview_text: str) -> date | None:
        for line in preview_text.splitlines()[:30]:
            normalized_line = self.normalize_search_text(line)
            if normalized_line.startswith(("can cu", "dieu ", "khoan ", "muc ", "chuong ")):
                continue
            for pattern in DATE_PATTERNS:
                match = pattern.search(line)
                if match is None:
                    match = pattern.search(normalized_line)
                if match is None:
                    continue
                day, month, year = match.groups()
                try:
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        return None


legal_metadata_parser_service = LegalMetadataParserService()
