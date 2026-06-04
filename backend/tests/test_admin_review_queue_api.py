from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base, get_db
from src.core.security import get_current_user
from src.main import app
from src.models.chat import ChatSession
from src.models.citation import Citation
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_case import LegalCase
from src.models.user import User
from src.models.validation_run import ValidationRun
from src.services.benchmark_history_service import benchmark_history_service
from src.services.chat_service import ChatService
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


def test_admin_review_queues_api_returns_operational_queues() -> None:
    db = create_test_session()
    admin = User(full_name="Admin User", email="admin@example.test", password_hash="hashed", role="admin", is_active=True)
    session = ChatSession(session_token="token", session_type="public", status="active")
    document = Document(
        title="Unreviewed law",
        file_name="law.txt",
        source_type="txt",
        legal_domain="dat-dai",
        storage_path="docs/law.txt",
        legal_status="unknown",
        metadata_review_status="pending_review",
        ingestion_quality_status="pending",
        retrieval_visibility="indexed_unreviewed",
        is_active=True,
    )
    db.add_all([admin, session, document])
    db.flush()
    legal_case = LegalCase(session_id=session.id, title="Case", legal_domain="dat-dai", status="needs_review")
    db.add(legal_case)
    db.flush()
    legal_case_id = legal_case.id
    db.add(
        ValidationRun(
            case_id=legal_case_id,
            response_text="response",
            validation_status="needs_review",
            confidence_score=0.5,
            escalation_recommended=True,
            findings_json='["Citation support is incomplete."]',
        )
    )
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_current_user():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        client = TestClient(app)
        response = client.get("/api/admin/review-queues?limit_per_queue=5")
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["summary"]["metadata_review"]["count"] == 1
    assert payload["summary"]["validation_failures"]["count"] == 1
    assert payload["queues"]["validation_failures"][0]["case_id"] == legal_case_id

def test_ask_flow_persists_citations_validation_and_admin_audit(monkeypatch) -> None:
    db = create_test_session()
    admin = User(full_name="Admin User", email="admin@example.test", password_hash="hashed", role="admin", is_active=True)
    document = Document(
        title="Luat Hon nhan va Gia dinh",
        file_name="family-law.txt",
        source_type="txt",
        legal_domain="hon-nhan-va-gia-dinh",
        authority_level="quoc-hoi",
        issuing_authority="Quoc hoi",
        document_code="52/2014/QH13",
        document_type="luat",
        normative_level=95,
        source_reference="https://example.test/family-law",
        storage_path="docs/family-law.txt",
        legal_status="active",
        is_active=True,
    )
    db.add_all([admin, document])
    db.flush()
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=1,
        section_title="Dieu 81",
        chunk_type="article",
        citation_label="Dieu 81",
        hierarchy_path="Chuong V > Dieu 81",
        retrieval_text="Dieu 81",
        content="Quyen nuoi con duoc xem xet theo loi ich tot nhat cua tre.",
        char_count=80,
    )
    db.add(chunk)
    db.commit()

    def fake_search_law(*_args, **_kwargs):
        return [
            SearchLawResult(
                document_id=document.id,
                chunk_id=chunk.id,
                document_title=document.title,
                citation_label=chunk.citation_label,
                hierarchy_path=chunk.hierarchy_path,
                legal_status=document.legal_status,
                source_reference=document.source_reference,
                score=95,
                excerpt=chunk.content,
            )
        ]

    monkeypatch.setattr("src.orchestration.tool_execution.search_law", fake_search_law)
    chat_service = ChatService()
    session = chat_service.create_session(db)
    chat_service.ask(db, session.session_token, "Toi dang ly hon va tranh chap quyen nuoi con.")
    legal_case = db.query(LegalCase).one()
    legal_case_id = legal_case.id
    citation_count = db.query(Citation).count()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_current_user():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        response = TestClient(app).get(f"/api/admin/legal-cases/{legal_case_id}")
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["legal_case"]["id"] == legal_case_id
    assert payload["validation_runs"][0]["validation_status"] in {"passed", "pass_with_warnings", "needs_review"}
    assert citation_count == 1

def test_benchmark_history_artifact_feeds_admin_failure_queue(tmp_path) -> None:
    db = create_test_session()
    admin = User(full_name="Admin User", email="admin@example.test", password_hash="hashed", role="admin", is_active=True)
    db.add(admin)
    db.commit()
    original_report_dir = benchmark_history_service.report_dir
    benchmark_history_service.report_dir = tmp_path
    benchmark_history_service.record_report(
        {
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
                    "checks": [{"name": "citation_present", "passed": False, "detail": "0 citations persisted"}],
                }
            ],
        },
        cases_path="benchmarks/smoke_cases.json",
    )

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_current_user():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        response = TestClient(app).get("/api/admin/review-queues?limit_per_queue=5")
    finally:
        benchmark_history_service.report_dir = original_report_dir
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 200
    benchmark_queue = response.json()["data"]["queues"]["benchmark_failures"]
    assert benchmark_queue[0]["source_type"] == "benchmark_case"
    assert benchmark_queue[0]["source_id"] == "case-1"
