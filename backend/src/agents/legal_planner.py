from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PlannerStep:
    step: str
    status: str
    detail: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LegalPlan:
    intent: str
    domain: str
    complexity: str
    steps: list[PlannerStep]

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "domain": self.domain,
            "complexity": self.complexity,
            "steps": [step.to_dict() for step in self.steps],
        }


class LegalPlanner:
    def build_plan(
        self,
        *,
        intent: str,
        domain: str,
        complexity: str,
        has_results: bool,
        has_related_articles: bool,
        unresolved_conflict: bool,
    ) -> LegalPlan:
        steps = [
            PlannerStep("classify_intent", "completed", f"intent={intent}"),
            PlannerStep("score_complexity", "completed", f"complexity={complexity}"),
            PlannerStep("retrieve_legal_evidence", "completed" if has_results else "empty", f"domain={domain}"),
            PlannerStep(
                "inspect_related_articles",
                "completed" if has_related_articles else "empty",
                "Expanded supporting context from nearby provisions." if has_related_articles else None,
            ),
            PlannerStep("check_validity", "completed" if has_results else "skipped"),
            PlannerStep(
                "resolve_conflict",
                "needs_review" if unresolved_conflict else "completed",
                "Potential legal conflict remained unresolved." if unresolved_conflict else None,
            ),
            PlannerStep("validate_response", "completed"),
            PlannerStep("escalate_if_needed", "conditional"),
        ]
        return LegalPlan(intent=intent, domain=domain, complexity=complexity, steps=steps)


legal_planner = LegalPlanner()