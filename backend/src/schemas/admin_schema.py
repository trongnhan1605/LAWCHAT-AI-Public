from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from src.schemas.base import BaseResponse
from src.schemas.knowledge_schema import CategoryItem, DocumentItem


class AdminOverviewPayload(BaseModel):
    total_sessions: int
    total_messages: int
    total_legal_cases: int
    active_legal_cases: int
    high_risk_legal_cases: int
    total_case_facts: int
    total_documents: int
    ingested_documents: int
    total_chunks: int
    total_document_relations: int
    total_citations: int
    total_categories: int
    active_categories: int
    total_tickets: int
    open_tickets: int
    answered_tickets: int
    total_planner_runs: int
    total_reasoning_runs: int
    total_validation_runs: int
    validation_runs_needing_review: int
    escalations_recommended: int


class AdminActivityItem(BaseModel):
    event_type: str
    title: str
    description: str
    occurred_at: datetime


class AIUsageOverviewItem(BaseModel):
    total_requests: int
    metadata_requests: int
    embedding_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_input_tokens: int
    total_web_search_calls: int
    total_estimated_cost_usd: float


class AIUsageByDayItem(BaseModel):
    day: date
    request_count: int
    metadata_requests: int
    embedding_requests: int
    web_search_calls: int
    estimated_cost_usd: float


class AIUsageByDocumentItem(BaseModel):
    document_id: int | None = None
    title: str
    file_name: str | None = None
    models_used: list[str]
    request_count: int
    metadata_requests: int
    embedding_requests: int
    input_tokens: int
    output_tokens: int
    web_search_calls: int
    estimated_cost_usd: float


class AIUsageRequestItem(BaseModel):
    id: int
    created_at: datetime
    request_type: str
    endpoint: str
    provider: str
    model: str
    request_identifier: str | None = None
    document_id: int | None = None
    document_title: str | None = None
    file_name: str | None = None
    chunk_count: int | None = None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    total_tokens: int
    web_search_calls: int
    estimated_cost_usd: float
    status: str
    error_message: str | None = None


class PlannerRunItem(BaseModel):
    id: int
    case_id: int | None = None
    session_id: int | None = None
    user_id: int | None = None
    query_text: str
    detected_intent: str | None = None
    detected_domain: str | None = None
    complexity_level: str | None = None
    status: str
    plan_json: str | None = None
    context_json: str | None = None
    result_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LegalCaseItem(BaseModel):
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


class CaseFactItem(BaseModel):
    id: int
    case_id: int
    source_message_id: int | None = None
    fact_type: str
    fact_key: str
    fact_value: str
    happened_on: date | None = None
    is_disputed: bool
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ValidationRunItem(BaseModel):
    id: int
    case_id: int | None = None
    planner_run_id: int | None = None
    reasoning_run_id: int | None = None
    response_text: str | None = None
    validation_status: str
    confidence_score: float | None = None
    escalation_recommended: bool
    findings_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketCaseItem(BaseModel):
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


class LegalCaseDetailPayload(BaseModel):
    legal_case: LegalCaseItem
    case_facts: list[CaseFactItem]
    planner_runs: list[PlannerRunItem]
    validation_runs: list[ValidationRunItem]
    tickets: list[TicketCaseItem]


class ReasoningGraphNodeItem(BaseModel):
    id: str
    type: str | None = None
    label: str
    document_id: int | None = None
    chunk_id: int | None = None


class ReasoningGraphEdgeItem(BaseModel):
    from_: str = Field(alias="from")
    to: str
    type: str

    model_config = {"populate_by_name": True}


class LegalCaseReasoningGraphPayload(BaseModel):
    graph_type: str
    case_id: int
    case_title: str
    reasoning_run_id: int | None = None
    status: str
    domain: str | None = None
    intent: str | None = None
    nodes: list[ReasoningGraphNodeItem]
    edges: list[ReasoningGraphEdgeItem]
    conflict_resolution: dict | None = None


class MetadataAISettingsPayload(BaseModel):
    enabled: bool
    provider: str
    model: str
    web_search_enabled: bool
    available_providers: list[str]
    available_models: list[str]


class EmbeddingAISettingsPayload(BaseModel):
    enabled: bool
    model: str
    available_models: list[str]


class ChatbotAISettingsPayload(BaseModel):
    enabled: bool
    provider: str
    model: str
    public_model: str
    customer_model: str
    consultant_model: str
    available_providers: list[str]
    available_models: list[str]


class GraphBackendSettingsPayload(BaseModel):
    backend: str
    available_backends: list[str]
    neo4j_configured: bool
    neo4j_available: bool
    neo4j_database: str | None = None
    neo4j_sync_enabled: bool


class DefinitionItem(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    priority: int
    is_active: bool


class AdminUserItem(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class ContentArticleItem(BaseModel):
    id: int
    title: str
    slug: str
    category: str
    excerpt: str
    source_url: str | None = None
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentArticleRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    category: str = Field(min_length=2, max_length=120)
    excerpt: str = Field(min_length=10, max_length=600)
    source_url: str | None = Field(default=None, max_length=600)
    is_featured: bool = False
    is_active: bool = True


class LawyerProfileItem(BaseModel):
    id: int
    full_name: str
    slug: str
    title: str
    location: str
    specialties: str
    experience_years: int
    rating: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LawyerProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=180)
    location: str = Field(min_length=2, max_length=160)
    specialties: str = Field(min_length=2, max_length=500)
    experience_years: int = Field(default=0, ge=0, le=80)
    rating: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=700)
    avatar_url: str | None = Field(default=None, max_length=600)
    is_featured: bool = False
    is_active: bool = True


class CreateAdminUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(min_length=4, max_length=32)
    is_active: bool = True


class UpdateAdminUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: str = Field(min_length=4, max_length=32)
    is_active: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminOperationsPayload(BaseModel):
    overview: AdminOverviewPayload
    users: list[AdminUserItem]
    documents: list[DocumentItem]
    categories: list[CategoryItem]
    content_articles: list[ContentArticleItem] = []
    lawyer_profiles: list[LawyerProfileItem] = []
    document_types: list[DefinitionItem]
    authority_levels: list[DefinitionItem]
    activities: list[AdminActivityItem]
    metadata_ai_settings: MetadataAISettingsPayload
    embedding_ai_settings: EmbeddingAISettingsPayload
    chatbot_ai_settings: ChatbotAISettingsPayload
    graph_backend_settings: GraphBackendSettingsPayload
    graph_backend_insights: GraphBackendInsightsPayload | None = None
    ai_usage_overview: AIUsageOverviewItem
    ai_usage_by_day: list[AIUsageByDayItem]
    ai_usage_by_document: list[AIUsageByDocumentItem]
    recent_ai_requests: list[AIUsageRequestItem]
    recent_legal_cases: list[LegalCaseItem] = []
    recent_planner_runs: list[PlannerRunItem] = []
    recent_validation_runs: list[ValidationRunItem] = []


class GraphBackendStatusPayload(BaseModel):
    default_backend: str
    relational: dict[str, object]
    neo4j: dict[str, object]


class GraphProjectionSyncPayload(BaseModel):
    mode: str
    document_id: int | None = None
    document_count: int
    provision_count: int
    document_relation_count: int
    provision_relation_count: int


class GraphBackendBenchmarkItem(BaseModel):
    backend: str
    document_id: int
    depth: int
    runs: int
    avg_ms: float
    min_ms: float
    max_ms: float
    node_count: int
    edge_count: int


class GraphBackendBenchmarkPayload(BaseModel):
    document_ids: list[int]
    depths: list[int]
    runs_per_case: int
    results: list[GraphBackendBenchmarkItem]


class GraphBackendParityItem(BaseModel):
    document_id: int
    depth: int
    node_count_relational: int
    node_count_neo4j: int
    edge_count_relational: int
    edge_count_neo4j: int
    node_count_match: bool
    edge_count_match: bool
    edge_identity_match: bool
    anchor_match: bool


class GraphBackendParityPayload(BaseModel):
    document_ids: list[int]
    depths: list[int]
    results: list[GraphBackendParityItem]


class GraphBackendRecommendationPayload(BaseModel):
    recommended_backend: str
    summary: str
    reasons: list[str]


class GraphBackendInsightsPayload(BaseModel):
    benchmark: GraphBackendBenchmarkPayload | None = None
    parity: GraphBackendParityPayload | None = None
    recommendation: GraphBackendRecommendationPayload | None = None
    updated_at: datetime | None = None


class CorpusQualitySummaryPayload(BaseModel):
    total_documents: int
    pending_review_documents: int
    reviewed_documents: int
    high_risk_documents: int
    medium_risk_documents: int
    low_risk_documents: int
    total_chunks: int
    total_provisions: int
    total_document_relations: int
    total_provision_relations: int
    relations_missing_evidence: int
    issue_counts: dict[str, int]


class CorpusQualityDocumentItem(BaseModel):
    document_id: int
    title: str
    file_name: str
    source_reference: str | None = None
    storage_path: str
    document_code: str | None = None
    document_type: str | None = None
    legal_domain: str
    authority_level: str | None = None
    issuing_authority: str | None = None
    signed_date: str | None = None
    effective_date: str | None = None
    expiry_date: str | None = None
    legal_status: str | None = None
    metadata_review_status: str
    content_sha256: str | None = None
    source_identity: str | None = None
    ingestion_quality_status: str = "pending"
    ingestion_quality_notes: str | None = None
    retrieval_visibility: str = "indexed_unreviewed"
    ocr_quality_label: str | None = None
    ocr_quality_score: float | None = None
    chunk_count: int
    provision_count: int
    indexed_chunk_count: int
    document_relation_count: int
    provision_relation_count: int
    missing_relation_evidence_count: int
    risk_level: str
    issue_codes: list[str]
    recommendations: list[str]


class CorpusQualityReportPayload(BaseModel):
    summary: CorpusQualitySummaryPayload
    items: list[CorpusQualityDocumentItem]

class ReviewQueueSummaryItem(BaseModel):
    count: int
    high: int
    medium: int
    low: int

class ReviewQueueItem(BaseModel):
    queue: str
    source_type: str
    source_id: str
    title: str
    status: str
    severity: str
    detail: str
    action: str
    created_at: str | None = None
    document_id: int | None = None
    case_id: int | None = None
    source_path: str | None = None

class ReviewQueuesPayload(BaseModel):
    summary: dict[str, ReviewQueueSummaryItem]
    queues: dict[str, list[ReviewQueueItem]]


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class UpdateCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class ToggleCategoryRequest(BaseModel):
    is_active: bool


class UpdateMetadataAISettingsRequest(BaseModel):
    enabled: bool
    provider: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=2, max_length=64)
    web_search_enabled: bool


class UpdateEmbeddingAISettingsRequest(BaseModel):
    enabled: bool
    model: str = Field(min_length=2, max_length=64)


class UpdateChatbotAISettingsRequest(BaseModel):
    enabled: bool
    provider: str = Field(min_length=2, max_length=32)
    public_model: str = Field(min_length=2, max_length=64)
    customer_model: str = Field(min_length=2, max_length=64)
    consultant_model: str = Field(min_length=2, max_length=64)


class UpdateGraphBackendSettingsRequest(BaseModel):
    backend: str = Field(min_length=2, max_length=32)


class CreateDefinitionRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    priority: int = Field(ge=0, le=9999)


class UpdateDefinitionRequest(CreateDefinitionRequest):
    is_active: bool = True


class CreateDocumentRequest(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    file_name: str = Field(min_length=2, max_length=255)
    source_type: str = Field(min_length=2, max_length=16)
    legal_domain: str = Field(min_length=2, max_length=128)
    authority_level: str | None = Field(default=None, max_length=64)
    issuing_authority: str | None = Field(default=None, max_length=255)
    document_code: str | None = Field(default=None, max_length=128)
    document_type: str | None = Field(default=None, max_length=64)
    normative_level: int | None = None
    signed_date: date | None = None
    source_reference: str | None = Field(default=None, max_length=500)
    storage_path: str = Field(min_length=2, max_length=1000)
    summary: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    legal_status: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    duplicate_action: str | None = Field(default=None, max_length=32)


class UpdateDocumentRequest(CreateDocumentRequest):
    pass


class DocumentReviewRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class OcrCorrectionPreviewRequest(BaseModel):
    text: str = Field(default="", max_length=2000000)


class OcrCorrectionSuggestionItem(BaseModel):
    token_index: int
    original: str
    corrected: str
    confidence_score: float | None = None
    reason: str | None = None
    line_number: int | None = None
    context_excerpt: str | None = None


class OcrCorrectionPreviewPayload(BaseModel):
    normalized_text: str | None = None
    corrected_text: str
    changed: bool
    changed_token_count: int
    suggestions: list[OcrCorrectionSuggestionItem] = []
    review_required: bool = False


class UploadedDocumentFile(BaseModel):
    title: str
    file_name: str
    source_type: str
    source_reference: str
    storage_path: str
    extracted_text: str | None = None
    extracted_characters: int = 0
    ocr_applied: bool = False
    ocr_review_required: bool = False
    ocr_correction_changed_token_count: int = 0
    ocr_suggestions: list[OcrCorrectionSuggestionItem] = []
    legal_domain: str | None = None
    authority_level: str | None = None
    issuing_authority: str | None = None
    document_code: str | None = None
    document_type: str | None = None
    normative_level: int | None = None
    signed_date: date | None = None
    summary: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    legal_status: str | None = None


class AutoIngestedDocumentPayload(BaseModel):
    uploaded_file: UploadedDocumentFile
    document: DocumentItem
    extracted_characters: int
    chunk_count: int


class AdminOperationsResponse(BaseResponse[AdminOperationsPayload]):
    pass


class GraphBackendStatusResponse(BaseResponse[GraphBackendStatusPayload]):
    pass


class GraphProjectionSyncResponse(BaseResponse[GraphProjectionSyncPayload]):
    pass


class CorpusQualityReportResponse(BaseResponse[CorpusQualityReportPayload]):
    pass

class ReviewQueuesResponse(BaseResponse[ReviewQueuesPayload]):
    pass


class AdminOverviewResponse(BaseResponse[AdminOverviewPayload]):
    pass


class LegalCaseListResponse(BaseResponse[list[LegalCaseItem]]):
    pass


class LegalCaseDetailResponse(BaseResponse[LegalCaseDetailPayload]):
    pass


class LegalCaseReasoningGraphResponse(BaseResponse[LegalCaseReasoningGraphPayload]):
    pass


class AdminActivityResponse(BaseResponse[list[AdminActivityItem]]):
    pass


class AdminCategoryListResponse(BaseResponse[list[CategoryItem]]):
    pass


class AdminCategoryResponse(BaseResponse[CategoryItem]):
    pass


class AdminUserListResponse(BaseResponse[list[AdminUserItem]]):
    pass


class AdminUserResponse(BaseResponse[AdminUserItem]):
    pass


class ContentArticleListResponse(BaseResponse[list[ContentArticleItem]]):
    pass


class ContentArticleResponse(BaseResponse[ContentArticleItem]):
    pass


class LawyerProfileListResponse(BaseResponse[list[LawyerProfileItem]]):
    pass


class LawyerProfileResponse(BaseResponse[LawyerProfileItem]):
    pass


class UploadedDocumentFileResponse(BaseResponse[UploadedDocumentFile]):
    pass


class OcrCorrectionPreviewResponse(BaseResponse[OcrCorrectionPreviewPayload]):
    pass


class AutoIngestedDocumentResponse(BaseResponse[AutoIngestedDocumentPayload]):
    pass


class MetadataAISettingsResponse(BaseResponse[MetadataAISettingsPayload]):
    pass


class DefinitionListResponse(BaseResponse[list[DefinitionItem]]):
    pass


class DefinitionResponse(BaseResponse[DefinitionItem]):
    pass


class DocumentReviewResponse(BaseResponse[DocumentItem]):
    pass
