from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user, get_optional_current_user
from src.schemas.chat_schema import AskMessageRequest, AskMessageResponse, ChatMessagePayload, ChatSessionDetailPayload, ChatSessionPayload, CitationPayload, CreateSessionResponse, EscalateRequest, SessionDetailResponse
from src.schemas.ticket_schema import TicketPayload, TicketResponse
from src.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(db: Session = Depends(get_db)) -> CreateSessionResponse:
    session = chat_service.create_session(db, session_type="public")
    return CreateSessionResponse(success=True, message="Chat session created", data=_serialize_session(session))


@router.post("/customer/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_customer_session(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> CreateSessionResponse:
    session = chat_service.create_session(db, session_type="customer", user_id=current_user.id)
    return CreateSessionResponse(success=True, message="Customer chat session created", data=_serialize_session(session))


@router.get("/customer/sessions/latest", response_model=SessionDetailResponse)
def get_latest_customer_session(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> SessionDetailResponse:
    session = chat_service.get_or_create_latest_customer_session(db, current_user.id)
    messages = [_serialize_message(message) for message in chat_service.list_messages(db, session.id)]
    payload = ChatSessionDetailPayload(session=_serialize_session(session), messages=messages)
    return SessionDetailResponse(success=True, message="Customer chat session fetched", data=payload)


@router.get("/sessions/{session_token}", response_model=SessionDetailResponse)
def get_session(session_token: str, current_user=Depends(get_optional_current_user), db: Session = Depends(get_db)) -> SessionDetailResponse:
    session = chat_service.get_session(db, session_token, current_user)
    messages = [_serialize_message(message) for message in chat_service.list_messages(db, session.id)]
    payload = ChatSessionDetailPayload(session=_serialize_session(session), messages=messages)
    return SessionDetailResponse(success=True, message="Chat session fetched", data=payload)


@router.post("/sessions/{session_token}/messages", response_model=AskMessageResponse)
def ask_message(session_token: str, payload: AskMessageRequest, current_user=Depends(get_optional_current_user), db: Session = Depends(get_db)) -> AskMessageResponse:
    session, user_message, assistant_message = chat_service.ask(db, session_token, payload.content, current_user)
    data = {
        "session": _serialize_session(session),
        "user_message": _serialize_message(user_message),
        "assistant_message": _serialize_message(assistant_message),
    }
    return AskMessageResponse(success=True, message="Message processed", data=data)


@router.post("/sessions/{session_token}/escalate", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def escalate(session_token: str, payload: EscalateRequest, current_user=Depends(get_optional_current_user), db: Session = Depends(get_db)) -> TicketResponse:
    ticket = chat_service.escalate(db, session_token, payload.reason, current_user)
    return TicketResponse(success=True, message="Ticket created", data=TicketPayload.model_validate(ticket))


def _serialize_session(session) -> ChatSessionPayload:
    confidence = float(session.last_confidence_score) if session.last_confidence_score is not None else None
    return ChatSessionPayload(
        session_token=session.session_token,
        user_id=session.user_id,
        session_type=session.session_type,
        status=session.status,
        topic_guess=session.topic_guess,
        last_confidence_score=confidence,
        escalated_ticket_id=session.escalated_ticket_id,
    )


def _serialize_message(message) -> ChatMessagePayload:
    citation = None
    if message.citation_title:
        citation = CitationPayload(title=message.citation_title, source_reference=message.citation_source)
    confidence = float(message.confidence_score) if message.confidence_score is not None else None
    return ChatMessagePayload(
        id=message.id,
        role=message.role,
        message_type=message.message_type,
        content=message.content,
        category_slug=message.category_slug,
        confidence_score=confidence,
        warning_text=message.warning_text,
        citation=citation,
        needs_escalation=message.needs_escalation,
        created_at=message.created_at,
    )
