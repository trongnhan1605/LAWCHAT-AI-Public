from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from src.models.document import Document


ACTIVE_STATUSES = {"active"}
INACTIVE_STATUSES = {"expired", "repealed"}
NON_AUTHORITATIVE_STATUSES = {"draft", "unknown"}


@dataclass(frozen=True)
class ValidityCheckResult:
    status: str
    is_currently_effective: bool
    is_authoritative: bool
    effective_date: str | None
    expiry_date: str | None
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_document_validity(document: Document, *, reference_date: date | None = None) -> ValidityCheckResult:
    today = reference_date or date.today()
    status = (document.legal_status or "unknown").strip().lower()
    reasons: list[str] = []

    if status in INACTIVE_STATUSES:
        reasons.append(f"Document status is marked as {status}.")
    elif status in NON_AUTHORITATIVE_STATUSES:
        reasons.append(f"Document status is marked as {status}.")

    if document.effective_date and document.effective_date > today:
        reasons.append(f"Document becomes effective on {document.effective_date.isoformat()}.")

    if document.expiry_date and document.expiry_date < today:
        reasons.append(f"Document expired on {document.expiry_date.isoformat()}.")

    is_currently_effective = (
        status in ACTIVE_STATUSES
        and (document.effective_date is None or document.effective_date <= today)
        and (document.expiry_date is None or document.expiry_date >= today)
    )
    is_authoritative = is_currently_effective and status not in NON_AUTHORITATIVE_STATUSES

    if is_currently_effective and not reasons:
        reasons.append("Document is active within the evaluated date range.")

    return ValidityCheckResult(
        status=status,
        is_currently_effective=is_currently_effective,
        is_authoritative=is_authoritative,
        effective_date=document.effective_date.isoformat() if document.effective_date else None,
        expiry_date=document.expiry_date.isoformat() if document.expiry_date else None,
        reasons=reasons,
    )
