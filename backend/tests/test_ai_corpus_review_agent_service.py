from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.ai_corpus_review_agent_service import ai_corpus_review_agent_service


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


def test_ai_corpus_review_agent_returns_non_authoritative_review(monkeypatch) -> None:
    db = create_test_session()
    document = Document(
        title="Nghi quyet test",
        file_name="01-2024-test.docx",
        source_type="docx",
        legal_domain="hon-nhan-va-gia-dinh",
        authority_level="hoi-dong-tham-phan-tandtc",
        issuing_authority="Hoi dong tham phan",
        document_code="01/2024/NQ-HDTP",
        document_type="nghi-quyet",
        signed_date=date(2024, 1, 1),
        source_reference="docs/legal_sources/imports/test.docx",
        storage_path="docs/legal_sources/imports/test.docx",
        legal_status="active",
        metadata_review_status="pending_review",
        ingestion_quality_status="review_required",
        retrieval_visibility="indexed_unreviewed",
        is_seed=False,
        is_active=True,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=1,
            citation_label="Dieu 1",
            retrieval_text="Dieu 1",
            content="Dieu 1. Noi dung test",
            char_count=21,
        )
    )
    db.commit()

    monkeypatch.setattr(ai_corpus_review_agent_service, "is_enabled", lambda: True)
    monkeypatch.setattr(
        ai_corpus_review_agent_service,
        "_request_openai",
        lambda **_kwargs: {
            "output_text": (
                '{"ai_review_status":"needs_human_review","risk_level":"medium",'
                '"metadata_findings":["metadata pending"],"parser_findings":[],'
                '"relation_findings":[],"suggested_metadata_updates":[],'
                '"retrieval_decision":"keep_unreviewed","reviewer_notes":"Need human review",'
                '"confidence":0.7}'
            )
        },
    )
    monkeypatch.setattr("src.services.ai_corpus_review_agent_service.ai_usage_service.log_request", lambda **_kwargs: None)

    report = ai_corpus_review_agent_service.review_pending_documents(db, max_documents=1)

    assert report["policy"]["ai_is_authoritative"] is False
    assert report["policy"]["requires_human_review"] is True
    assert report["review_count"] == 1
    assert report["reviews"][0]["requires_human_review"] is True
    assert report["reviews"][0]["ai_review_status"] == "needs_human_review"
