from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.case_fact import CaseFact
from src.models.category import Category
from src.models.chat import ChatMessage, ChatSession
from src.models.citation import Citation
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.models.legal_case import LegalCase
from src.models.planner_run import PlannerRun
from src.models.reasoning_run import ReasoningRun
from src.models.ticket import Ticket
from src.models.user import User
from src.models.validation_run import ValidationRun
from src.services.admin_service import AdminService
from src.services.admin_review_workflow_service import AdminReviewWorkflowService
from src.services.benchmark_history_service import BenchmarkHistoryService
from src.services.legal_provision_service import legal_provision_service
from src.services.metadata_normalization_service import metadata_normalization_service


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


def seed_admin_fixture(db: Session) -> tuple[LegalCase, Ticket]:
    user = User(full_name="Admin User", email="admin@example.test", password_hash="hashed", role="admin", is_active=True)
    category = Category(name="Hon nhan", slug="hon-nhan-va-gia-dinh", description="Family law", is_active=True)
    session = ChatSession(session_token="session-1", user_id=1, session_type="public", status="active")
    document = Document(
        title="Luat Hon nhan va Gia dinh",
        file_name="family-law.txt",
        source_type="txt",
        legal_domain="hon-nhan-va-gia-dinh",
        authority_level="quoc-hoi",
        issuing_authority="Quoc hoi",
        document_code="LHNGD",
        document_type="luat",
        normative_level=95,
        signed_date=date.today() - timedelta(days=30),
        source_reference="https://example.test/family-law",
        storage_path="docs/family-law.txt",
        summary="Van ban mau",
        effective_date=date.today() - timedelta(days=25),
        expiry_date=None,
        legal_status="active",
        is_seed=False,
        is_active=True,
    )
    db.add_all([user, category, session, document])
    db.flush()

    legal_case = LegalCase(
        session_id=session.id,
        user_id=user.id,
        title="Ho so ly hon",
        legal_domain="hon-nhan-va-gia-dinh",
        status="needs_review",
        risk_level="high",
        summary="Mo ta ho so",
        desired_outcome="Can danh gia quyen nuoi con",
    )
    db.add(legal_case)
    db.flush()

    db.add_all(
        [
            ChatMessage(session_id=session.id, role="user", message_type="question", content="Toi dang ly hon", category_slug="hon-nhan-va-gia-dinh", needs_escalation=False),
            ChatMessage(session_id=session.id, role="assistant", message_type="answer", content="Can cu theo dieu 81", category_slug="hon-nhan-va-gia-dinh", needs_escalation=True),
            DocumentChunk(
                document_id=document.id,
                chunk_index=1,
                section_title="Dieu 81",
                chunk_type="article",
                citation_label="Dieu 81",
                hierarchy_path="Chuong V > Dieu 81",
                article_number="81",
                clause_number=None,
                point_number=None,
                retrieval_text="Dieu 81",
                content="Noi dung dieu 81",
                metadata_json=None,
                char_count=80,
            ),
            CaseFact(case_id=legal_case.id, fact_type="family_issue", fact_key="family_context", fact_value="Ly hon tranh chap nuoi con", is_disputed=True, confidence_score=0.8),
        ]
    )
    db.flush()

    planner_run = PlannerRun(case_id=legal_case.id, session_id=session.id, user_id=user.id, query_text="Ly hon va nuoi con", detected_intent="legal_qa", detected_domain="hon-nhan-va-gia-dinh", complexity_level="high", status="completed")
    reasoning_run = ReasoningRun(case_id=legal_case.id, planner_run_id=1, session_id=session.id, issue_summary="issue", reasoning_graph_json="{}", evidence_json="[]", status="completed")
    db.add_all([planner_run, reasoning_run])
    db.flush()

    validation_run = ValidationRun(case_id=legal_case.id, planner_run_id=planner_run.id, reasoning_run_id=reasoning_run.id, response_text="response", validation_status="needs_review", confidence_score=0.58, escalation_recommended=True, findings_json="[]")
    ticket = Ticket(session_id=session.id, case_id=legal_case.id, title="Ticket 1", topic="hon-nhan-va-gia-dinh", escalation_reason="Can review", confidence_score=0.58, status="new", priority="high")
    relation = DocumentRelation(source_document_id=document.id, target_document_id=document.id, relation_type="refers_to", relation_label="Noi bo", legal_basis="Dieu 81", confidence_score=0.6, is_active=True)
    citation = Citation(planner_run_id=planner_run.id, reasoning_run_id=reasoning_run.id, validation_run_id=1, chat_message_id=2, document_id=document.id, chunk_id=1, citation_type="legal_basis", document_title=document.title, citation_label="Dieu 81", hierarchy_path="Chuong V > Dieu 81", source_reference=document.source_reference, excerpt="Noi dung dieu 81")
    db.add_all([validation_run, ticket, relation])
    db.flush()
    citation.validation_run_id = validation_run.id
    citation.chat_message_id = 2
    citation.chunk_id = 1
    db.add(citation)
    db.commit()
    return legal_case, ticket


def test_build_overview_counts_key_operational_entities() -> None:
    db = create_test_session()
    legal_case, _ = seed_admin_fixture(db)
    service = AdminService()

    overview = service.build_overview(db)

    assert overview["total_sessions"] == 1
    assert overview["total_messages"] == 2
    assert overview["total_legal_cases"] == 1
    assert overview["active_legal_cases"] == 1
    assert overview["high_risk_legal_cases"] == 1
    assert overview["total_case_facts"] == 1
    assert overview["total_documents"] == 1
    assert overview["ingested_documents"] == 1
    assert overview["total_chunks"] == 1
    assert overview["total_document_relations"] == 1
    assert overview["total_citations"] == 1
    assert overview["total_categories"] == 1
    assert overview["active_categories"] == 1
    assert overview["total_tickets"] == 1
    assert overview["open_tickets"] == 1
    assert overview["total_planner_runs"] == 1
    assert overview["total_reasoning_runs"] == 1
    assert overview["total_validation_runs"] == 1
    assert overview["validation_runs_needing_review"] == 1
    assert overview["escalations_recommended"] == 1

    db.close()


def test_get_legal_case_detail_returns_case_runs_and_ticket_scope() -> None:
    db = create_test_session()
    legal_case, ticket = seed_admin_fixture(db)
    service = AdminService()

    loaded_case, case_facts, planner_runs, validation_runs, tickets = service.get_legal_case_detail(db, legal_case.id)

    assert loaded_case.id == legal_case.id
    assert len(case_facts) == 1
    assert case_facts[0].case_id == legal_case.id
    assert len(planner_runs) == 1
    assert planner_runs[0].case_id == legal_case.id
    assert len(validation_runs) == 1
    assert validation_runs[0].case_id == legal_case.id
    assert len(tickets) == 1
    assert tickets[0].id == ticket.id

    db.close()


def test_create_document_normalizes_metadata_and_marks_reviewed() -> None:
    db = create_test_session()
    service = AdminService()

    document = service.create_document(
        db,
        title="  luat lao dong  ",
        file_name="  luat-lao-dong .PDF ",
        source_type=" PDF ",
        legal_domain=" Lao Dong ",
        authority_level=" Quoc Hoi ",
        issuing_authority="  quoc hoi  ",
        document_code=" 12 /2024/ qh15 ",
        document_type=" Luat ",
        normative_level=95,
        signed_date=date.today(),
        source_reference=" https://example.test/luat ",
        storage_path=" docs/uploads/luat.pdf ",
        summary="  van ban ve lao dong ",
        effective_date=date.today(),
        expiry_date=None,
        legal_status=" con hieu luc ",
        is_active=True,
    )

    assert document.title == "Luat lao dong"
    assert document.source_type == "pdf"
    assert document.legal_domain == "lao-dong"
    assert document.authority_level == "quoc-hoi"
    assert document.issuing_authority == "Quoc hoi"
    assert document.document_code == "12 /2024/ QH15"
    assert document.document_type == "luat"
    assert document.legal_status == "active"
    assert document.metadata_review_status == "reviewed"
    assert document.metadata_last_reviewed_at is not None

    db.close()


def test_create_document_does_not_treat_generic_title_as_duplicate() -> None:
    db = create_test_session()
    service = AdminService()

    first = service.create_document(
        db,
        title="NGHI DINH",
        file_name="01-2024-nd-cp.docx",
        source_type="docx",
        legal_domain="dat-dai",
        authority_level="chinh-phu",
        issuing_authority="Chinh phu",
        document_code="01/2024/ND-CP",
        document_type="nghi-dinh",
        normative_level=80,
        signed_date=None,
        source_reference=None,
        storage_path="docs/uploads/01-2024-nd-cp.docx",
        summary=None,
        effective_date=None,
        expiry_date=None,
        legal_status="active",
        is_active=True,
        duplicate_action="overwrite",
    )
    second = service.create_document(
        db,
        title="NGHI DINH",
        file_name="02-2024-nd-cp.docx",
        source_type="docx",
        legal_domain="dat-dai",
        authority_level="chinh-phu",
        issuing_authority="Chinh phu",
        document_code="02/2024/ND-CP",
        document_type="nghi-dinh",
        normative_level=80,
        signed_date=None,
        source_reference=None,
        storage_path="docs/uploads/02-2024-nd-cp.docx",
        summary=None,
        effective_date=None,
        expiry_date=None,
        legal_status="active",
        is_active=True,
        duplicate_action="overwrite",
    )

    assert first.id != second.id
    assert db.query(Document).count() == 2

    db.close()

def test_admin_review_workflow_builds_operational_queues() -> None:
    db = create_test_session()
    legal_case, _ticket = seed_admin_fixture(db)
    service = AdminReviewWorkflowService()

    payload = service.build_queues(db, limit_per_queue=10)

    assert payload["summary"]["metadata_review"]["count"] == 1
    assert payload["summary"]["provision_review"]["count"] == 1
    assert payload["summary"]["validation_failures"]["count"] == 1
    validation_item = payload["queues"]["validation_failures"][0]
    assert validation_item["case_id"] == legal_case.id
    assert validation_item["source_type"] == "validation_run"

    db.close()

def test_benchmark_history_records_runs_and_exposes_failures(tmp_path) -> None:
    service = BenchmarkHistoryService(report_dir=tmp_path)
    report = {
        "status": "runtime_completed",
        "total": 1,
        "passed": 0,
        "failed": 1,
        "skipped": 0,
        "pass_rate": 0.0,
        "quick": True,
        "allow_unreviewed": True,
        "results": [
            {
                "id": "case-1",
                "status": "fail",
                "checks": [
                    {"name": "citation_present", "passed": False, "detail": "0 citations persisted"},
                    {"name": "escalation_expected", "passed": True, "detail": "expected=True, actual=True"},
                ],
            }
        ],
    }

    persisted = service.record_report(report, cases_path="benchmarks/smoke_cases.json")
    runs = service.list_runs()
    failures = service.list_failure_items()

    assert persisted["source_path"].endswith(".json")
    assert runs[0]["failed"] == 1
    assert failures[0]["source_id"] == "case-1"
    assert failures[0]["queue"] == "benchmark_failures"


def test_clear_document_provisions_removes_relations_by_provision_id() -> None:
    db = create_test_session()
    source_document = Document(title="Source", file_name="source.txt", source_type="txt", legal_domain="dat-dai", storage_path="docs/source.txt", legal_status="active", is_seed=False, is_active=True)
    target_document = Document(title="Target", file_name="target.txt", source_type="txt", legal_domain="dat-dai", storage_path="docs/target.txt", legal_status="active", is_seed=False, is_active=True)
    db.add_all([source_document, target_document])
    db.flush()
    source_provision = LegalProvision(document_id=source_document.id, provision_level="article", article_number="1", content="Dieu 1", citation_label="Dieu 1", sort_key="0001")
    target_provision = LegalProvision(document_id=target_document.id, provision_level="article", article_number="2", content="Dieu 2", citation_label="Dieu 2", sort_key="0002")
    db.add_all([source_provision, target_provision])
    db.flush()
    relation = ProvisionRelation(
        source_document_id=target_document.id,
        source_provision_id=target_provision.id,
        target_document_id=target_document.id,
        target_provision_id=source_provision.id,
        relation_type="refers_to",
        source_excerpt="Dan chieu Dieu 1",
        target_excerpt="Dieu 1",
        is_active=True,
    )
    db.add(relation)
    db.commit()

    legal_provision_service.clear_document_provisions(db, source_document.id)

    assert db.query(LegalProvision).filter(LegalProvision.document_id == source_document.id).count() == 0
    assert db.query(LegalProvision).filter(LegalProvision.document_id == target_document.id).count() == 1
    assert db.query(ProvisionRelation).count() == 0

    db.close()


def test_mark_document_metadata_reviewed_updates_status_and_notes() -> None:
    db = create_test_session()
    service = AdminService()
    document = Document(
        title="Van ban can review",
        file_name="van-ban.txt",
        source_type="txt",
        legal_domain="lao-dong",
        storage_path="docs/van-ban.txt",
        metadata_review_status="pending_review",
        legal_status="unknown",
        is_seed=False,
        is_active=True,
    )
    db.add(document)
    db.commit()

    reviewed = service.mark_document_metadata_reviewed(db, document.id, "Da xac nhan metadata chinh")

    assert reviewed.metadata_review_status == "reviewed"
    assert reviewed.metadata_review_notes == "Da xac nhan metadata chinh"
    assert reviewed.metadata_last_reviewed_at is not None

    db.close()
