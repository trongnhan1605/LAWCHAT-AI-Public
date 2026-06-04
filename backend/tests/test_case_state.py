from decimal import Decimal

from src.models.chat import ChatSession
from src.models.legal_case import LegalCase
from src.orchestration.case_state import legal_case_state_updater
from src.validation.legal_validation_coordinator import CoordinatedValidationResult


def test_case_state_updater_applies_escalation_outcome() -> None:
    session = ChatSession(session_token="token", status="active", session_type="public")
    legal_case = LegalCase(title="Case", legal_domain="dat-dai", status="intake")
    validation_result = CoordinatedValidationResult(
        validation_status="needs_review",
        confidence_score=0.5,
        escalation_recommended=True,
        warning_text="Review needed",
        findings=["No legal evidence was retrieved."],
        authoritative_result_count=0,
        citation_coverage_score=1.0,
        related_article_count=0,
        semantic_match_count=0,
        semantic_edge_count=0,
    )

    legal_case_state_updater.apply_answer_outcome(
        session=session,
        legal_case=legal_case,
        detected_domain="dat-dai",
        complexity_level="high",
        case_summary="summary",
        structured_facts=[{"fact_key": "raw_problem"}],
        validation_result=validation_result,
    )

    assert session.topic_guess == "dat-dai"
    assert session.last_confidence_score == Decimal("0.5")
    assert session.status == "active"
    assert legal_case.status == "needs_review"
    assert legal_case.risk_level == "high"
    assert legal_case.summary == "summary"
    assert "raw_problem" in legal_case.structured_facts_json
