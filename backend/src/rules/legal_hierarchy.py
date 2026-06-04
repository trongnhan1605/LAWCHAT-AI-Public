from __future__ import annotations

from dataclasses import dataclass


AUTHORITY_LEVEL_PRIORITY = {
    "quoc-hoi": 100,
    "uy-ban-thuong-vu-quoc-hoi": 95,
    "chinh-phu": 80,
    "thu-tuong-chinh-phu": 75,
    "hoi-dong-tham-phan-tandtc": 74,
    "toa-an-nhan-dan-toi-cao": 72,
    "vien-kiem-sat-nhan-dan-toi-cao": 70,
    "bo": 60,
    "uy-ban-nhan-dan": 40,
    "khac": 10,
}

DOCUMENT_TYPE_PRIORITY = {
    "bo-luat": 100,
    "luat": 95,
    "nghi-quyet": 90,
    "nghi-dinh": 80,
    "thong-tu": 60,
    "quyet-dinh": 50,
    "chi-thi": 40,
    "an-le": 65,
    "khac": 10,
}


@dataclass(frozen=True)
class HierarchySnapshot:
    document_type: str | None
    authority_level: str | None
    normative_level: int | None

    @property
    def effective_priority(self) -> int:
        if self.normative_level is not None:
            return int(self.normative_level)

        type_priority = DOCUMENT_TYPE_PRIORITY.get((self.document_type or "").strip().lower(), 0)
        authority_priority = AUTHORITY_LEVEL_PRIORITY.get((self.authority_level or "").strip().lower(), 0)
        return max(type_priority, authority_priority)


def compare_hierarchy(left: HierarchySnapshot, right: HierarchySnapshot) -> int:
    left_priority = left.effective_priority
    right_priority = right.effective_priority
    if left_priority > right_priority:
        return 1
    if left_priority < right_priority:
        return -1
    return 0
