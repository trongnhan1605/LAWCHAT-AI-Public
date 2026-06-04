from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.agents.legal_planner import legal_planner
from src.models.chat import ChatSession
from src.models.legal_case import LegalCase
from src.models.planner_run import PlannerRun


class PlannerRunLifecycle:
    def create(
        self,
        db: Session,
        *,
        legal_case: LegalCase,
        session: ChatSession,
        query_text: str,
        detected_intent: str,
        detected_domain: str,
        complexity_level: str,
    ) -> PlannerRun:
        planner_run = PlannerRun(
            case_id=legal_case.id,
            session_id=session.id,
            user_id=session.user_id,
            query_text=query_text,
            detected_intent=detected_intent,
            detected_domain=detected_domain,
            complexity_level=complexity_level,
            status="running",
        )
        db.add(planner_run)
        db.flush()
        return planner_run

    def complete(
        self,
        planner_run: PlannerRun,
        *,
        case_id: int,
        detected_intent: str,
        detected_domain: str,
        complexity_level: str,
        search_result_count: int,
        has_related_articles: bool,
        authoritative_result_count: int,
        citation_coverage_score: float,
        related_article_count: int,
        semantic_match_count: int,
        semantic_edge_count: int,
        semantic_validation_matches: int,
        unresolved_conflict: bool,
        validation_status: str,
        escalation_recommended: bool,
    ) -> None:
        planner_run.status = "completed"
        planner_run.plan_json = json.dumps(
            legal_planner.build_plan(
                intent=detected_intent,
                domain=detected_domain,
                complexity=complexity_level,
                has_results=search_result_count > 0,
                has_related_articles=has_related_articles,
                unresolved_conflict=unresolved_conflict,
            ).to_dict(),
            ensure_ascii=False,
        )
        planner_run.context_json = json.dumps(
            {
                "case_id": case_id,
                "search_result_count": search_result_count,
                "authoritative_result_count": authoritative_result_count,
                "citation_coverage_score": citation_coverage_score,
                "related_article_count": related_article_count,
                "semantic_match_count": semantic_match_count,
                "semantic_edge_count": semantic_edge_count,
                "semantic_validation_matches": semantic_validation_matches,
                "unresolved_conflict": unresolved_conflict,
            },
            ensure_ascii=False,
        )
        planner_run.result_json = json.dumps(
            {
                "validation_status": validation_status,
                "escalation_recommended": escalation_recommended,
            },
            ensure_ascii=False,
        )

    def fail(self, planner_run: PlannerRun, *, message: str) -> None:
        planner_run.status = "failed"
        planner_run.result_json = json.dumps({"error": message}, ensure_ascii=False)


planner_run_lifecycle = PlannerRunLifecycle()
