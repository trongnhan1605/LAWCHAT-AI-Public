from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import pytest

import src.models  # noqa: F401
from src.core.database import Base
from src.core.exceptions import ValidationException
from src.models.case_fact import CaseFact
from src.models.chat import ChatMessage, ChatSession
from src.models.legal_case import LegalCase
from src.models.ticket import Ticket
from src.models.ticket_message import TicketMessage
from src.models.validation_run import ValidationRun
from src.services.ticket_service import TicketService


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


def seed_ticket_fixture(db: Session) -> Ticket:
    chat_session = ChatSession(session_token="ticket-session", session_type="public", status="escalated")
    db.add(chat_session)
    db.flush()

    legal_case = LegalCase(session_id=chat_session.id, title="Ho so review", legal_domain="dat-dai", status="needs_review", risk_level="high")
    db.add(legal_case)
    db.flush()

    db.add_all(
        [
            CaseFact(case_id=legal_case.id, fact_type="land_issue", fact_key="land_context", fact_value="Thu hoi dat", is_disputed=True, confidence_score=0.82),
            ValidationRun(case_id=legal_case.id, validation_status="needs_review", confidence_score=0.57, escalation_recommended=True, findings_json="[]"),
            ChatMessage(session_id=chat_session.id, role="user", message_type="question", content="Dat cua toi bi thu hoi", needs_escalation=False),
            ChatMessage(session_id=chat_session.id, role="assistant", message_type="answer", content="Can xem xet boi thuong", needs_escalation=True),
        ]
    )
    db.flush()

    ticket = Ticket(session_id=chat_session.id, case_id=legal_case.id, title="Ticket dat dai", topic="dat-dai", escalation_reason="Can review dat dai", confidence_score=0.57, status="in_progress", priority="high")
    db.add(ticket)
    db.flush()

    db.add(TicketMessage(ticket_id=ticket.id, sender_type="consultant", sender_name="Consultant", content="Dang xem xet"))
    db.commit()
    return ticket


def test_get_ticket_detail_returns_case_validation_session_and_consultant_messages() -> None:
    db = create_test_session()
    ticket = seed_ticket_fixture(db)
    service = TicketService()

    loaded_ticket, legal_case, case_facts, validation_runs, session_messages, consultant_messages = service.get_ticket_detail(db, ticket.id)

    assert loaded_ticket.id == ticket.id
    assert legal_case is not None
    assert legal_case.id == ticket.case_id
    assert len(case_facts) == 1
    assert len(validation_runs) == 1
    assert len(session_messages) == 2
    assert len(consultant_messages) == 1

    db.close()


def test_reply_ticket_updates_consultant_note_and_sets_answered_status() -> None:
    db = create_test_session()
    ticket = seed_ticket_fixture(db)
    service = TicketService()

    message = service.reply_ticket(db, ticket.id, "Reviewer", "Can doi chieu them ho so boi thuong")
    refreshed_ticket = service.get_ticket(db, ticket.id)

    assert message.ticket_id == ticket.id
    assert message.sender_name == "Reviewer"
    assert refreshed_ticket.consultant_note == "Can doi chieu them ho so boi thuong"
    assert refreshed_ticket.status == "answered"

    db.close()


def test_update_status_rejects_unsupported_value() -> None:
    db = create_test_session()
    ticket = seed_ticket_fixture(db)
    service = TicketService()

    with pytest.raises(ValidationException):
        service.update_status(db, ticket.id, "invalid-status")

    db.close()