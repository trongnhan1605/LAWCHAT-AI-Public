from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import require_roles
from src.schemas.ticket_schema import SessionMessagePayload, TicketCaseFactPayload, TicketDetailPayload, TicketDetailResponse, TicketLegalCasePayload, TicketListResponse, TicketMessagePayload, TicketPayload, TicketReplyRequest, TicketResponse, TicketStatusUpdateRequest, TicketValidationRunPayload
from src.services.ticket_service import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(require_roles("consultant", "admin"))])


@router.get("", response_model=TicketListResponse)
def list_tickets(db: Session = Depends(get_db)) -> TicketListResponse:
    items = [TicketPayload.model_validate(ticket) for ticket in ticket_service.list_tickets(db)]
    return TicketListResponse(success=True, message="Tickets fetched", data=items)


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> TicketDetailResponse:
    ticket, legal_case, case_facts, validation_runs, session_messages, consultant_messages = ticket_service.get_ticket_detail(db, ticket_id)
    payload = TicketDetailPayload(
        ticket=TicketPayload.model_validate(ticket),
        legal_case=TicketLegalCasePayload.model_validate(legal_case) if legal_case is not None else None,
        case_facts=[
            TicketCaseFactPayload.model_validate({
                "id": item.id,
                "case_id": item.case_id,
                "source_message_id": item.source_message_id,
                "fact_type": item.fact_type,
                "fact_key": item.fact_key,
                "fact_value": item.fact_value,
                "is_disputed": item.is_disputed,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
            for item in case_facts
        ],
        validation_runs=[
            TicketValidationRunPayload.model_validate({
                "id": item.id,
                "case_id": item.case_id,
                "planner_run_id": item.planner_run_id,
                "reasoning_run_id": item.reasoning_run_id,
                "validation_status": item.validation_status,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                "escalation_recommended": item.escalation_recommended,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
            for item in validation_runs
        ],
        session_messages=[SessionMessagePayload.model_validate(message) for message in session_messages],
        consultant_messages=[TicketMessagePayload.model_validate(message) for message in consultant_messages],
    )
    return TicketDetailResponse(success=True, message="Ticket detail fetched", data=payload)


@router.post("/{ticket_id}/reply", response_model=TicketResponse)
def reply_ticket(ticket_id: int, payload: TicketReplyRequest, db: Session = Depends(get_db)) -> TicketResponse:
    ticket_service.reply_ticket(db, ticket_id, payload.sender_name, payload.content)
    ticket = ticket_service.get_ticket(db, ticket_id)
    return TicketResponse(success=True, message="Ticket replied", data=TicketPayload.model_validate(ticket))


@router.post("/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(ticket_id: int, payload: TicketStatusUpdateRequest, db: Session = Depends(get_db)) -> TicketResponse:
    ticket = ticket_service.update_status(db, ticket_id, payload.status)
    return TicketResponse(success=True, message="Ticket status updated", data=TicketPayload.model_validate(ticket))
