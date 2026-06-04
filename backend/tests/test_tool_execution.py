from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.document import Document
from src.orchestration.tool_execution import legal_tool_executor
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


def make_document(document_id: int, *, title: str, document_type: str, signed_days_ago: int) -> Document:
    return Document(
        id=document_id,
        title=title,
        file_name=f"{document_id}.txt",
        source_type="txt",
        legal_domain="dat-dai",
        authority_level="quoc-hoi",
        issuing_authority="Quoc hoi",
        document_code=f"VB-{document_id}",
        document_type=document_type,
        signed_date=date.today() - timedelta(days=signed_days_ago),
        source_reference=f"https://example.test/{document_id}",
        storage_path=f"docs/{document_id}.txt",
        effective_date=date.today() - timedelta(days=signed_days_ago - 1),
        legal_status="active",
        is_seed=False,
        is_active=True,
    )


def test_tool_executor_loads_evidence_documents_and_resolves_conflict(monkeypatch) -> None:
    db = create_test_session()
    older_document = make_document(1, title="Nghi dinh cu", document_type="nghi-dinh", signed_days_ago=60)
    newer_document = make_document(2, title="Luat moi", document_type="luat", signed_days_ago=20)
    db.add_all([older_document, newer_document])
    db.commit()

    monkeypatch.setattr(
        "src.orchestration.tool_execution.search_law",
        lambda *_args, **_kwargs: [
            SearchLawResult(
                document_id=1,
                chunk_id=None,
                document_title=older_document.title,
                citation_label="Dieu 1",
                hierarchy_path="Dieu 1",
                legal_status="active",
                source_reference=older_document.source_reference,
                score=90,
                excerpt="Older evidence",
            ),
            SearchLawResult(
                document_id=2,
                chunk_id=None,
                document_title=newer_document.title,
                citation_label="Dieu 2",
                hierarchy_path="Dieu 2",
                legal_status="active",
                source_reference=newer_document.source_reference,
                score=88,
                excerpt="Newer evidence",
            ),
        ],
    )
    monkeypatch.setattr("src.orchestration.tool_execution.get_related_articles", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("src.orchestration.tool_execution.legal_semantic_graph_service.explain_query", lambda *_args, **_kwargs: {})

    result = legal_tool_executor.execute(db, content="query", preferred_terms=[])

    assert len(result.search_results) == 2
    assert sorted(result.evidence_documents) == [1, 2]
    assert result.conflict_result is not None
    assert result.conflict_result.winner_document_id == 2
    assert result.unresolved_conflict is False

    db.close()


def test_tool_executor_searches_demo_visible_unreviewed_documents(monkeypatch) -> None:
    db = create_test_session()
    captured: dict[str, object] = {}

    def fake_search_law(*_args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("src.orchestration.tool_execution.search_law", fake_search_law)
    monkeypatch.setattr("src.orchestration.tool_execution.get_related_articles", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("src.orchestration.tool_execution.legal_semantic_graph_service.explain_query", lambda *_args, **_kwargs: {})

    result = legal_tool_executor.execute(db, content="query", preferred_terms=["lao dong"], legal_domain="lao-dong")

    assert result.search_results == []
    assert captured["allow_unreviewed"] is True
    assert captured["preferred_terms"] == ["lao dong"]
    assert captured["legal_domain"] == "lao-dong"

    db.close()
