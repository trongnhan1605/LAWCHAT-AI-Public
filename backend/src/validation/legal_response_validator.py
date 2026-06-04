from __future__ import annotations

from dataclasses import asdict, dataclass

from src.tools.search_law import SearchLawResult


@dataclass(frozen=True)
class LegalResponseValidationResult:
    validation_status: str
    confidence_score: float
    escalation_recommended: bool
    warning_text: str | None
    findings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_legal_response(
    *,
    retrieved_results: list[SearchLawResult],
    authoritative_result_count: int,
    unresolved_conflict: bool,
    detected_complexity: str,
) -> LegalResponseValidationResult:
    findings: list[str] = []
    confidence = 0.84

    if not retrieved_results:
        findings.append("No legal evidence was retrieved.")
        confidence -= 0.34
    elif len(retrieved_results) == 1:
        findings.append("Only one evidence item was retrieved.")
        confidence -= 0.08

    if authoritative_result_count == 0 and retrieved_results:
        findings.append("Retrieved evidence exists but none of it is currently authoritative.")
        confidence -= 0.22

    if unresolved_conflict:
        findings.append("Potential legal conflict could not be resolved deterministically.")
        confidence -= 0.18

    if detected_complexity == "high":
        findings.append("Case complexity is high.")
        confidence -= 0.12
    elif detected_complexity == "medium":
        confidence -= 0.05

    confidence = max(0.28, min(0.94, round(confidence, 4)))
    escalation_recommended = confidence < 0.62 or unresolved_conflict or authoritative_result_count == 0

    if escalation_recommended:
        warning_text = "Kết quả hiện cần được tư vấn viên hoặc bộ phận pháp lý rà soát thêm trước khi dùng để ra quyết định."
        validation_status = "needs_review"
    elif confidence < 0.75:
        warning_text = "Kết quả có căn cứ nhưng vẫn nên đối chiếu thêm tình tiết cụ thể của vụ việc."
        validation_status = "pass_with_warnings"
    else:
        warning_text = None
        validation_status = "passed"

    if not findings and validation_status == "passed":
        findings.append("Validation passed with authoritative evidence and no unresolved conflict.")

    return LegalResponseValidationResult(
        validation_status=validation_status,
        confidence_score=confidence,
        escalation_recommended=escalation_recommended,
        warning_text=warning_text,
        findings=findings,
    )
