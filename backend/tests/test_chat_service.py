from __future__ import annotations

from datetime import date, timedelta
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.case_fact import CaseFact
from src.models.chat import ChatSession
from src.models.citation import Citation
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_case import LegalCase
from src.models.planner_run import PlannerRun
from src.models.reasoning_run import ReasoningRun
from src.models.ticket import Ticket
from src.models.validation_run import ValidationRun
from src.services.bootstrap_service import ensure_seed_data
from src.services.chat_service import ChatService
from src.tools.search_law import SearchLawResult


def make_document(document_id: int, *, title: str, document_type: str, authority_level: str, signed_days_ago: int) -> Document:
    return Document(
        id=document_id,
        title=title,
        file_name=f"{document_id}.txt",
        source_type="txt",
        legal_domain="hon-nhan-va-gia-dinh",
        authority_level=authority_level,
        issuing_authority="Quoc hoi",
        document_code=f"VB-{document_id}",
        document_type=document_type,
        normative_level=None,
        signed_date=date.today() - timedelta(days=signed_days_ago),
        source_reference=f"https://example.test/{document_id}",
        storage_path=f"docs/{document_id}.txt",
        summary="Van ban phap ly mau",
        effective_date=date.today() - timedelta(days=signed_days_ago - 1),
        expiry_date=None,
        legal_status="active",
        is_seed=False,
        is_active=True,
    )


def make_chunk(chunk_id: int, document_id: int, citation_label: str) -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        chunk_index=1,
        section_title=citation_label,
        chunk_type="article",
        citation_label=citation_label,
        hierarchy_path=f"Chuong I > {citation_label}",
        article_number="1",
        clause_number=None,
        point_number=None,
        retrieval_text=citation_label,
        content=f"Noi dung cua {citation_label}",
        metadata_json=None,
        char_count=120,
    )


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


def test_chat_service_ask_creates_case_runs_messages_and_citations(monkeypatch) -> None:
    db = create_test_session()
    service = ChatService()

    primary_document = make_document(
        1,
        title="Luat Hon nhan va Gia dinh",
        document_type="luat",
        authority_level="quoc-hoi",
        signed_days_ago=30,
    )
    secondary_document = make_document(
        2,
        title="Nghi dinh Huong dan",
        document_type="nghi-dinh",
        authority_level="chinh-phu",
        signed_days_ago=15,
    )
    db.add_all(
        [
            primary_document,
            secondary_document,
            make_chunk(101, 1, "Dieu 81"),
            make_chunk(102, 2, "Dieu 12"),
        ]
    )
    db.commit()

    def fake_search_law(*_args, **_kwargs):
        return [
            SearchLawResult(
                document_id=1,
                chunk_id=101,
                document_title=primary_document.title,
                citation_label="Dieu 81",
                hierarchy_path="Chuong V > Dieu 81",
                legal_status="active",
                source_reference=primary_document.source_reference,
                score=96,
                excerpt="Quyen nuoi con duoc xem xet theo loi ich tot nhat cua tre.",
            ),
            SearchLawResult(
                document_id=2,
                chunk_id=102,
                document_title=secondary_document.title,
                citation_label="Dieu 12",
                hierarchy_path="Chuong II > Dieu 12",
                legal_status="active",
                source_reference=secondary_document.source_reference,
                score=89,
                excerpt="Huong dan bo sung ve viec xac dinh nguoi truc tiep nuoi con.",
            ),
        ]

    monkeypatch.setattr("src.orchestration.tool_execution.search_law", fake_search_law)

    session = service.create_session(db)
    persisted_session, user_message, assistant_message = service.ask(
        db,
        session.session_token,
        "Toi dang ly hon va tranh chap quyen nuoi con, can biet can cu phap ly nao ap dung.",
    )

    legal_case = db.query(LegalCase).one()
    planner_run = db.query(PlannerRun).one()
    reasoning_run = db.query(ReasoningRun).one()
    validation_run = db.query(ValidationRun).one()
    case_facts = db.query(CaseFact).all()
    citations = db.query(Citation).order_by(Citation.id.asc()).all()

    assert persisted_session.id == session.id
    assert persisted_session.topic_guess == "hon-nhan-va-gia-dinh"
    assert legal_case.session_id == session.id
    assert legal_case.risk_level == "high"
    assert legal_case.status == "analysis_ready"
    assert planner_run.case_id == legal_case.id
    assert planner_run.status == "completed"
    assert reasoning_run.case_id == legal_case.id
    assert reasoning_run.status == "completed"
    assert validation_run.case_id == legal_case.id
    assert validation_run.validation_status == "pass_with_warnings"
    assert float(validation_run.confidence_score) == 0.67
    assert validation_run.escalation_recommended is False
    assert len(case_facts) >= 1
    assert len(citations) == 2
    assert user_message.role == "user"
    assert assistant_message.role == "assistant"
    assert assistant_message.citation_title == primary_document.title
    assert assistant_message.needs_escalation is False
    assert "Khuyen nghi" in assistant_message.content or "Khuyến nghị" in assistant_message.content

    db.close()


def test_chat_service_escalate_creates_single_ticket_for_session(monkeypatch) -> None:
    db = create_test_session()
    service = ChatService()

    document = make_document(
        1,
        title="Luật Hôn nhân và Gia đình",
        document_type="luat",
        authority_level="quoc-hoi",
        signed_days_ago=30,
    )
    db.add_all([document, make_chunk(101, 1, "Dieu 56")])
    db.commit()

    monkeypatch.setattr(
        "src.orchestration.tool_execution.search_law",
        lambda *_args, **_kwargs: [
            SearchLawResult(
                document_id=1,
                chunk_id=101,
                document_title=document.title,
                citation_label="Dieu 56",
                hierarchy_path="Chuong IV > Dieu 56",
                legal_status="active",
                source_reference=document.source_reference,
                score=91,
                excerpt="Ly hon theo yeu cau cua mot ben.",
            )
        ],
    )

    session = service.create_session(db)
    service.ask(db, session.session_token, "Toi muon ly hon don phuong va can duoc ho tro them.")

    first_ticket = service.escalate(db, session.session_token, "Can tu van vien xem xet them")
    second_ticket = service.escalate(db, session.session_token, "Ly do moi nhung khong duoc tao ticket moi")
    persisted_session = db.query(ChatSession).filter(ChatSession.id == session.id).one()

    assert first_ticket.id == second_ticket.id
    assert persisted_session.status == "escalated"
    assert persisted_session.escalated_ticket_id == first_ticket.id
    assert db.query(Ticket).count() == 1

    db.close()


def test_chat_service_reasoning_graph_includes_semantic_path_for_land_query(monkeypatch) -> None:
    db = create_test_session()
    ensure_seed_data(db)
    service = ChatService()

    investment_document = make_document(
        11,
        title="Luat Dau tu",
        document_type="luat",
        authority_level="quoc-hoi",
        signed_days_ago=40,
    )
    enterprise_document = make_document(
        12,
        title="Luat Doanh nghiep",
        document_type="luat",
        authority_level="quoc-hoi",
        signed_days_ago=35,
    )
    land_document = make_document(
        13,
        title="Luat Dat dai",
        document_type="luat",
        authority_level="quoc-hoi",
        signed_days_ago=25,
    )
    for document in (investment_document, enterprise_document, land_document):
        document.legal_domain = "dat-dai"

    db.add_all(
        [
            investment_document,
            enterprise_document,
            land_document,
            make_chunk(201, 11, "Dieu 23"),
            make_chunk(202, 12, "Dieu 22"),
            make_chunk(203, 13, "Dieu 28"),
        ]
    )
    db.commit()
    ensure_seed_data(db)

    monkeypatch.setattr(
        "src.orchestration.tool_execution.search_law",
        lambda *_args, **_kwargs: [
            SearchLawResult(
                document_id=11,
                chunk_id=201,
                document_title=investment_document.title,
                citation_label="Dieu 23",
                hierarchy_path="Chuong IV > Dieu 23",
                legal_status="active",
                source_reference=investment_document.source_reference,
                score=94,
                excerpt="Nha dau tu nuoc ngoai thuc hien hoat dong dau tu theo dieu kien tuong ung.",
            ),
            SearchLawResult(
                document_id=13,
                chunk_id=203,
                document_title=land_document.title,
                citation_label="Dieu 28",
                hierarchy_path="Chuong III > Dieu 28",
                legal_status="active",
                source_reference=land_document.source_reference,
                score=91,
                excerpt="To chuc kinh te co von dau tu nuoc ngoai duoc xem xet quyen lien quan den dat dai theo dieu kien luat dinh.",
            ),
        ],
    )

    session = service.create_session(db)
    _, _, assistant_message = service.ask(
        db,
        session.session_token,
        "Nha dau tu nuoc ngoai thanh lap doanh nghiep tai Viet Nam thi co duoc nhan chuyen nhuong quyen su dung dat khong?",
    )

    reasoning_run = db.query(ReasoningRun).order_by(ReasoningRun.id.desc()).first()
    assert reasoning_run is not None
    reasoning_graph = __import__("json").loads(reasoning_run.reasoning_graph_json)
    semantic_path = reasoning_graph.get("semantic_path")
    assert semantic_path is not None
    assert len(semantic_path.get("matched_concepts", [])) >= 3
    edge_types = {edge["edge_type"] for edge in semantic_path.get("edges", [])}
    assert "CREATES_ENTITY" in edge_types
    assert "ENABLES_RIGHT" in edge_types
    assert "Đường suy luận ngữ nghĩa" in assistant_message.content
    assert "Căn cứ cho đường suy luận" in assistant_message.content
    assert "Quyền sử dụng đất" in assistant_message.content or "quyen su dung dat" in assistant_message.content

    db.close()


def test_chat_service_ask_without_evidence_records_validation_and_escalation_flag(monkeypatch) -> None:
    db = create_test_session()
    service = ChatService()

    monkeypatch.setattr("src.orchestration.tool_execution.search_law", lambda *_args, **_kwargs: [])

    session = service.create_session(db)
    _, _, assistant_message = service.ask(
        db,
        session.session_token,
        "Toi dang co tranh chap phuc tap va can biet can cu phap ly nao ap dung.",
    )

    legal_case = db.query(LegalCase).one()
    planner_run = db.query(PlannerRun).one()
    reasoning_run = db.query(ReasoningRun).one()
    validation_run = db.query(ValidationRun).one()

    plan = json.loads(planner_run.plan_json)
    context = json.loads(planner_run.context_json)
    findings = json.loads(validation_run.findings_json)

    assert legal_case.status == "needs_review"
    assert planner_run.status == "completed"
    assert reasoning_run.status == "completed"
    assert validation_run.validation_status == "needs_review"
    assert validation_run.escalation_recommended is True
    assert assistant_message.needs_escalation is True
    assert assistant_message.citation_title is None
    assert db.query(Citation).count() == 0
    assert context["search_result_count"] == 0
    assert context["citation_coverage_score"] == 1.0
    assert any(step["step"] == "retrieve_legal_evidence" and step["status"] == "empty" for step in plan["steps"])
    assert "No legal evidence was retrieved." in findings

    db.close()
