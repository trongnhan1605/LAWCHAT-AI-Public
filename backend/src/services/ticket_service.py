from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundException, ValidationException
from src.models.case_fact import CaseFact
from src.models.chat import ChatMessage, ChatSession
from src.models.legal_case import LegalCase
from src.models.ticket import Ticket
from src.models.ticket_message import TicketMessage
from src.models.validation_run import ValidationRun

ALLOWED_STATUSES = {"new", "assigned", "in_progress", "waiting_user", "answered", "closed", "cancelled"}


class TicketService:
    def list_tickets(self, db: Session) -> list[Ticket]:
        return db.query(Ticket).order_by(Ticket.updated_at.desc(), Ticket.id.desc()).all()

    def get_ticket(self, db: Session, ticket_id: int) -> Ticket:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket is None:
            raise NotFoundException("Ticket not found")
        return ticket

    def get_ticket_detail(self, db: Session, ticket_id: int) -> tuple[Ticket, LegalCase | None, list[CaseFact], list[ValidationRun], list[ChatMessage], list[TicketMessage]]:
        ticket = self.get_ticket(db, ticket_id)
        legal_case = None
        case_facts: list[CaseFact] = []
        validation_runs: list[ValidationRun] = []
        if ticket.case_id is not None:
            legal_case = db.query(LegalCase).filter(LegalCase.id == ticket.case_id).first()
            case_facts = (
                db.query(CaseFact)
                .filter(CaseFact.case_id == ticket.case_id)
                .order_by(CaseFact.created_at.asc(), CaseFact.id.asc())
                .all()
            )
            validation_runs = (
                db.query(ValidationRun)
                .filter(ValidationRun.case_id == ticket.case_id)
                .order_by(ValidationRun.updated_at.desc(), ValidationRun.id.desc())
                .all()
            )
        session_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == ticket.session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .all()
        )
        consultant_messages = (
            db.query(TicketMessage)
            .filter(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc(), TicketMessage.id.asc())
            .all()
        )
        return ticket, legal_case, case_facts, validation_runs, session_messages, consultant_messages

    def reply_ticket(self, db: Session, ticket_id: int, sender_name: str, content: str) -> TicketMessage:
        ticket = self.get_ticket(db, ticket_id)
        message = TicketMessage(ticket_id=ticket.id, sender_type="consultant", sender_name=sender_name, content=content)
        db.add(message)
        ticket.consultant_note = content
        if ticket.status in {"new", "assigned", "in_progress"}:
            ticket.status = "answered"
        db.commit()
        db.refresh(message)
        return message

    def update_status(self, db: Session, ticket_id: int, status: str) -> Ticket:
        normalized = status.strip().lower()
        if normalized not in ALLOWED_STATUSES:
            raise ValidationException("Unsupported ticket status")

        ticket = self.get_ticket(db, ticket_id)
        ticket.status = normalized
        db.commit()
        db.refresh(ticket)
        return ticket


ticket_service = TicketService()
