from __future__ import annotations

import json

from sqlalchemy.orm import Session

from src.models.reasoning_run import ReasoningRun
from src.orchestration.input_understanding import CATEGORY_DISPLAY_NAMES
from src.orchestration.tool_execution import LegalToolExecutionResult
from src.reasoning.legal_reasoning_builder import legal_reasoning_builder


class ReasoningRunLifecycle:
    def build_and_persist(
        self,
        db: Session,
        *,
        case_id: int,
        planner_run_id: int,
        session_id: int,
        content: str,
        domain_slug: str,
        intent: str,
        tool_result: LegalToolExecutionResult,
    ) -> ReasoningRun:
        domain_name = CATEGORY_DISPLAY_NAMES.get(domain_slug, domain_slug)
        reasoning_artifact = legal_reasoning_builder.build_artifact(
            content=content,
            domain_name=domain_name,
            domain_slug=domain_slug,
            intent=intent,
            search_results=tool_result.search_results,
            evidence_documents=tool_result.evidence_documents,
            related_articles=tool_result.related_articles,
            conflict_result=tool_result.conflict_result,
            semantic_graph=tool_result.semantic_graph,
        )

        reasoning_run = ReasoningRun(
            case_id=case_id,
            planner_run_id=planner_run_id,
            session_id=session_id,
            issue_summary=reasoning_artifact.issue_summary,
            reasoning_graph_json=json.dumps(reasoning_artifact.reasoning_graph, ensure_ascii=False),
            evidence_json=json.dumps(reasoning_artifact.evidence_summary, ensure_ascii=False),
            status="completed",
        )
        db.add(reasoning_run)
        db.flush()
        return reasoning_run


reasoning_run_lifecycle = ReasoningRunLifecycle()
