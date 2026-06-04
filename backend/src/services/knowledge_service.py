import difflib
import json
import math
import re
import unicodedata
from datetime import date
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.logging import logger
from src.core.exceptions import NotFoundException, ValidationException
from src.core.config import settings
from src.ingestion.knowledge_ingestion_pipeline import knowledge_ingestion_pipeline
from src.ingestion.legal_chunk_builder import legal_chunk_builder
from src.ingestion.provision_sync_pipeline import provision_sync_pipeline
from src.ingestion.text_extraction import document_text_extractor
from src.models.category import Category
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.retrieval.hybrid_chunk_ranker import ChunkRankingCallbacks, hybrid_chunk_ranker
from src.services.document_relation_service import document_relation_service
from src.services.embedding_service import embedding_service
from src.services.legal_metadata_parser_service import legal_metadata_parser_service
from src.services.legal_provision_parser_service import legal_provision_parser_service
from src.services.ocr_service import ocr_service
from src.services.provision_relation_service import provision_relation_service

LEGAL_TITLE_MAX_CHARS = 220
FALLBACK_TARGET_WORDS = 220
FALLBACK_MAX_WORDS = 320
FALLBACK_OVERLAP_SEGMENTS = 1
STOPWORDS = {
    "cua",
    "cho",
    "co",
    "can",
    "cau",
    "duoc",
    "hay",
    "khi",
    "la",
    "lam",
    "nguoi",
    "nay",
    "neu",
    "nhung",
    "sau",
    "tai",
    "thi",
    "the",
    "theo",
    "toi",
    "tren",
    "va",
    "voi",
}
PART_PATTERN = re.compile(r"^(PHẦN|Phan|han)\s+(.+)$", flags=re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^(Chương|Chuong|huong)\s+(.+)$", flags=re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(Mục|Muc|uc)\s+(.+)$", flags=re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^(Điều|Dieu|ieu)\s+(\d+[A-Za-z]*)\s*[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
CLAUSE_PATTERN = re.compile(r"^((?:Khoản|Khoan|hoan)\s+)?(\d+)(?!\.\d)[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
POINT_PATTERN = re.compile(r"^((?:Điểm|Diem|iem)\s+)?([a-zđ])([\)\.:\-])?\s*(.*)$")
ROMAN_ARTICLE_PATTERN = re.compile(r"^([IVXLC]+)\.\s*(.*)$", flags=re.IGNORECASE)
OUTLINE_ARTICLE_PATTERN = re.compile(r"^(\d+)[\.\-:]\s*(.*)$")
DECIMAL_CLAUSE_PATTERN = re.compile(r"^(\d+\.\d+)[\.\-:]?\s*(.*)$")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[\.;:!?])\s+")
LEGAL_OCR_ARTICLE_BOUNDARY_PATTERN = re.compile(r"\s+(?=(Điều|Dieu)\s+\d+[A-Za-z]*)", flags=re.IGNORECASE)
LEGAL_OCR_HEADING_BOUNDARY_PATTERN = re.compile(r"\s+(?=(PHẦN|Phần|Phan|Chương|Chuong|Mục|Muc)\s+[A-Z0-9IVXLCĐđ])", flags=re.IGNORECASE)
LEGAL_OCR_NAMED_CLAUSE_BOUNDARY_PATTERN = re.compile(r"\s+(?=((Khoản|Khoan)\s+\d+\s+[A-ZĐÀÁẢÃẠĂÂa-zđ]))", flags=re.IGNORECASE)
LEGAL_OCR_NUMBERED_CLAUSE_BOUNDARY_PATTERN = re.compile(r"\s+(?=(\d+[\.:\-]\s+[A-ZĐÀÁẢÃẠĂÂa-zđ]))", flags=re.IGNORECASE)
LEGAL_OCR_SYMBOL_POINT_BOUNDARY_PATTERN = re.compile(r"\s+(?=([a-zđ][\)\.:\-]\s+[A-ZĐÀÁẢÃẠĂÂa-zđ]))", flags=re.IGNORECASE)
LEGAL_OCR_NAMED_POINT_INLINE_PATTERN = re.compile(
    r"(Điểm|Diem|ĐIỂM|DIEM)\s+([a-zđ])\s+(.*?)(?=(?:\s+(?:Điểm|Diem|ĐIỂM|DIEM)\s+[a-zđ]\s+)|$)",
)
COMMON_LEGAL_ARTICLE_TITLES = (
    "pham vi dieu chinh",
    "doi tuong ap dung",
    "giai thich tu ngu",
    "nguyen tac ap dung",
    "nguyen tac",
    "quyen va nghia vu",
    "quyen, nghia vu",
    "dieu khoan thi hanh",
    "hieu luc thi hanh",
    "trach nhiem thi hanh",
)
LEGAL_OCR_CONFUSABLE_MAP = str.maketrans({
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
})
LEGAL_OCR_SPELLING_LEXICON = {
    "ap", "biet", "bo", "ca", "cap", "chi", "chinh", "chiu", "chuong", "co", "cua", "dac", "dai",
    "dat", "dieu", "diem", "dinh", "do", "doi", "doi", "doi", "doi", "doi", "doanh", "du", "dung", "giai",
    "hanh", "hieu", "hoi", "hop", "khoan", "kien", "luat", "luc", "muc", "nghia", "nghi", "ngu",
    "nguyen", "ngoai", "nhan", "noi", "nuoc", "phep", "pham", "phu", "quoc", "quyen", "quy", "tai",
    "tac", "thich", "thi", "thong", "tiet", "to", "truong", "tu", "tuong", "van", "vi", "vu", "xet",
}
LEGAL_OCR_CANONICAL_PHRASES: tuple[tuple[str, str], ...] = (
    ("cong hoa xa hoi chu nghia viet nam", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"),
    ("doc lap tu do hanh phuc", "Độc lập - Tự do - Hạnh phúc"),
    ("chinh phu", "CHÍNH PHỦ"),
    ("nghi dinh", "NGHỊ ĐỊNH"),
    ("quyet dinh", "QUYẾT ĐỊNH"),
    ("thong tu", "THÔNG TƯ"),
    ("sua doi", "sửa đổi"),
    ("bo sung", "bổ sung"),
    ("mot so dieu", "một số điều"),
    ("cua nghi dinh so", "của Nghị định số"),
    ("quy dinh ve", "quy định về"),
    ("quy dinh chung", "QUY ĐỊNH CHUNG"),
    ("tien su dung dat", "tiền sử dụng đất"),
    ("tien thue dat", "tiền thuê đất"),
    ("quy phat trien dat", "quỹ phát triển đất"),
    ("can cu", "Căn cứ"),
    ("luat to chuc chinh phu", "Luật Tổ chức Chính phủ"),
    ("luat dat dai so", "Luật Đất đai số"),
    ("luat dat dai", "Luật Đất đai"),
    ("theo de nghi cua", "Theo đề nghị của"),
    ("bo truong bo tai chinh", "Bộ trưởng Bộ Tài chính"),
    ("pham vi dieu chinh", "Phạm vi điều chỉnh"),
    ("doi tuong ap dung", "Đối tượng áp dụng"),
    ("dieu khoan thi hanh", "Điều khoản thi hành"),
    ("hieu luc thi hanh", "Hiệu lực thi hành"),
    ("trach nhiem thi hanh", "Trách nhiệm thi hành"),
    ("giay chung nhan", "Giấy chứng nhận"),
    ("quyen su dung dat", "quyền sử dụng đất"),
    ("quyen so huu tai san gan lien voi dat", "quyền sở hữu tài sản gắn liền với đất"),
    ("quy hoach", "quy hoạch"),
    ("boi thuong", "bồi thường"),
    ("ho tro", "hỗ trợ"),
    ("tai dinh cu", "tái định cư"),
)
LEGAL_OCR_HEADING_LINE_MAP: tuple[tuple[str, str], ...] = (
    ("chinh phu", "CHÍNH PHỦ"),
    ("nghi dinh", "NGHỊ ĐỊNH"),
    ("quyet dinh", "QUYẾT ĐỊNH"),
    ("thong tu", "THÔNG TƯ"),
    ("bo tai chinh", "BỘ TÀI CHÍNH"),
    ("bo tai nguyen va moi truong", "BỘ TÀI NGUYÊN VÀ MÔI TRƯỜNG"),
)
LEGAL_OCR_HIGH_CONFIDENCE_PHRASES = {
    phrase
    for phrase, _canonical in LEGAL_OCR_CANONICAL_PHRASES
    if len(phrase.split()) >= 2
}
LEGAL_VIETNAMESE_REFERENCE_PHRASES: tuple[str, ...] = tuple(
    canonical for _, canonical in LEGAL_OCR_CANONICAL_PHRASES
) + (
    "Chính phủ",
    "Cộng hòa xã hội chủ nghĩa Việt Nam",
    "Độc lập - Tự do - Hạnh phúc",
    "Hà Nội",
    "ngày",
    "tháng",
    "năm",
    "Điều",
    "Khoản",
    "Điểm",
    "Chương",
    "Mục",
    "Phần",
    "Nghị định",
    "Quyết định",
    "Thông tư",
)
LEGAL_VIETNAMESE_SURFACE_MAP: dict[str, str] = {}
for _phrase in LEGAL_VIETNAMESE_REFERENCE_PHRASES:
    for _token in re.findall(r"[A-Za-zÀ-ỹĐđ]+", _phrase, flags=re.UNICODE):
        _normalized_token = legal_metadata_parser_service.normalize_search_text(_token.replace("Đ", "D").replace("đ", "d"))
        if _normalized_token and _normalized_token not in LEGAL_VIETNAMESE_SURFACE_MAP:
            LEGAL_VIETNAMESE_SURFACE_MAP[_normalized_token] = _token.lower()
LEGAL_VIETNAMESE_SURFACE_MAP.update({
    "so": "số",
    "mot": "một",
    "bo": "bộ",
    "sua": "sửa",
    "doi": "đổi",
    "phan": "phần",
    "muc": "mục",
    "chuong": "chương",
    "dieu": "điều",
    "khoan": "khoản",
    "diem": "điểm",
    "ngay": "ngày",
    "thang": "tháng",
    "nam": "năm",
    "ha": "hà",
    "noi": "nội",
    "dat": "đất",
    "dai": "đai",
    "nghi": "nghị",
    "dinh": "định",
    "luat": "luật",
    "chinh": "chính",
    "phu": "phủ",
    "quy": "quỹ",
    "ve": "về",
    "su": "sử",
    "dung": "dụng",
    "thue": "thuê",
    "can": "căn",
    "cu": "cứ",
})
LEGAL_SPELL_SUGGESTION_LEXICON = sorted({
    *LEGAL_OCR_SPELLING_LEXICON,
    *LEGAL_VIETNAMESE_SURFACE_MAP.keys(),
})
HIGH_CONFIDENCE_ACCENTABLE_TOKENS = {
    "chinh",
    "phu",
    "cong",
    "hoa",
    "xa",
    "hoi",
    "chu",
    "nghia",
    "viet",
    "nam",
    "doc",
    "lap",
    "tu",
    "hanh",
    "phuc",
    "nghi",
    "dinh",
    "quyet",
    "thong",
    "tu",
    "sua",
    "doi",
    "bo",
    "sung",
    "mot",
    "so",
    "dieu",
    "cua",
    "quy",
    "ve",
    "tien",
    "su",
    "dung",
    "dat",
    "thue",
    "can",
    "cu",
    "luat",
    "to",
    "chuc",
    "ngay",
    "thang",
    "nam",
    "ha",
    "noi",
}


class KnowledgeService:
    def preview_legal_ocr_correction(self, text: str) -> dict[str, object]:
        original_text = str(text or "")
        normalized_text = self.postprocess_legal_ocr_text(original_text)
        corrected_text, suggestions = self._apply_vietnamese_legal_spell_suggestions(normalized_text)
        original_tokens = [item for item in re.split(r"\s+", normalized_text.strip()) if item]
        corrected_tokens = [item for item in re.split(r"\s+", corrected_text.strip()) if item]
        changed_token_count = 0
        if suggestions:
            changed_token_count = len(suggestions)
        else:
            for original_token, corrected_token in zip(original_tokens, corrected_tokens):
                if original_token != corrected_token:
                    changed_token_count += 1
            changed_token_count += abs(len(original_tokens) - len(corrected_tokens))
        return {
            "normalized_text": normalized_text,
            "corrected_text": corrected_text,
            "changed": corrected_text != normalized_text,
            "changed_token_count": changed_token_count,
            "suggestions": suggestions,
            "review_required": bool(suggestions),
        }

    def correct_legal_ocr_spelling(self, text: str) -> str:
        corrected_tokens: list[str] = []
        for raw_token in str(text or "").split():
            corrected_tokens.append(self._correct_legal_ocr_token(raw_token))
        return " ".join(corrected_tokens)

    def postprocess_legal_ocr_text(self, text: str) -> str:
        normalized_text = self.correct_legal_ocr_spelling(str(text or "")).replace("\r\n", "\n").replace("\r", "\n")
        normalized_text = re.sub(r"[ \t]+", " ", normalized_text)
        normalized_text = LEGAL_OCR_HEADING_BOUNDARY_PATTERN.sub("\n", normalized_text)
        normalized_text = LEGAL_OCR_ARTICLE_BOUNDARY_PATTERN.sub("\n", normalized_text)
        normalized_text = LEGAL_OCR_NAMED_CLAUSE_BOUNDARY_PATTERN.sub("\n", normalized_text)
        normalized_text = LEGAL_OCR_NUMBERED_CLAUSE_BOUNDARY_PATTERN.sub("\n", normalized_text)
        normalized_text = LEGAL_OCR_SYMBOL_POINT_BOUNDARY_PATTERN.sub("\n", normalized_text)

        processed_lines: list[str] = []
        for raw_line in normalized_text.split("\n"):
            line = self._normalize_legal_ocr_line(raw_line)
            if line:
                processed_lines.extend(self._expand_inline_named_points(line))

        processed_lines = self._merge_legal_ocr_lines(processed_lines)
        processed_lines = self._split_article_title_from_body(processed_lines)
        processed_lines = [self._restore_legal_vietnamese_phrases(line) for line in processed_lines]

        return "\n".join(processed_lines).strip()

    def _correct_legal_ocr_token(self, token: str) -> str:
        match = re.match(r"^(\W*)([\wÀ-ỹ]+)(\W*)$", token, flags=re.UNICODE)
        if match is None:
            return token

        prefix, core, suffix = match.groups()
        if not core or core.isdigit() or len(core) < 2:
            return token

        normalized_core = self._normalize_ocr_candidate_token(core)
        replacement = None
        if normalized_core in LEGAL_OCR_SPELLING_LEXICON:
            replacement = normalized_core
        elif any(character.isdigit() for character in core) and len(normalized_core) >= 4 and normalized_core.isalpha():
            matches = difflib.get_close_matches(normalized_core, LEGAL_OCR_SPELLING_LEXICON, n=1, cutoff=0.84)
            replacement = matches[0] if matches else None

        if replacement is None or replacement == self._normalize_text(core):
            return token

        if core.isupper():
            rendered = replacement.upper()
        elif core[:1].isupper() and core[1:].islower():
            rendered = replacement.capitalize()
        else:
            rendered = replacement
        return f"{prefix}{rendered}{suffix}"

    def _normalize_ocr_candidate_token(self, token: str) -> str:
        candidate = str(token or "").translate(LEGAL_OCR_CONFUSABLE_MAP)
        return self._normalize_text(candidate)

    def _split_article_title_from_body(self, lines: list[str]) -> list[str]:
        normalized_lines: list[str] = []
        for line in lines:
            split_lines = self._split_single_article_title_from_body(line)
            normalized_lines.extend(split_lines)
        return normalized_lines

    def _split_single_article_title_from_body(self, line: str) -> list[str]:
        article_match = ARTICLE_PATTERN.match(line)
        if article_match is None:
            return [line]

        _, article_number, article_remainder = article_match.groups()
        remainder = article_remainder.strip()
        if not remainder:
            return [line]

        normalized_remainder = self._normalize_text(remainder)
        for title in COMMON_LEGAL_ARTICLE_TITLES:
            if not normalized_remainder.startswith(title):
                continue
            title_word_count = len(title.split())
            words = remainder.split()
            if len(words) <= title_word_count:
                return [f"Điều {article_number}. {remainder}"]

            title_text = " ".join(words[:title_word_count])
            body_text = " ".join(words[title_word_count:]).strip()
            if not body_text:
                return [f"Điều {article_number}. {title_text}"]
            return [f"Điều {article_number}. {title_text}", body_text]

        return [line]

    def _merge_legal_ocr_lines(self, lines: list[str]) -> list[str]:
        merged_lines: list[str] = []
        for line in lines:
            if not merged_lines:
                merged_lines.append(line)
                continue

            previous = merged_lines[-1]
            if self._should_attach_title_to_previous_heading(previous, line):
                merged_lines[-1] = f"{previous}. {line}" if self._is_article_heading(previous) else f"{previous} {line}"
                continue

            if self._should_merge_broken_ocr_line(previous, line):
                merged_lines[-1] = f"{previous} {line}".replace("  ", " ").strip()
                continue

            merged_lines.append(line)

        return merged_lines

    def _should_attach_title_to_previous_heading(self, previous: str, current: str) -> bool:
        if not current or self._is_structural_legal_line(current):
            return False

        if self._match_heading(previous)[0] is not None:
            return self._looks_like_legal_title_line(current)

        if self._is_article_heading(previous):
            return "." not in previous and self._looks_like_legal_title_line(current)

        return False

    def _should_merge_broken_ocr_line(self, previous: str, current: str) -> bool:
        if not previous or not current:
            return False
        if self._is_structural_legal_line(previous) or self._is_structural_legal_line(current):
            return False
        if previous.endswith((".", ";", ":", "?", "!")):
            return False
        if self._looks_like_legal_title_line(current):
            return False

        current_first = current[0]
        return current_first.islower() or current_first.isdigit() or len(previous.split()) <= 5

    def _is_structural_legal_line(self, line: str) -> bool:
        return (
            self._match_heading(line)[0] is not None
            or self._is_article_heading(line)
            or self._is_clause_heading(line)
            or self._is_point_heading(line)
        )

    def _looks_like_legal_title_line(self, line: str) -> bool:
        if not line or len(line) > LEGAL_TITLE_MAX_CHARS:
            return False
        if self._is_structural_legal_line(line):
            return False

        words = [word for word in re.split(r"\s+", line) if word]
        if len(words) < 2:
            return False

        uppercase_words = sum(1 for word in words if any(char.isalpha() for char in word) and word == word.upper())
        titlecase_words = sum(1 for word in words if any(char.isalpha() for char in word) and word[:1].isupper())
        return uppercase_words >= max(1, math.ceil(len(words) * 0.6)) or titlecase_words >= max(2, math.ceil(len(words) * 0.7))

    def _expand_inline_named_points(self, line: str) -> list[str]:
        matches = list(LEGAL_OCR_NAMED_POINT_INLINE_PATTERN.finditer(line))
        if not matches:
            return [line]

        prefix = line[:matches[0].start()].strip()
        expanded_lines = [prefix] if prefix else []
        for match in matches:
            point_label = match.group(2).lower()
            point_content = self._normalize_segment(match.group(3))
            expanded_lines.append(f"{point_label}) {point_content}" if point_content else f"{point_label})")
        return [item for item in expanded_lines if item]

    def _normalize_legal_ocr_line(self, line: str) -> str:
        normalized_line = self._normalize_segment(line)
        if not normalized_line:
            return ""

        normalized_line = re.sub(r"^(PHẦN|Phan)\b", "Phần", normalized_line, flags=re.IGNORECASE)
        normalized_line = re.sub(r"^(Chương|Chuong)\b", "Chương", normalized_line, flags=re.IGNORECASE)
        normalized_line = re.sub(r"^(Mục|Muc)\b", "Mục", normalized_line, flags=re.IGNORECASE)

        article_match = ARTICLE_PATTERN.match(normalized_line)
        if article_match:
            _, article_number, article_title = article_match.groups()
            article_title = article_title.strip()
            return f"Điều {article_number}" if not article_title else f"Điều {article_number}. {article_title}"

        clause_match = CLAUSE_PATTERN.match(normalized_line)
        if clause_match:
            clause_prefix, clause_number, clause_content = clause_match.groups()
            clause_content = clause_content.strip()
            if clause_prefix or clause_content:
                return f"{clause_number}. {clause_content}".strip()

        point_match = POINT_PATTERN.match(normalized_line)
        if point_match:
            point_prefix, point_label, _, point_content = point_match.groups()
            point_content = point_content.strip()
            if point_prefix or point_content:
                return f"{point_label.lower()}) {point_content}".strip()

        return normalized_line

    def _restore_legal_vietnamese_phrases(self, line: str) -> str:
        normalized_line = legal_metadata_parser_service.normalize_search_text(line)
        for normalized_heading, canonical_heading in LEGAL_OCR_HEADING_LINE_MAP:
            if normalized_line == normalized_heading:
                return canonical_heading

        article_match = ARTICLE_PATTERN.match(line)
        if article_match:
            _, article_number, article_title = article_match.groups()
            article_title = self._restore_phrase_text(article_title, restore_single_tokens=True).strip()
            return f"Điều {article_number}" if not article_title else f"Điều {article_number}. {article_title}"

        clause_match = CLAUSE_PATTERN.match(line)
        if clause_match:
            clause_prefix, clause_number, clause_content = clause_match.groups()
            if clause_prefix or clause_content:
                restored_content = self._restore_phrase_text(clause_content.strip(), restore_single_tokens=False).strip()
                return f"{clause_number}." if not restored_content else f"{clause_number}. {restored_content}"

        point_match = POINT_PATTERN.match(line)
        if point_match:
            point_prefix, point_label, _, point_content = point_match.groups()
            if point_prefix or point_content:
                restored_content = self._restore_phrase_text(point_content.strip(), restore_single_tokens=False).strip()
                return f"{point_label.lower()})" if not restored_content else f"{point_label.lower()}) {restored_content}"

        chapter_match = CHAPTER_PATTERN.match(line)
        if chapter_match:
            _, chapter_suffix = chapter_match.groups()
            chapter_suffix = chapter_suffix.strip()
            chapter_parts = chapter_suffix.split(maxsplit=1)
            if len(chapter_parts) == 2:
                marker, chapter_title = chapter_parts
                return f"Chương {marker} {self._restore_phrase_text(chapter_title, restore_single_tokens=True).strip()}".strip()
            return f"Chương {chapter_suffix}".strip()

        section_match = SECTION_PATTERN.match(line)
        if section_match:
            _, section_suffix = section_match.groups()
            return f"Mục {self._restore_phrase_text(section_suffix, restore_single_tokens=True).strip()}".strip()

        part_match = PART_PATTERN.match(line)
        if part_match:
            _, part_suffix = part_match.groups()
            return f"Phần {self._restore_phrase_text(part_suffix, restore_single_tokens=True).strip()}".strip()

        if self._should_restore_high_confidence_phrase_line(normalized_line):
            return self._restore_phrase_text(line, restore_single_tokens=False)
        return line

    def _restore_phrase_text(self, text: str, *, restore_single_tokens: bool = False) -> str:
        original_words = re.findall(r"[A-Za-zÀ-ỹĐđ0-9/-]+", text, flags=re.UNICODE)
        if not original_words:
            return text

        normalized_words = [
            legal_metadata_parser_service.normalize_search_text(token.replace("Đ", "D").replace("đ", "d"))
            for token in original_words
        ]

        replacement_map = {tuple(key.split()): value for key, value in LEGAL_OCR_CANONICAL_PHRASES}
        max_phrase_length = max(len(key.split()) for key, _ in LEGAL_OCR_CANONICAL_PHRASES)
        rebuilt_words: list[str] = []
        index = 0
        while index < len(normalized_words):
            replacement = None
            matched_length = 0
            for phrase_length in range(min(max_phrase_length, len(normalized_words) - index), 0, -1):
                candidate = tuple(normalized_words[index:index + phrase_length])
                replacement = replacement_map.get(candidate)
                if replacement:
                    matched_length = phrase_length
                    break
            if replacement:
                rebuilt_words.append(replacement)
                index += matched_length
            else:
                if restore_single_tokens:
                    rebuilt_words.append(self._restore_single_legal_token(normalized_words[index], original_words[index]))
                else:
                    rebuilt_words.append(original_words[index])
                index += 1

        rebuilt_line = " ".join(item for item in rebuilt_words if item)
        rebuilt_line = re.sub(r"\s+([,.;:!?])", r"\1", rebuilt_line)
        rebuilt_line = re.sub(r"\(\s+", "(", rebuilt_line)
        rebuilt_line = re.sub(r"\s+\)", ")", rebuilt_line)
        rebuilt_line = re.sub(r"\s{2,}", " ", rebuilt_line).strip()
        return rebuilt_line or text

    def _should_restore_high_confidence_phrase_line(self, normalized_line: str) -> bool:
        if not normalized_line:
            return False
        return any(phrase in normalized_line for phrase in LEGAL_OCR_HIGH_CONFIDENCE_PHRASES)

    def _restore_single_legal_token(self, normalized_token: str, original_token: str) -> str:
        token_map = {
            "dieu": "Điều",
            "khoan": "Khoản",
            "diem": "Điểm",
            "phan": "Phần",
            "chuong": "Chương",
            "muc": "Mục",
            "so": "số",
            "ngay": "ngày",
            "thang": "tháng",
            "nam": "năm",
            "ha": "Hà",
            "noi": "Nội",
            "cua": "của",
        }
        return token_map.get(normalized_token, original_token)

    def _apply_vietnamese_legal_spell_suggestions(self, text: str) -> tuple[str, list[dict[str, object]]]:
        corrected_lines: list[str] = []
        suggestions: list[dict[str, object]] = []
        for line_number, raw_line in enumerate(str(text or "").splitlines(), start=1):
            corrected_line, line_suggestions = self._apply_vietnamese_legal_spell_suggestions_to_line(raw_line, line_number)
            corrected_lines.append(corrected_line)
            suggestions.extend(line_suggestions)
        return "\n".join(corrected_lines).strip(), suggestions[:120]

    def _apply_vietnamese_legal_spell_suggestions_to_line(
        self,
        line: str,
        line_number: int,
    ) -> tuple[str, list[dict[str, object]]]:
        if not line.strip():
            return line, []

        token_matches = list(re.finditer(r"[A-Za-zÀ-ỹĐđ0-9/-]+", line, flags=re.UNICODE))
        if not token_matches:
            return line, []

        normalized_line = legal_metadata_parser_service.normalize_search_text(line)
        is_structural_line = self._is_structural_legal_line(line) or self._should_restore_high_confidence_phrase_line(normalized_line)
        rebuilt_parts: list[str] = []
        suggestions: list[dict[str, object]] = []
        previous_end = 0
        rendered_tokens: list[str] = [match.group(0) for match in token_matches]

        for token_index, match in enumerate(token_matches):
            original_token = match.group(0)
            previous_token = token_matches[token_index - 1].group(0) if token_index > 0 else None
            next_token = token_matches[token_index + 1].group(0) if token_index + 1 < len(token_matches) else None
            replacement, confidence_score, reason = self._suggest_vietnamese_legal_token(
                original_token=original_token,
                previous_token=previous_token,
                next_token=next_token,
                is_structural_line=is_structural_line,
            )
            rendered_token = replacement or original_token
            rendered_tokens[token_index] = rendered_token
            rebuilt_parts.append(line[previous_end:match.start()])
            rebuilt_parts.append(rendered_token)
            previous_end = match.end()
            if replacement and replacement != original_token:
                suggestions.append(
                    {
                        "token_index": token_index,
                        "original": original_token,
                        "corrected": replacement,
                        "confidence_score": round(confidence_score, 2),
                        "reason": reason,
                        "line_number": line_number,
                        "context_excerpt": line.strip()[:240],
                    }
                )

        rebuilt_parts.append(line[previous_end:])
        corrected_line = "".join(rebuilt_parts)
        return corrected_line, suggestions

    def _suggest_vietnamese_legal_token(
        self,
        *,
        original_token: str,
        previous_token: str | None,
        next_token: str | None,
        is_structural_line: bool,
    ) -> tuple[str | None, float, str | None]:
        token = str(original_token or "")
        if len(token) < 2:
            return None, 0.0, None

        normalized_original = legal_metadata_parser_service.normalize_search_text(token.replace("Đ", "D").replace("đ", "d"))
        normalized_candidate = self._normalize_ocr_candidate_token(token)
        if not normalized_candidate:
            return None, 0.0, None

        if self._looks_like_year_token(token):
            return None, 0.0, None

        if self._is_date_context(previous_token, next_token) and normalized_candidate in {"am", "na", "nqm", "nm", "mam"}:
            return self._render_suggested_token("năm", token), 0.94, "date_context"

        if any(character.isdigit() for character in token) and normalized_candidate in LEGAL_VIETNAMESE_SURFACE_MAP:
            surface = LEGAL_VIETNAMESE_SURFACE_MAP[normalized_candidate]
            return self._render_suggested_token(surface, token), 0.97, "ocr_confusable_character"

        if (
            is_structural_line
            and normalized_candidate in HIGH_CONFIDENCE_ACCENTABLE_TOKENS
            and normalized_candidate != "nam"
            and not self._token_has_diacritics(token)
        ):
            surface = LEGAL_VIETNAMESE_SURFACE_MAP.get(normalized_candidate)
            if surface and self._render_suggested_token(surface, token) != token:
                return self._render_suggested_token(surface, token), 0.9, "legal_heading_accent"

        if normalized_candidate not in LEGAL_SPELL_SUGGESTION_LEXICON:
            matches = difflib.get_close_matches(normalized_candidate, LEGAL_SPELL_SUGGESTION_LEXICON, n=1, cutoff=0.88)
            if matches:
                best_match = matches[0]
                surface = LEGAL_VIETNAMESE_SURFACE_MAP.get(best_match, best_match)
                rendered = self._render_suggested_token(surface, token)
                if rendered != token and (is_structural_line or any(character.isdigit() for character in token)):
                    score = max(0.82, difflib.SequenceMatcher(a=normalized_candidate, b=best_match).ratio())
                    return rendered, score, "lexicon_similarity"

        if normalized_original != normalized_candidate and normalized_candidate in LEGAL_VIETNAMESE_SURFACE_MAP and normalized_candidate != "nam":
            surface = LEGAL_VIETNAMESE_SURFACE_MAP[normalized_candidate]
            rendered = self._render_suggested_token(surface, token)
            if rendered != token and (is_structural_line or any(character.isdigit() for character in token)):
                return rendered, 0.9, "normalized_confusable_match"

        return None, 0.0, None

    def _is_date_context(self, previous_token: str | None, next_token: str | None) -> bool:
        previous_normalized = self._normalize_text(previous_token or "")
        next_normalized = self._normalize_text(next_token or "")
        return previous_normalized == "thang" or bool(re.fullmatch(r"\d{4}", next_token or ""))

    def _looks_like_year_token(self, token: str) -> bool:
        normalized = self._normalize_text(token)
        return bool(re.fullmatch(r"\d{4}", token or "")) or normalized in {"qh15", "nd", "cp"}

    def _render_suggested_token(self, surface: str, original_token: str) -> str:
        if original_token.isupper():
            return surface.upper()
        if original_token[:1].isupper() and original_token[1:].islower():
            return surface.capitalize()
        return surface

    def _token_has_diacritics(self, token: str) -> bool:
        decomposed = unicodedata.normalize("NFD", token or "")
        return any(unicodedata.category(character) == "Mn" for character in decomposed)

    def _derive_ocr_quality(
        self,
        *,
        document: Document,
        segments: list[str],
        chunk_payloads: list[tuple[str | None, str]],
        ocr_average_confidence: float | None,
        ocr_used: bool,
    ) -> tuple[float | None, str | None]:
        joined_text = "\n".join(segment for segment in segments if segment)
        if not joined_text.strip():
            return None, None

        metadata_score = self._document_metadata_quality_score(document)
        structure_score = self._document_structure_quality_score(segments, chunk_payloads)
        chunk_score = self._document_chunk_quality_score(chunk_payloads)
        cleanliness_score = self._document_text_cleanliness_score(segments, joined_text)

        if not ocr_used:
            total_score = 15.0 + cleanliness_score + structure_score + metadata_score + chunk_score
            score = round(max(0.0, min(100.0, total_score)), 2)
            if score >= 65:
                return score, "direct_text_high"
            if score >= 55:
                return score, "direct_text_medium"
            return score, "direct_text_low"

        if ocr_average_confidence is None:
            return None, None

        normalized_structure = (structure_score / 25.0) * 12.0
        normalized_metadata = (metadata_score / 25.0) * 8.0
        normalized_chunk = (chunk_score / 20.0) * 7.0
        normalized_cleanliness = (cleanliness_score / 30.0) * 3.0
        score = round(
            max(
                0.0,
                min(
                    100.0,
                    (float(ocr_average_confidence) * 0.70)
                    + normalized_structure
                    + normalized_metadata
                    + normalized_chunk
                    + normalized_cleanliness,
                ),
            ),
            2,
        )
        if score >= 90:
            return score, "ocr_high"
        if score >= 80:
            return score, "ocr_medium"
        return score, "ocr_low"

    def _document_metadata_quality_score(self, document: Document) -> float:
        fields = [
            document.document_code,
            document.document_type,
            document.issuing_authority,
            document.authority_level,
            document.signed_date,
        ]
        return float(sum(5 for value in fields if value))

    def _document_structure_quality_score(self, segments: list[str], chunk_payloads: list[tuple[str | None, str]]) -> float:
        normalized_segments = [self._normalize_text(segment) for segment in segments if segment]
        article_count = sum(1 for segment in normalized_segments if segment.startswith("dieu "))
        heading_count = sum(1 for segment in normalized_segments if segment.startswith(("phan ", "chuong ", "muc ")))
        clause_count = sum(1 for segment in normalized_segments if re.match(r"^\d+\.", segment))
        point_count = sum(1 for segment in normalized_segments if re.match(r"^[a-z][\)\.]\s+", segment))
        titled_chunk_count = sum(1 for title, _ in chunk_payloads if title and title.lower() != "preamble")

        score = 0.0
        score += min(12.0, article_count * 2.5)
        score += min(6.0, heading_count * 2.0)
        score += min(3.0, clause_count * 0.5)
        score += min(2.0, point_count * 0.35)
        score += min(4.0, titled_chunk_count * 0.35)
        return min(25.0, score)

    def _document_chunk_quality_score(self, chunk_payloads: list[tuple[str | None, str]]) -> float:
        if not chunk_payloads:
            return 0.0

        chunk_lengths = [len(content) for _, content in chunk_payloads if content]
        if not chunk_lengths:
            return 0.0

        average_length = sum(chunk_lengths) / len(chunk_lengths)
        short_chunks = sum(1 for size in chunk_lengths if size < 160)
        very_long_chunks = sum(1 for size in chunk_lengths if size > 4000)

        score = 0.0
        if 300 <= average_length <= 2200:
            score += 10.0
        elif 180 <= average_length <= 3000:
            score += 7.0
        else:
            score += 4.0

        if len(chunk_lengths) > 1:
            score += 4.0
        if len(chunk_lengths) > 5:
            score += 2.0

        short_ratio = short_chunks / len(chunk_lengths)
        long_ratio = very_long_chunks / len(chunk_lengths)
        score += max(0.0, 4.0 - (short_ratio * 8.0))
        score += max(0.0, 4.0 - (long_ratio * 10.0))
        return min(20.0, score)

    def _document_text_cleanliness_score(self, segments: list[str], joined_text: str) -> float:
        total_chars = len(joined_text)
        total_segments = max(1, len(segments))
        short_segment_ratio = sum(1 for segment in segments if self._word_count(segment) <= 3) / total_segments
        replacement_ratio = joined_text.count("\ufffd") / max(1, total_chars)

        score = 14.0
        if total_chars >= 12000:
            score += 8.0
        elif total_chars >= 3000:
            score += 6.0
        elif total_chars >= 1000:
            score += 3.0

        score += max(0.0, 6.0 - (short_segment_ratio * 18.0))
        score += max(0.0, 2.0 - (replacement_ratio * 200.0))
        return min(30.0, max(0.0, score))

    def _analyze_structure_diagnostics(self, text: str, provisions: list[LegalProvision] | None = None) -> dict[str, object]:
        joined_text = text.strip()
        drafts = legal_provision_parser_service.parse_text(joined_text) if joined_text else []
        if provisions is not None:
            article_count = sum(1 for item in provisions if item.provision_level == "article")
            clause_count = sum(1 for item in provisions if item.provision_level == "clause")
            point_count = sum(1 for item in provisions if item.provision_level == "point")
            provision_count = len(provisions)
        else:
            article_count = sum(1 for item in drafts if item.provision_level == "article")
            clause_count = sum(1 for item in drafts if item.provision_level == "clause")
            point_count = sum(1 for item in drafts if item.provision_level == "point")
            provision_count = len(drafts)
        notes: list[str] = []
        parser_source = None
        if provisions:
            for item in provisions:
                if not item.metadata_json:
                    continue
                try:
                    metadata = json.loads(item.metadata_json)
                except json.JSONDecodeError:
                    continue
                parser_source = metadata.get("parser_source") or parser_source
                if parser_source:
                    break

        if not joined_text:
            notes.append("No extracted text is available for structure parsing.")
        if joined_text and article_count == 0:
            notes.append("No article heading was detected in extracted text.")
        if article_count > 0 and clause_count == 0:
            notes.append("Article headings were detected, but no clause structure was found.")
        if clause_count > 0 and point_count == 0:
            notes.append("Clause structure was detected, but no point-level structure was found.")

        char_count = len(joined_text)
        score = 0.0
        if char_count >= 1000:
            score += 20.0
        elif char_count >= 300:
            score += 10.0
        if article_count > 0:
            score += 35.0
        if clause_count > 0:
            score += 20.0
        if point_count > 0:
            score += 10.0
        if provision_count >= article_count and provision_count > 0:
            score += 10.0
        if article_count == 0 and char_count >= 500:
            score -= 15.0
        score = max(0.0, min(100.0, score))

        if score >= 85:
            label = "high"
        elif score >= 60:
            label = "medium"
        elif score > 0:
            label = "low"
        else:
            label = "missing"

        if not notes and provision_count > 0:
            notes.append("Structure parsing found a usable legal hierarchy.")
        if parser_source == "ai_fallback":
            notes.append("AI fallback parser was used because deterministic parsing was incomplete or failed.")

        if provision_count == 0:
            status = "failed"
        elif parser_source == "ai_fallback":
            status = "parsed_with_ai_fallback"
        elif article_count > 0:
            status = "parsed"
        else:
            status = "partial"

        return {
            "parser_article_count": article_count,
            "parser_clause_count": clause_count,
            "parser_point_count": point_count,
            "parser_provision_count": provision_count,
            "structure_quality_score": round(score, 2),
            "structure_quality_label": label,
            "parser_status": status,
            "parser_notes": notes,
        }

    def _should_attempt_ai_structure_fallback(self, text: str) -> bool:
        return provision_sync_pipeline.should_attempt_ai_structure_fallback(text, knowledge_service=self)

    def _sync_document_provisions_with_fallback(self, db: Session, document: Document, extracted_text: str) -> tuple[int, str]:
        return provision_sync_pipeline.sync_document_provisions_with_fallback(
            db,
            document=document,
            extracted_text=extracted_text,
            knowledge_service=self,
        )

    def list_categories(self, db: Session) -> list[Category]:
        return db.query(Category).filter(Category.is_active == True).order_by(Category.name.asc()).all()

    def list_documents(self, db: Session) -> list[Document]:
        return db.query(Document).filter(Document.is_active == True).order_by(Document.created_at.desc()).all()

    def list_chunks(self, db: Session, document_id: int) -> list[DocumentChunk]:
        self.get_document(db, document_id)
        return (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    def list_provisions(self, db: Session, document_id: int) -> list[LegalProvision]:
        self.get_document(db, document_id)
        return (
            db.query(LegalProvision)
            .filter(LegalProvision.document_id == document_id)
            .order_by(LegalProvision.sort_key.asc(), LegalProvision.id.asc())
            .all()
        )

    def get_document(self, db: Session, document_id: int) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise NotFoundException("Document not found")
        return document

    def ingest_document(self, db: Session, document_id: int, extracted_text_override: str | None = None) -> tuple[Document, int, int]:
        document = self.get_document(db, document_id)
        result = knowledge_ingestion_pipeline.ingest_document(
            db,
            document=document,
            knowledge_service=self,
            extracted_text_override=extracted_text_override,
        )
        return result.document, result.extracted_character_count, result.chunk_count

    def refresh_document_metadata_and_relations(self, db: Session, document_id: int) -> Document:
        document = self.get_document(db, document_id)
        return knowledge_ingestion_pipeline.refresh_document_metadata_and_relations(db, document=document, knowledge_service=self)

    def ingest_all_documents(self, db: Session) -> dict:
        documents = db.query(Document).order_by(Document.created_at.desc()).all()
        ingested_documents = 0
        total_chunks = 0
        failed_documents: list[dict[str, str | int]] = []

        for document in documents:
            try:
                _, _, chunk_count = self.ingest_document(db, document.id)
                ingested_documents += 1
                total_chunks += chunk_count
            except Exception as caught:
                db.rollback()
                failed_documents.append({
                    "document_id": document.id,
                    "title": document.title,
                    "reason": str(caught),
                })

        return {
            "total_documents": len(documents),
            "ingested_documents": ingested_documents,
            "total_chunks": total_chunks,
            "failed_documents": failed_documents,
        }

    def retrieval_preview(self, db: Session, document_id: int, query: str, limit: int = 5, allow_unreviewed: bool = True) -> list[tuple[DocumentChunk, int]]:
        ranked = self._rank_chunks(db, query, limit=limit, document_id=document_id, allow_unreviewed=allow_unreviewed)
        return [(chunk, score) for _, chunk, score in ranked]

    def search_chunks(
        self,
        db: Session,
        query: str,
        limit: int = 3,
        preferred_terms: list[str] | None = None,
        legal_domain: str | None = None,
        allow_unreviewed: bool = True,
    ) -> list[tuple[Document, DocumentChunk, int]]:
        return self._rank_chunks(db, query, limit=limit, preferred_terms=preferred_terms, legal_domain=legal_domain, allow_unreviewed=allow_unreviewed)

    def diagnose_document(self, db: Session, document_id: int) -> dict:
        document = self.get_document(db, document_id)
        source_path = Path(document.storage_path)
        if not source_path.exists():
            raise NotFoundException("Document source file not found on disk")

        if document.source_type == "pdf":
            existing_provisions = self.list_provisions(db, document.id)
            reader = PdfReader(str(source_path))
            sample_pages = []
            total_chars = 0
            extracted_segments: list[str] = []
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                chars = len(text.strip())
                total_chars += chars
                if text.strip():
                    extracted_segments.append(text.strip())
                if index <= 5:
                    sample_pages.append({"page": index, "extracted_characters": chars})

            extractable = total_chars > 0
            ocr_result = ocr_service.diagnose_pdf(source_path, max_pages=5)
            ocr_sample_pages = [
                {"page": item.page, "extracted_characters": len(item.text.strip())}
                for item in (ocr_result.page_results or [])[:5]
            ]
            recommendation = (
                "PDF has extractable text and can be ingested directly."
                if extractable
                else (
                    "PDF appears image-only. OCR is available locally and can be used during ingestion."
                    if ocr_result.available
                    else "PDF appears image-only. Install Tesseract OCR locally or provide a text-based TXT/DOCX source before reliable ingestion."
                )
            )
            parsed_segments = extracted_segments if extractable else [item.text.strip() for item in ocr_result.page_results or [] if item.text.strip()]
            chunk_payloads = self._build_chunk_payloads(parsed_segments if extractable else [])
            ocr_quality_score, ocr_quality_label = self._derive_ocr_quality(
                document=document,
                segments=parsed_segments,
                chunk_payloads=chunk_payloads,
                ocr_average_confidence=ocr_result.average_confidence,
                ocr_used=not extractable,
            )
            structure_diagnostics = self._analyze_structure_diagnostics("\n".join(parsed_segments), existing_provisions)
            document.ocr_quality_score = ocr_quality_score
            document.ocr_quality_label = ocr_quality_label
            db.commit()
            return {
                "document_id": document.id,
                "source_type": document.source_type,
                "is_extractable": extractable,
                "total_pages": len(reader.pages),
                "extracted_characters": total_chars,
                "sample_pages": sample_pages,
                "ocr_available": ocr_result.available,
                "ocr_engine": ocr_result.engine,
                "ocr_recommended": not extractable,
                "ocr_applied": False,
                "ocr_average_confidence": ocr_result.average_confidence,
                "ocr_quality_score": ocr_quality_score,
                "ocr_quality_label": ocr_quality_label,
                "ocr_sample_pages": ocr_sample_pages,
                "parser_article_count": structure_diagnostics["parser_article_count"],
                "parser_clause_count": structure_diagnostics["parser_clause_count"],
                "parser_point_count": structure_diagnostics["parser_point_count"],
                "parser_provision_count": structure_diagnostics["parser_provision_count"],
                "provision_relation_count": db.query(func.count(ProvisionRelation.id)).filter(ProvisionRelation.source_document_id == document.id).scalar() or 0,
                "structure_quality_score": structure_diagnostics["structure_quality_score"],
                "structure_quality_label": structure_diagnostics["structure_quality_label"],
                "parser_status": structure_diagnostics["parser_status"],
                "parser_notes": structure_diagnostics["parser_notes"],
                "recommendation": recommendation,
            }

        extracted_text = self._extract_text(document.source_type, source_path)
        extracted_segments = self._extract_segments(document.source_type, source_path)
        existing_provisions = self.list_provisions(db, document.id)
        chunk_payloads = self._build_chunk_payloads(extracted_segments) if extracted_text.strip() else []
        ocr_quality_score, ocr_quality_label = self._derive_ocr_quality(
            document=document,
            segments=extracted_segments,
            chunk_payloads=chunk_payloads,
            ocr_average_confidence=None,
            ocr_used=False,
        )
        structure_diagnostics = self._analyze_structure_diagnostics(extracted_text, existing_provisions)
        document.ocr_quality_score = ocr_quality_score
        document.ocr_quality_label = ocr_quality_label
        db.commit()
        return {
            "document_id": document.id,
            "source_type": document.source_type,
            "is_extractable": bool(extracted_text.strip()),
            "total_pages": None,
            "extracted_characters": len(extracted_text),
            "sample_pages": [{"page": 1, "extracted_characters": len(extracted_text)}],
            "ocr_available": False,
            "ocr_engine": None,
            "ocr_recommended": False,
            "ocr_applied": False,
            "ocr_average_confidence": None,
            "ocr_quality_score": ocr_quality_score,
            "ocr_quality_label": ocr_quality_label,
            "ocr_sample_pages": [],
            "parser_article_count": structure_diagnostics["parser_article_count"],
            "parser_clause_count": structure_diagnostics["parser_clause_count"],
            "parser_point_count": structure_diagnostics["parser_point_count"],
            "parser_provision_count": structure_diagnostics["parser_provision_count"],
            "provision_relation_count": db.query(func.count(ProvisionRelation.id)).filter(ProvisionRelation.source_document_id == document.id).scalar() or 0,
            "structure_quality_score": structure_diagnostics["structure_quality_score"],
            "structure_quality_label": structure_diagnostics["structure_quality_label"],
            "parser_status": structure_diagnostics["parser_status"],
            "parser_notes": structure_diagnostics["parser_notes"],
            "recommendation": "Source is text-based and can be ingested directly." if extracted_text.strip() else "Source contains no usable text.",
        }

    def get_chunk_count(self, db: Session, document_id: int) -> int:
        return db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()

    def get_embedded_chunk_count(self, db: Session, document_id: int) -> int:
        return (
            db.query(func.count(DocumentChunkVector.id))
            .join(DocumentChunk, DocumentChunk.id == DocumentChunkVector.chunk_id)
            .filter(DocumentChunk.document_id == document_id)
            .filter(DocumentChunkVector.embedding_status == "indexed")
            .scalar()
            or 0
        )

    def get_embedding_status(self, db: Session, document_id: int) -> str:
        total_chunks = self.get_chunk_count(db, document_id)
        if total_chunks == 0:
            return "not_indexed"

        indexed_count = self.get_embedded_chunk_count(db, document_id)
        failed_count = (
            db.query(func.count(DocumentChunkVector.id))
            .join(DocumentChunk, DocumentChunk.id == DocumentChunkVector.chunk_id)
            .filter(DocumentChunk.document_id == document_id)
            .filter(DocumentChunkVector.embedding_status == "failed")
            .scalar()
            or 0
        )

        if indexed_count == total_chunks:
            return "indexed"
        if failed_count > 0 and indexed_count > 0:
            return "partial"
        if failed_count > 0:
            return "failed"
        if embedding_service.is_enabled():
            return "pending"
        return "disabled"

    def _extract_text(self, source_type: str, source_path: Path) -> str:
        return document_text_extractor.extract_text(source_type, source_path)

    def _apply_inferred_document_metadata(self, document: Document, segments: list[str]) -> None:
        preview_text = "\n".join(segment for segment in segments[:80] if segment)
        inferred = legal_metadata_parser_service.infer_document_metadata(
            file_name=document.file_name,
            preview_text=preview_text,
        )

        if inferred.get("document_title") and legal_metadata_parser_service.looks_like_placeholder_title(document.title, document.file_name):
            document.title = str(inferred["document_title"])
        if inferred.get("document_code"):
            document.document_code = str(inferred["document_code"])
        if inferred.get("document_type") and (not document.document_type or document.document_type == "khac"):
            document.document_type = str(inferred["document_type"])
        if inferred.get("issuing_authority") and not document.issuing_authority:
            document.issuing_authority = str(inferred["issuing_authority"])
        if inferred.get("authority_level") and not document.authority_level:
            document.authority_level = str(inferred["authority_level"])
        if inferred.get("signed_date") and not document.signed_date:
            document.signed_date = inferred["signed_date"]

    def _extract_segments(self, source_type: str, source_path: Path) -> list[str]:
        return document_text_extractor.extract_segments(source_type, source_path)

    def _split_plaintext_segments(self, text: str) -> list[str]:
        return document_text_extractor.split_plaintext_segments(text)

    def _normalize_segment(self, value: str) -> str:
        return document_text_extractor.normalize_segment(value)

    def _build_chunk_payloads(self, segments: list[str]) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.build_chunk_payloads(segments)

    def _build_legal_chunks(self, segments: list[str]) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.build_legal_chunks(segments)

    def _emit_preamble_chunks(self, context: dict[str, str | None], preamble_segments: list[str]) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.emit_preamble_chunks(context, preamble_segments)

    def _emit_article_chunks(
        self,
        context: dict[str, str | None],
        article_heading: str,
        body_segments: list[str],
        article_has_structure: bool,
    ) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.emit_article_chunks(context, article_heading, body_segments, article_has_structure)

    def _emit_clause_chunks(
        self,
        article_prefix: list[str],
        article_heading: str,
        clause_heading: str,
        clause_body: list[str],
    ) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.emit_clause_chunks(article_prefix, article_heading, clause_heading, clause_body)

    def _materialize_unit(self, section_title: str | None, prefix_lines: list[str], body_segments: list[str]) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.materialize_unit(section_title, prefix_lines, body_segments)

    def _context_prefix_lines(self, context: dict[str, str | None]) -> list[str]:
        return legal_chunk_builder.context_prefix_lines(context)

    def _match_heading(self, segment: str) -> tuple[str | None, str | None]:
        return legal_chunk_builder.match_heading(segment)

    def _consume_heading_with_optional_title(self, segment: str, segments: list[str], index: int) -> tuple[str, int]:
        return legal_chunk_builder.consume_heading_with_optional_title(segment, segments, index)

    def _consume_article_heading(self, segment: str, segments: list[str], index: int) -> tuple[str, str, int]:
        return legal_chunk_builder.consume_article_heading(segment, segments, index)

    def _is_heading_title_candidate(self, segment: str) -> bool:
        return legal_chunk_builder.is_heading_title_candidate(segment)

    def _is_article_heading(self, segment: str) -> bool:
        return legal_chunk_builder.is_article_heading(segment)

    def _is_roman_article_heading(self, segment: str) -> bool:
        return legal_chunk_builder.is_roman_article_heading(segment)

    def _is_outline_article_heading(self, segment: str) -> bool:
        return legal_chunk_builder.is_outline_article_heading(segment)

    def _is_clause_heading(self, segment: str) -> bool:
        return legal_chunk_builder.is_clause_heading(segment)

    def _is_point_heading(self, segment: str) -> bool:
        return legal_chunk_builder.is_point_heading(segment)

    def _article_reference(self, article_heading: str) -> str:
        return legal_chunk_builder.article_reference(article_heading)

    def _extract_clause_number(self, clause_heading: str) -> str | None:
        return legal_chunk_builder.extract_clause_number(clause_heading)

    def _extract_point_label(self, point_heading: str) -> str | None:
        return legal_chunk_builder.extract_point_label(point_heading)

    def _truncate_title(self, value: str | None) -> str | None:
        return legal_chunk_builder.truncate_title(value)

    def _build_fallback_chunks(self, segments: list[str]) -> list[tuple[str | None, str]]:
        return legal_chunk_builder.build_fallback_chunks(segments)

    def _split_segment_for_fallback(self, segment: str) -> list[str]:
        return legal_chunk_builder.split_segment_for_fallback(segment)

    def _joined_word_count(self, segments: list[str]) -> int:
        return legal_chunk_builder.joined_word_count(segments)

    def _word_count(self, text: str) -> int:
        return legal_chunk_builder.word_count(text)

    def _is_fallback_boundary(self, segment: str) -> bool:
        return legal_chunk_builder.is_fallback_boundary(segment)

    def _detect_section_title(self, chunk: str) -> str | None:
        return legal_chunk_builder.detect_section_title(chunk)

    def _build_scoring_text(self, chunk: DocumentChunk) -> str:
        if chunk.retrieval_text:
            return chunk.retrieval_text
        if chunk.section_title:
            return f"{chunk.section_title} {chunk.content}"
        return chunk.content

    def _build_chunk_metadata(self, document: Document, section_title: str | None, content: str) -> dict[str, str | None]:
        return legal_chunk_builder.build_chunk_metadata_payload(document, section_title, content)

    def _build_chunk_identifier(
        self,
        document: Document,
        article_number: str | None,
        clause_number: str | None,
        point_number: str | None,
        chunk_type: str,
    ) -> str:
        return legal_chunk_builder.build_chunk_identifier(document, article_number, clause_number, point_number, chunk_type)

    def _extract_article_number(self, article_heading: str | None) -> str | None:
        return legal_chunk_builder.extract_article_number(article_heading)

    def _slugify_path_component(self, value: str) -> str:
        return legal_chunk_builder.slugify_path_component(value)

    def _build_summary(self, text: str) -> str:
        clean = " ".join(text.split())
        return clean[:320].strip()

    def _rank_chunks(
        self,
        db: Session,
        query: str,
        limit: int,
        preferred_terms: list[str] | None = None,
        document_id: int | None = None,
        legal_domain: str | None = None,
        allow_unreviewed: bool = True,
    ) -> list[tuple[Document, DocumentChunk, int]]:
        return hybrid_chunk_ranker.rank_chunks(
            db,
            query,
            limit=limit,
            preferred_terms=preferred_terms,
            document_id=document_id,
            legal_domain=legal_domain,
            allow_unreviewed=allow_unreviewed,
            callbacks=ChunkRankingCallbacks(
                tokenize=self._tokenize,
                extract_query_references=self._extract_query_references,
                build_scoring_text=self._build_scoring_text,
                score_chunk=self._score_chunk,
                score_semantic_similarity=self._score_semantic_similarity,
                score_legal_reference_match=self._score_legal_reference_match,
                score_exact_citation_phrase=self._score_exact_citation_phrase,
                document_priority_boost=self._document_priority_boost,
            ),
        )

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._normalize_text(text)
        tokens = re.findall(r"\w+", normalized, flags=re.UNICODE)
        return [token for token in tokens if len(token) >= 3 and token not in STOPWORDS]

    def _extract_query_references(self, query: str) -> dict[str, str | None]:
        normalized = self._normalize_text(query)
        article_match = re.search(r"\bdieu\s+(\d+[a-z]*)\b", normalized)
        clause_match = re.search(r"\bkhoan\s+(\d+[a-z]*)\b", normalized)
        point_match = re.search(r"\bdiem\s+([a-z])\b", normalized)
        return {
            "article_number": article_match.group(1).lower() if article_match else None,
            "clause_number": clause_match.group(1).lower() if clause_match else None,
            "point_number": point_match.group(1).lower() if point_match else None,
        }

    def _score_semantic_similarity(self, query_vector: list[float] | None, embedding_json: str | None) -> float:
        if not query_vector or not embedding_json:
            return 0.0
        try:
            chunk_vector = json.loads(embedding_json)
        except json.JSONDecodeError:
            return 0.0
        if not isinstance(chunk_vector, list) or not chunk_vector:
            return 0.0
        if len(chunk_vector) != len(query_vector):
            return 0.0

        numerator = sum(float(left) * float(right) for left, right in zip(query_vector, chunk_vector, strict=True))
        query_norm = math.sqrt(sum(float(value) * float(value) for value in query_vector))
        chunk_norm = math.sqrt(sum(float(value) * float(value) for value in chunk_vector))
        if query_norm == 0 or chunk_norm == 0:
            return 0.0
        cosine = numerator / (query_norm * chunk_norm)
        return max(0.0, float(cosine))

    def _score_legal_reference_match(self, chunk: DocumentChunk, references: dict[str, str | None]) -> float:
        bonus = 0.0
        article_number = (chunk.article_number or "").lower()
        clause_number = (chunk.clause_number or "").lower()
        point_number = (chunk.point_number or "").lower()

        if references.get("article_number") and references["article_number"] == article_number:
            bonus += 0.22
        if references.get("clause_number") and references["clause_number"] == clause_number:
            bonus += 0.10
        if references.get("point_number") and references["point_number"] == point_number:
            bonus += 0.08
        return min(bonus, 0.34)

    def _score_exact_citation_phrase(self, chunk: DocumentChunk, query: str) -> float:
        normalized_query = self._normalize_text(query)
        citation_parts = [
            self._normalize_text(chunk.citation_label) if chunk.citation_label else "",
            self._normalize_text(chunk.section_title) if chunk.section_title else "",
        ]
        for citation_part in citation_parts:
            if citation_part and citation_part in normalized_query:
                return 0.12
        return 0.0

    def _score_chunk(self, content: str, tokens: list[str], preferred_terms: list[str], chunk_index: int) -> int:
        normalized_content = self._normalize_text(content)
        if not tokens:
            return 0

        score = sum(len(re.findall(rf"\b{re.escape(token)}\b", normalized_content)) * 3 for token in tokens)
        bigrams = [f"{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1)]
        score += sum(len(re.findall(rf"\b{re.escape(bigram)}\b", normalized_content)) * 8 for bigram in bigrams)
        if len(tokens) >= 3:
            trigram = " ".join(tokens[:3])
            score += len(re.findall(rf"\b{re.escape(trigram)}\b", normalized_content)) * 12
        for term in preferred_terms:
            normalized_term = self._normalize_text(term)
            score += len(re.findall(rf"\b{re.escape(normalized_term)}\b", normalized_content)) * 10
        if chunk_index == 1 and "demo seed" in normalized_content:
            score -= 8
        return score

    def _document_priority_boost(self, document: Document) -> int:
        boost = 0
        if document.normative_level:
            boost += max(document.normative_level // 10, 0)

        status = (document.legal_status or "active").lower()
        if status == "active":
            boost += 6
        elif status == "expired":
            boost -= 8
        elif status == "repealed":
            boost -= 12
        elif status == "draft":
            boost -= 4

        if document.effective_date and document.effective_date <= date.today():
            boost += 2

        ocr_quality_score = float(document.ocr_quality_score) if document.ocr_quality_score is not None else None
        ocr_quality_label = (document.ocr_quality_label or "").lower()
        if ocr_quality_label.startswith("direct_text"):
            boost += 10
        elif ocr_quality_label == "ocr_high":
            boost += 5
        elif ocr_quality_label in {"direct_text_medium", "ocr_medium"}:
            boost -= 1
        elif ocr_quality_label in {"direct_text_low", "ocr_low"}:
            boost -= 8

        if ocr_quality_score is not None:
            if ocr_quality_score >= 95:
                boost += 4
            elif ocr_quality_score >= 90:
                boost += 2
            elif ocr_quality_score < 85:
                boost -= 4
            elif ocr_quality_score < 75:
                boost -= 8

        if document.metadata_review_status == "pending_review" and ocr_quality_score is not None and ocr_quality_score < 85:
            boost -= 3
        return boost

    def _normalize_text(self, text: str) -> str:
        lowered = text.lower().replace("đ", "d")
        decomposed = unicodedata.normalize("NFD", lowered)
        stripped = "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
        return re.sub(r"\s+", " ", stripped).strip()


knowledge_service = KnowledgeService()
