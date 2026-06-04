from src.orchestration.contracts import LegalOrchestrationResult, make_step
from src.orchestration.input_understanding import legal_input_understanding


def test_orchestration_step_serializes_metadata() -> None:
    step = make_step(
        "retrieval",
        "completed",
        detail="Retrieved legal evidence.",
        result_count=3,
        domain="dat-dai",
    )

    assert step.to_dict() == {
        "name": "retrieval",
        "status": "completed",
        "detail": "Retrieved legal evidence.",
        "metadata": {"result_count": 3, "domain": "dat-dai"},
    }


def test_orchestration_result_serializes_nested_steps() -> None:
    result = LegalOrchestrationResult(
        intent="legal_qa",
        domain="dat-dai",
        complexity="medium",
        answer_text="Draft answer",
        validation_status="pass",
        confidence_score=0.82,
        escalation_recommended=False,
        citation_count=2,
        steps=[
            make_step("input_understanding", "completed", intent="legal_qa"),
            make_step("validation", "completed", confidence_score=0.82),
        ],
    )

    serialized = result.to_dict()

    assert serialized["intent"] == "legal_qa"
    assert serialized["citation_count"] == 2
    assert serialized["steps"] == [
        {
            "name": "input_understanding",
            "status": "completed",
            "detail": None,
            "metadata": {"intent": "legal_qa"},
        },
        {
            "name": "validation",
            "status": "completed",
            "detail": None,
            "metadata": {"confidence_score": 0.82},
        },
    ]


def test_input_understanding_detects_labor_resignation_query() -> None:
    result = legal_input_understanding.analyze("Tôi muốn nghỉ việc thì cần chuẩn bị hồ sơ gì?")

    assert result.detected_domain == "lao-dong"
    assert result.detected_intent == "legal_qa"
