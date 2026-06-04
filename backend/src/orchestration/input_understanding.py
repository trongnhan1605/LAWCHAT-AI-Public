from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata


KEYWORD_CATEGORY_MAP = {
    "lao dong": "lao-dong",
    "hop dong lao dong": "lao-dong",
    "nghi viec": "lao-dong",
    "thoi viec": "lao-dong",
    "don phuong cham dut": "lao-dong",
    "bao truoc": "lao-dong",
    "tien luong": "lao-dong",
    "bao hiem xa hoi": "lao-dong",
    "sa thai": "lao-dong",
    "ky luat lao dong": "lao-dong",
    "hon nhan": "hon-nhan-va-gia-dinh",
    "ly hon": "hon-nhan-va-gia-dinh",
    "nuoi con": "hon-nhan-va-gia-dinh",
    "cap duong": "hon-nhan-va-gia-dinh",
    "ket hon": "hon-nhan-va-gia-dinh",
    "mang thai ho": "hon-nhan-va-gia-dinh",
    "dat dai": "dat-dai",
    "so do": "dat-dai",
    "thu hoi dat": "dat-dai",
    "quyen su dung dat": "dat-dai",
    "boi thuong": "dat-dai",
    "tranh chap dat": "dat-dai",
}

HIGH_RISK_TERMS = {
    "tranh chap",
    "khoi kien",
    "khieu nai",
    "to tung",
    "thu hoi dat",
    "ly hon",
    "gianh quyen nuoi con",
    "sa thai",
    "don phuong cham dut",
}

CATEGORY_RETRIEVAL_HINTS = {
    "lao-dong": [
        "lao dong",
        "hop dong lao dong",
        "nghi viec",
        "thoi viec",
        "don phuong cham dut",
        "bao truoc",
        "tien luong",
        "bao hiem xa hoi",
        "sa thai",
    ],
    "hon-nhan-va-gia-dinh": [
        "hon nhan va gia dinh",
        "ly hon",
        "nuoi con",
        "cap duong",
        "mang thai ho",
        "adoption",
    ],
    "dat-dai": [
        "dat dai",
        "quyen su dung dat",
        "thu hoi dat",
        "boi thuong",
        "so do",
        "tranh chap dat dai",
    ],
}

CATEGORY_DISPLAY_NAMES = {
    "lao-dong": "Lao động",
    "hon-nhan-va-gia-dinh": "Hôn nhân và gia đình",
    "dat-dai": "Đất đai",
}


@dataclass(frozen=True)
class InputUnderstandingResult:
    normalized_content: str
    detected_domain: str
    detected_intent: str
    complexity_level: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_legal_text(text: str) -> str:
    lowered = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
    return re.sub(r"\s+", " ", stripped).strip()


class LegalInputUnderstanding:
    def analyze(self, content: str) -> InputUnderstandingResult:
        normalized_content = normalize_legal_text(content)
        return InputUnderstandingResult(
            normalized_content=normalized_content,
            detected_domain=self.classify_category(normalized_content),
            detected_intent=self.detect_intent(normalized_content),
            complexity_level=self.score_complexity(normalized_content),
        )

    def classify_category(self, normalized_content: str) -> str:
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in normalized_content:
                return slug
        return "hon-nhan-va-gia-dinh"

    def detect_intent(self, normalized_content: str) -> str:
        if any(term in normalized_content for term in {"so sanh", "khac nhau", "xung dot"}):
            return "conflict_check"
        if any(term in normalized_content for term in {"hieu luc", "con hieu luc", "het hieu luc"}):
            return "validity_check"
        if any(term in normalized_content for term in {"tim", "tra cuu", "van ban nao", "dieu nao"}):
            return "legal_search"
        return "legal_qa"

    def score_complexity(self, normalized_content: str) -> str:
        if any(term in normalized_content for term in HIGH_RISK_TERMS):
            return "high"
        if len(normalized_content.split()) > 45:
            return "medium"
        return "low"


legal_input_understanding = LegalInputUnderstanding()
