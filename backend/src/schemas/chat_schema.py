from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.base import BaseResponse


class ChatSessionPayload(BaseModel):
    session_token: str
    user_id: int | None = None
    session_type: str
    status: str
    topic_guess: str | None = None
    last_confidence_score: float | None = None
    escalated_ticket_id: int | None = None


class CitationPayload(BaseModel):
    title: str
    source_reference: str | None = None


class ChatMessagePayload(BaseModel):
    id: int
    role: str
    message_type: str
    content: str
    category_slug: str | None = None
    confidence_score: float | None = None
    warning_text: str | None = None
    citation: CitationPayload | None = None
    needs_escalation: bool
    created_at: datetime


class ChatSessionDetailPayload(BaseModel):
    session: ChatSessionPayload
    messages: list[ChatMessagePayload]


class CreateSessionResponse(BaseResponse[ChatSessionPayload]):
    pass


class SessionDetailResponse(BaseResponse[ChatSessionDetailPayload]):
    pass


class AskMessageRequest(BaseModel):
    content: str = Field(min_length=5, max_length=3000)


class AskMessagePayload(BaseModel):
    session: ChatSessionPayload
    user_message: ChatMessagePayload
    assistant_message: ChatMessagePayload


class AskMessageResponse(BaseResponse[AskMessagePayload]):
    pass


class EscalateRequest(BaseModel):
    reason: str = Field(default="User requested consultant support", min_length=5, max_length=500)
