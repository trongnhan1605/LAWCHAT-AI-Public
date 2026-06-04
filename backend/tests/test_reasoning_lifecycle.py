from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.chat import ChatSession
from src.models.document import Document
from src.models.legal_case import LegalCase
from src.models.planner_run import PlannerRun
from src.orchestration.reasoning_lifecycle import reasoning_run_lifecycle
from src.orchestration.tool_execution import LegalToolExecutionResult
from src.tools.search_law import SearchLawResult


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


def test_reasoning_lifecycle_builds_and_persists_run() -> None:
    db = create_test_session()
    chat_session = ChatSession(session_token="token", status="active", session_type="public")
    db.add(chat_session)
    db.flush()
    legal_case = LegalCase(session_id=chat_session.id, title="Case", legal_domain="dat-dai", status="intake")
    db.add(legal_case)
    db.flush()
    planner_run = PlannerRun(
        case_id=legal_case.id,
        session_id=chat_session.id,
        query_text="Query",
        detected_intent="legal_qa",
        detected_domain="dat-dai",
        complexity_level="medium",
        status="running",
    )
    document = Document(
        id=1,
        title="Luat Dat dai",
        file_name="1.txt",
        source_type="txt",
        legal_domain="dat-dai",
        authority_level="quoc-hoi",
        issuing_authority="Quoc hoi",
        document_code="VB-1",
        document_type="luat",
        signed_date=date.today() - timedelta(days=30),
        source_reference="https://example.test/1",
        storage_path="docs/1.txt",
        effective_date=date.today() - timedelta(days=29),
        legal_status="active",
        is_seed=False,
        is_active=True,
    )
    db.add_all([planner_run, document])
    db.flush()

    search_result = SearchLawResult(
        document_id=1,
        chunk_id=None,
        document_title=document.title,
        citation_label="Dieu 1",
        hierarchy_path="Dieu 1",
        legal_status="active",
        source_reference=document.source_reference,
        score=91,
        excerpt="Evidence",
    )
    tool_result = LegalToolExecutionResult(
        search_results=[search_result],
        related_articles=[],
        evidence_documents={1: document},
        semantic_graph={},
        conflict_result=None,
        unresolved_conflict=False,
    )

    reasoning_run = reasoning_run_lifecycle.build_and_persist(
        db,
        case_id=legal_case.id,
        planner_run_id=planner_run.id,
        session_id=chat_session.id,
        content="Query",
        domain_slug="dat-dai",
        intent="legal_qa",
        tool_result=tool_result,
    )

    assert reasoning_run.status == "completed"
    assert reasoning_run.case_id == legal_case.id
    assert "Đất đai" in reasoning_run.issue_summary
    assert json.loads(reasoning_run.reasoning_graph_json)["domain"] == "dat-dai"

    db.close()
