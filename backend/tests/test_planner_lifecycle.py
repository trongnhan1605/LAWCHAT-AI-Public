from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.chat import ChatSession
from src.models.legal_case import LegalCase
from src.orchestration.planner_lifecycle import planner_run_lifecycle


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return session_factory()


def test_planner_lifecycle_create_and_complete() -> None:
    db = create_test_session()
    chat_session = ChatSession(session_token="token", status="active", session_type="public")
    db.add(chat_session)
    db.flush()
    legal_case = LegalCase(session_id=chat_session.id, title="Case", legal_domain="dat-dai", status="intake")
    db.add(legal_case)
    db.flush()

    planner_run = planner_run_lifecycle.create(
        db,
        legal_case=legal_case,
        session=chat_session,
        query_text="Query",
        detected_intent="legal_qa",
        detected_domain="dat-dai",
        complexity_level="medium",
    )

    planner_run_lifecycle.complete(
        planner_run,
        case_id=legal_case.id,
        detected_intent="legal_qa",
        detected_domain="dat-dai",
        complexity_level="medium",
        search_result_count=2,
        has_related_articles=True,
        authoritative_result_count=2,
        citation_coverage_score=1.0,
        related_article_count=1,
        semantic_match_count=3,
        semantic_edge_count=2,
        semantic_validation_matches=3,
        unresolved_conflict=False,
        validation_status="passed",
        escalation_recommended=False,
    )

    plan = json.loads(planner_run.plan_json)
    context = json.loads(planner_run.context_json)
    result = json.loads(planner_run.result_json)

    assert planner_run.status == "completed"
    assert plan["intent"] == "legal_qa"
    assert context["search_result_count"] == 2
    assert context["semantic_edge_count"] == 2
    assert result == {"validation_status": "passed", "escalation_recommended": False}

    db.close()


def test_planner_lifecycle_fail_records_error() -> None:
    db = create_test_session()
    chat_session = ChatSession(session_token="token", status="active", session_type="public")
    db.add(chat_session)
    db.flush()
    legal_case = LegalCase(session_id=chat_session.id, title="Case", legal_domain="dat-dai", status="intake")
    db.add(legal_case)
    db.flush()

    planner_run = planner_run_lifecycle.create(
        db,
        legal_case=legal_case,
        session=chat_session,
        query_text="Query",
        detected_intent="legal_qa",
        detected_domain="dat-dai",
        complexity_level="medium",
    )

    planner_run_lifecycle.fail(planner_run, message="Planner step failed")

    assert planner_run.status == "failed"
    assert json.loads(planner_run.result_json) == {"error": "Planner step failed"}

    db.close()
