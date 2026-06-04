from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.chat import ChatSession
from src.models.legal_case import LegalCase
from src.models.planner_run import PlannerRun
from src.models.reasoning_run import ReasoningRun
from src.orchestration.tool_execution import LegalToolExecutionResult
from src.orchestration.validation_lifecycle import validation_run_lifecycle
from src.tools.search_law import SearchLawResult
from src.validation.legal_validation_coordinator import legal_validation_coordinator


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


def test_validation_lifecycle_evaluate_and_persist_needs_review_without_evidence() -> None:
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
        complexity_level="high",
        status="running",
    )
    db.add(planner_run)
    db.flush()
    reasoning_run = ReasoningRun(
        case_id=legal_case.id,
        planner_run_id=planner_run.id,
        session_id=chat_session.id,
        issue_summary="Issue",
        reasoning_graph_json="{}",
        evidence_json="[]",
        status="completed",
    )
    db.add(reasoning_run)
    db.flush()

    tool_result = LegalToolExecutionResult(
        search_results=[],
        related_articles=[],
        evidence_documents={},
        semantic_graph={},
        conflict_result=None,
        unresolved_conflict=False,
    )
    validation_result = validation_run_lifecycle.evaluate(tool_result=tool_result, detected_complexity="high")
    validation_run = validation_run_lifecycle.persist(
        db,
        case_id=legal_case.id,
        planner_run_id=planner_run.id,
        reasoning_run=reasoning_run,
        response_text="Answer",
        validation_result=validation_result,
    )

    assert validation_result.escalation_recommended is True
    assert validation_run.validation_status == "needs_review"
    assert json.loads(validation_run.findings_json)[0] == "No legal evidence was retrieved."

    db.close()

def test_validation_coordinator_flags_unsupported_legal_claims() -> None:
    db = create_test_session()
    from datetime import date

    from src.models.document import Document

    source_document = Document(
        title="Luat Dat dai",
        file_name="luat-dat-dai.txt",
        source_type="txt",
        legal_domain="dat-dai",
        authority_level="quoc-hoi",
        issuing_authority="Quoc hoi",
        document_code="31/2024/QH15",
        document_type="luat",
        normative_level=95,
        signed_date=date.today(),
        source_reference="https://example.test/luat-dat-dai",
        storage_path="docs/luat-dat-dai.txt",
        summary=None,
        effective_date=date.today(),
        legal_status="active",
        is_active=True,
    )
    db.add(source_document)
    db.flush()
    result = SearchLawResult(
        document_id=source_document.id,
        chunk_id=10,
        document_title=source_document.title,
        citation_label="Điều 10",
        hierarchy_path="Chương II > Điều 10",
        legal_status="active",
        source_reference=source_document.source_reference,
        score=90,
        excerpt="Điều 10 quy định về phân loại đất nông nghiệp và đất phi nông nghiệp.",
    )

    validation = legal_validation_coordinator.evaluate(
        retrieved_results=[result],
        evidence_documents={source_document.id: source_document},
        unresolved_conflict=False,
        detected_complexity="medium",
        related_articles=[],
        response_text="Căn cứ Điều 10, đất được phân loại thành đất nông nghiệp và đất phi nông nghiệp.\nTheo Điều 99, người dân luôn được cấp giấy chứng nhận ngay lập tức.",
    )

    assert validation.legal_claim_count == 2
    assert validation.claim_citation_support_score == 0.5
    assert any("Claim-citation-excerpt support is incomplete" in finding for finding in validation.findings)

    db.close()
