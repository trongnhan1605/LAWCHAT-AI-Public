from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.models.reasoning_run import ReasoningRun
from src.models.validation_run import ValidationRun
from src.orchestration.tool_execution import LegalToolExecutionResult
from src.validation.legal_validation_coordinator import CoordinatedValidationResult, legal_validation_coordinator


class ValidationRunLifecycle:
    def evaluate(
        self,
        *,
        tool_result: LegalToolExecutionResult,
        detected_complexity: str,
        response_text: str | None = None,
    ) -> CoordinatedValidationResult:
        return legal_validation_coordinator.evaluate(
            retrieved_results=tool_result.search_results,
            evidence_documents=tool_result.evidence_documents,
            unresolved_conflict=tool_result.unresolved_conflict,
            detected_complexity=detected_complexity,
            related_articles=tool_result.related_articles,
            semantic_graph=tool_result.semantic_graph,
            response_text=response_text,
        )

    def persist(
        self,
        db: Session,
        *,
        case_id: int,
        planner_run_id: int,
        reasoning_run: ReasoningRun,
        response_text: str,
        validation_result: CoordinatedValidationResult,
    ) -> ValidationRun:
        validation_run = ValidationRun(
            case_id=case_id,
            planner_run_id=planner_run_id,
            reasoning_run_id=reasoning_run.id,
            response_text=response_text,
            validation_status=validation_result.validation_status,
            confidence_score=validation_result.confidence_score,
            escalation_recommended=validation_result.escalation_recommended,
            findings_json=json.dumps(validation_result.findings, ensure_ascii=False),
        )
        db.add(validation_run)
        db.flush()
        return validation_run


validation_run_lifecycle = ValidationRunLifecycle()
