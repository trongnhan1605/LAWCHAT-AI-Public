from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.base import BaseResponse


class TicketPayload(BaseModel):
    id: int
    session_id: int
    case_id: int | None = None
    title: str
    topic: str | None = None
    escalation_reason: str
    confidence_score: float | None = None
    status: str
    priority: str
    consultant_note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseResponse[TicketPayload]):
    pass


class TicketMessagePayload(BaseModel):
    id: int
    ticket_id: int
    sender_type: str
    sender_name: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionMessagePayload(BaseModel):
    id: int
    role: str
    content: str
    category_slug: str | None = None
    warning_text: str | None = None
    citation_title: str | None = None
    citation_source: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketLegalCasePayload(BaseModel):
    id: int
    session_id: int | None = None
    user_id: int | None = None
    title: str
    legal_domain: str
    status: str
    risk_level: str
    summary: str | None = None
    desired_outcome: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketCaseFactPayload(BaseModel):
    id: int
    case_id: int
    source_message_id: int | None = None
    fact_type: str
    fact_key: str
    fact_value: str
    is_disputed: bool
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime


class TicketValidationRunPayload(BaseModel):
    id: int
    case_id: int | None = None
    planner_run_id: int | None = None
    reasoning_run_id: int | None = None
    validation_status: str
    confidence_score: float | None = None
    escalation_recommended: bool
    created_at: datetime
    updated_at: datetime


class TicketDetailPayload(BaseModel):
    ticket: TicketPayload
    legal_case: TicketLegalCasePayload | None = None
    case_facts: list[TicketCaseFactPayload] = []
    validation_runs: list[TicketValidationRunPayload] = []
    session_messages: list[SessionMessagePayload]
    consultant_messages: list[TicketMessagePayload]


class TicketListResponse(BaseResponse[list[TicketPayload]]):
    pass


class TicketDetailResponse(BaseResponse[TicketDetailPayload]):
    pass


class TicketReplyRequest(BaseModel):
    sender_name: str = Field(default="Consultant", min_length=2, max_length=120)
    content: str = Field(min_length=5, max_length=4000)


class TicketStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=2, max_length=32)
