from __future__ import annotations

from dataclasses import asdict, dataclass

from src.models.document import Document
from src.rules.legal_hierarchy import HierarchySnapshot, compare_hierarchy
from src.tools.check_validity import evaluate_document_validity


@dataclass(frozen=True)
class ConflictResolutionResult:
    winner_document_id: int | None
    loser_document_id: int | None
    resolution_basis: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def resolve_document_conflict(left: Document, right: Document) -> ConflictResolutionResult:
    reasons: list[str] = []
    left_validity = evaluate_document_validity(left)
    right_validity = evaluate_document_validity(right)

    if left_validity.is_authoritative and not right_validity.is_authoritative:
        reasons.append("Left document is authoritative while right document is not.")
        return ConflictResolutionResult(left.id, right.id, "validity", reasons)

    if right_validity.is_authoritative and not left_validity.is_authoritative:
        reasons.append("Right document is authoritative while left document is not.")
        return ConflictResolutionResult(right.id, left.id, "validity", reasons)

    hierarchy_order = compare_hierarchy(
        HierarchySnapshot(left.document_type, left.authority_level, left.normative_level),
        HierarchySnapshot(right.document_type, right.authority_level, right.normative_level),
    )
    if hierarchy_order > 0:
        reasons.append("Left document has higher legal hierarchy priority.")
        return ConflictResolutionResult(left.id, right.id, "hierarchy", reasons)
    if hierarchy_order < 0:
        reasons.append("Right document has higher legal hierarchy priority.")
        return ConflictResolutionResult(right.id, left.id, "hierarchy", reasons)

    if left.signed_date and right.signed_date:
        if left.signed_date > right.signed_date:
            reasons.append("Left document is newer by signed date.")
            return ConflictResolutionResult(left.id, right.id, "temporal_override", reasons)
        if right.signed_date > left.signed_date:
            reasons.append("Right document is newer by signed date.")
            return ConflictResolutionResult(right.id, left.id, "temporal_override", reasons)

    reasons.append("No deterministic winner could be established.")
    return ConflictResolutionResult(None, None, "unresolved", reasons)
