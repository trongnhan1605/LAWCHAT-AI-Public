from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


LegalOrchestrationStepName = Literal[
    "input_understanding",
    "planning",
    "retrieval",
    "related_articles",
    "validity_check",
    "conflict_check",
    "semantic_graph",
    "reasoning_build",
    "validation",
    "answer_generation",
    "citation_persistence",
    "escalation_decision",
]

StepStatus = Literal["pending", "running", "completed", "empty", "skipped", "needs_review", "failed"]


@dataclass(frozen=True)
class LegalOrchestrationStep:
    name: LegalOrchestrationStepName
    status: StepStatus
    detail: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LegalOrchestrationResult:
    intent: str
    domain: str
    complexity: str
    answer_text: str
    validation_status: str
    confidence_score: float
    escalation_recommended: bool
    steps: list[LegalOrchestrationStep]
    planner_run_id: int | None = None
    reasoning_run_id: int | None = None
    validation_run_id: int | None = None
    assistant_message_id: int | None = None
    citation_count: int = 0

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data


def make_step(
    name: LegalOrchestrationStepName,
    status: StepStatus,
    *,
    detail: str | None = None,
    **metadata: object,
) -> LegalOrchestrationStep:
    return LegalOrchestrationStep(name=name, status=status, detail=detail, metadata=metadata)
