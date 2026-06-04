from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json

from src.models.chat import ChatSession
from src.models.legal_case import LegalCase
from src.validation.legal_validation_coordinator import CoordinatedValidationResult


class LegalCaseStateUpdater:
    def apply_answer_outcome(
        self,
        *,
        session: ChatSession,
        legal_case: LegalCase,
        detected_domain: str,
        complexity_level: str,
        case_summary: str,
        structured_facts: list[dict[str, object]],
        validation_result: CoordinatedValidationResult,
    ) -> None:
        session.topic_guess = detected_domain
        session.last_confidence_score = Decimal(str(validation_result.confidence_score))
        session.last_message_at = datetime.now(UTC)
        session.status = "escalated" if validation_result.escalation_recommended and session.escalated_ticket_id else "active"

        legal_case.legal_domain = detected_domain
        legal_case.risk_level = complexity_level
        legal_case.status = "needs_review" if validation_result.escalation_recommended else "analysis_ready"
        legal_case.summary = case_summary
        legal_case.structured_facts_json = json.dumps(structured_facts, ensure_ascii=False)


legal_case_state_updater = LegalCaseStateUpdater()
