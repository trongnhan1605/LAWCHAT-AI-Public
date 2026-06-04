from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.core.security import get_current_user, require_roles
from src.ingestion.document_metadata_inference import document_metadata_inference_service
from src.ingestion.upload_text_preview import upload_text_preview_service
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.schemas.base import BaseResponse
from src.schemas.admin_schema import AdminActivityItem, AdminActivityResponse, AdminCategoryListResponse, AdminCategoryResponse, AdminOperationsPayload, AdminOperationsResponse, AdminOverviewPayload, AdminOverviewResponse, AdminUserItem, AdminUserListResponse, AdminUserResponse, AutoIngestedDocumentPayload, AutoIngestedDocumentResponse, CaseFactItem, ChatbotAISettingsPayload, ContentArticleItem, ContentArticleListResponse, ContentArticleRequest, ContentArticleResponse, CorpusQualityReportPayload, CorpusQualityReportResponse, CreateAdminUserRequest, CreateCategoryRequest, CreateDefinitionRequest, CreateDocumentRequest, DefinitionItem, DefinitionListResponse, DefinitionResponse, DocumentReviewRequest, DocumentReviewResponse, EmbeddingAISettingsPayload, GraphBackendBenchmarkPayload, GraphBackendInsightsPayload, GraphBackendParityPayload, GraphBackendRecommendationPayload, GraphBackendSettingsPayload, GraphBackendStatusResponse, GraphProjectionSyncResponse, LawyerProfileItem, LawyerProfileListResponse, LawyerProfileRequest, LawyerProfileResponse, LegalCaseDetailPayload, LegalCaseDetailResponse, LegalCaseItem, LegalCaseListResponse, LegalCaseReasoningGraphPayload, LegalCaseReasoningGraphResponse, MetadataAISettingsPayload, MetadataAISettingsResponse, OcrCorrectionPreviewPayload, OcrCorrectionPreviewRequest, OcrCorrectionPreviewResponse, PlannerRunItem, ReviewQueuesPayload, ReviewQueuesResponse, TicketCaseItem, ToggleCategoryRequest, UpdateAdminUserRequest, UpdateCategoryRequest, UpdateChatbotAISettingsRequest, UpdateDefinitionRequest, UpdateDocumentRequest, UpdateEmbeddingAISettingsRequest, UpdateGraphBackendSettingsRequest, UpdateMetadataAISettingsRequest, UploadedDocumentFile, UploadedDocumentFileResponse, ValidationRunItem
from src.schemas.knowledge_schema import CategoryItem, DocumentItem
from src.services.admin_service import admin_service
from src.services.admin_graph_operations_service import admin_graph_operations_service
from src.services.admin_review_workflow_service import admin_review_workflow_service
from src.services.admin_settings_service import admin_settings_service
from src.services.admin_upload_service import admin_upload_service
from src.services.ai_usage_service import ai_usage_service
from src.services.corpus_quality_report_service import corpus_quality_report_service
from src.services.graph_service import graph_service
from src.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


@router.get("/overview", response_model=AdminOverviewResponse)
def overview(db: Session = Depends(get_db)) -> AdminOverviewResponse:
    payload = AdminOverviewPayload.model_validate(admin_service.build_overview(db))
    return AdminOverviewResponse(success=True, message="Admin overview fetched", data=payload)


@router.get("/activity", response_model=AdminActivityResponse)
def activity(db: Session = Depends(get_db)) -> AdminActivityResponse:
    items = [AdminActivityItem.model_validate(item) for item in admin_service.recent_activity(db)]
    return AdminActivityResponse(success=True, message="Admin activity fetched", data=items)


@router.get("/review-queues", response_model=ReviewQueuesResponse)
def review_queues(limit_per_queue: int = 20, db: Session = Depends(get_db)) -> ReviewQueuesResponse:
    payload = ReviewQueuesPayload.model_validate(admin_review_workflow_service.build_queues(db, limit_per_queue=limit_per_queue))
    return ReviewQueuesResponse(success=True, message="Admin review queues fetched", data=payload)


@router.get("/legal-cases", response_model=LegalCaseListResponse)
def list_legal_cases(db: Session = Depends(get_db)) -> LegalCaseListResponse:
    items = [LegalCaseItem.model_validate(item) for item in admin_service.list_legal_cases(db)]
    return LegalCaseListResponse(success=True, message="Legal cases fetched", data=items)


@router.get("/legal-cases/{case_id}", response_model=LegalCaseDetailResponse)
def get_legal_case(case_id: int, db: Session = Depends(get_db)) -> LegalCaseDetailResponse:
    legal_case, case_facts, planner_runs, validation_runs, tickets = admin_service.get_legal_case_detail(db, case_id)
    payload = LegalCaseDetailPayload(
        legal_case=LegalCaseItem.model_validate(legal_case),
        case_facts=[
            CaseFactItem.model_validate({
                "id": item.id,
                "case_id": item.case_id,
                "source_message_id": item.source_message_id,
                "fact_type": item.fact_type,
                "fact_key": item.fact_key,
                "fact_value": item.fact_value,
                "happened_on": item.happened_on,
                "is_disputed": item.is_disputed,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
            for item in case_facts
        ],
        planner_runs=[PlannerRunItem.model_validate(item) for item in planner_runs],
        validation_runs=[
            ValidationRunItem.model_validate({
                "id": item.id,
                "case_id": item.case_id,
                "planner_run_id": item.planner_run_id,
                "reasoning_run_id": item.reasoning_run_id,
                "response_text": item.response_text,
                "validation_status": item.validation_status,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                "escalation_recommended": item.escalation_recommended,
                "findings_json": item.findings_json,
                "error_message": item.error_message,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
            for item in validation_runs
        ],
        tickets=[
            TicketCaseItem.model_validate({
                "id": item.id,
                "session_id": item.session_id,
                "case_id": item.case_id,
                "title": item.title,
                "topic": item.topic,
                "escalation_reason": item.escalation_reason,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                "status": item.status,
                "priority": item.priority,
                "consultant_note": item.consultant_note,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
            for item in tickets
        ],
    )
    return LegalCaseDetailResponse(success=True, message="Legal case detail fetched", data=payload)


@router.get("/legal-cases/{case_id}/reasoning-graph", response_model=LegalCaseReasoningGraphResponse)
def get_legal_case_reasoning_graph(case_id: int, db: Session = Depends(get_db)) -> LegalCaseReasoningGraphResponse:
    payload = LegalCaseReasoningGraphPayload.model_validate(graph_service.get_case_reasoning_graph(db, case_id))
    return LegalCaseReasoningGraphResponse(success=True, message="Legal case reasoning graph fetched", data=payload)


@router.get("/users", response_model=AdminUserListResponse)
def list_users(db: Session = Depends(get_db)) -> AdminUserListResponse:
    items = [_serialize_user(item) for item in admin_service.list_users(db)]
    return AdminUserListResponse(success=True, message="Admin users fetched", data=items)


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateAdminUserRequest, db: Session = Depends(get_db)) -> AdminUserResponse:
    user = admin_service.create_user(db, payload.full_name, payload.email, payload.password, payload.role, payload.is_active)
    return AdminUserResponse(success=True, message="User created", data=_serialize_user(user))


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: UpdateAdminUserRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AdminUserResponse:
    user = admin_service.update_user(
        db,
        user_id,
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
        password=payload.password,
        actor_user_id=current_user.id,
    )
    return AdminUserResponse(success=True, message="User updated", data=_serialize_user(user))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> Response:
    admin_service.delete_user(db, user_id, actor_user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/categories", response_model=AdminCategoryListResponse)
def list_categories(db: Session = Depends(get_db)) -> AdminCategoryListResponse:
    items = [CategoryItem.model_validate(item) for item in admin_service.list_categories(db)]
    return AdminCategoryListResponse(success=True, message="Admin categories fetched", data=items)


@router.post("/categories", response_model=AdminCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: CreateCategoryRequest, db: Session = Depends(get_db)) -> AdminCategoryResponse:
    category = admin_service.create_category(db, payload.name, payload.slug, payload.description)
    return AdminCategoryResponse(success=True, message="Category created", data=CategoryItem.model_validate(category))


@router.post("/categories/{category_id}/toggle", response_model=AdminCategoryResponse)
def toggle_category(category_id: int, payload: ToggleCategoryRequest, db: Session = Depends(get_db)) -> AdminCategoryResponse:
    category = admin_service.toggle_category(db, category_id, payload.is_active)
    return AdminCategoryResponse(success=True, message="Category updated", data=CategoryItem.model_validate(category))


@router.put("/categories/{category_id}", response_model=AdminCategoryResponse)
def update_category(category_id: int, payload: UpdateCategoryRequest, db: Session = Depends(get_db)) -> AdminCategoryResponse:
    category = admin_service.update_category(db, category_id, payload.name, payload.slug, payload.description, payload.is_active)
    return AdminCategoryResponse(success=True, message="Category updated", data=CategoryItem.model_validate(category))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/content-articles", response_model=ContentArticleListResponse)
def list_content_articles(db: Session = Depends(get_db)) -> ContentArticleListResponse:
    items = [ContentArticleItem.model_validate(item) for item in admin_service.list_content_articles(db)]
    return ContentArticleListResponse(success=True, message="Content articles fetched", data=items)


@router.post("/content-articles", response_model=ContentArticleResponse, status_code=status.HTTP_201_CREATED)
def create_content_article(payload: ContentArticleRequest, db: Session = Depends(get_db)) -> ContentArticleResponse:
    item = admin_service.create_content_article(db, payload.title, payload.slug, payload.category, payload.excerpt, payload.source_url, payload.is_featured, payload.is_active)
    return ContentArticleResponse(success=True, message="Content article created", data=ContentArticleItem.model_validate(item))


@router.put("/content-articles/{article_id}", response_model=ContentArticleResponse)
def update_content_article(article_id: int, payload: ContentArticleRequest, db: Session = Depends(get_db)) -> ContentArticleResponse:
    item = admin_service.update_content_article(db, article_id, payload.title, payload.slug, payload.category, payload.excerpt, payload.source_url, payload.is_featured, payload.is_active)
    return ContentArticleResponse(success=True, message="Content article updated", data=ContentArticleItem.model_validate(item))


@router.delete("/content-articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_article(article_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_content_article(db, article_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/lawyer-profiles", response_model=LawyerProfileListResponse)
def list_lawyer_profiles(db: Session = Depends(get_db)) -> LawyerProfileListResponse:
    items = [LawyerProfileItem.model_validate(item) for item in admin_service.list_lawyer_profiles(db)]
    return LawyerProfileListResponse(success=True, message="Lawyer profiles fetched", data=items)


@router.post("/lawyer-profiles", response_model=LawyerProfileResponse, status_code=status.HTTP_201_CREATED)
def create_lawyer_profile(payload: LawyerProfileRequest, db: Session = Depends(get_db)) -> LawyerProfileResponse:
    item = admin_service.create_lawyer_profile(db, payload.full_name, payload.slug, payload.title, payload.location, payload.specialties, payload.experience_years, payload.rating, payload.bio, payload.avatar_url, payload.is_featured, payload.is_active)
    return LawyerProfileResponse(success=True, message="Lawyer profile created", data=LawyerProfileItem.model_validate(item))


@router.put("/lawyer-profiles/{lawyer_id}", response_model=LawyerProfileResponse)
def update_lawyer_profile(lawyer_id: int, payload: LawyerProfileRequest, db: Session = Depends(get_db)) -> LawyerProfileResponse:
    item = admin_service.update_lawyer_profile(db, lawyer_id, payload.full_name, payload.slug, payload.title, payload.location, payload.specialties, payload.experience_years, payload.rating, payload.bio, payload.avatar_url, payload.is_featured, payload.is_active)
    return LawyerProfileResponse(success=True, message="Lawyer profile updated", data=LawyerProfileItem.model_validate(item))


@router.delete("/lawyer-profiles/{lawyer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lawyer_profile(lawyer_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_lawyer_profile(db, lawyer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/document-types", response_model=DefinitionListResponse)
def list_document_types(db: Session = Depends(get_db)) -> DefinitionListResponse:
    items = [_serialize_document_type(item) for item in admin_service.list_document_types(db)]
    return DefinitionListResponse(success=True, message="Document types fetched", data=items)


@router.post("/document-types", response_model=DefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_document_type(payload: CreateDefinitionRequest, db: Session = Depends(get_db)) -> DefinitionResponse:
    item = admin_service.create_document_type(db, payload.name, payload.slug, payload.description, payload.priority)
    return DefinitionResponse(success=True, message="Document type created", data=_serialize_document_type(item))


@router.put("/document-types/{item_id}", response_model=DefinitionResponse)
def update_document_type(item_id: int, payload: UpdateDefinitionRequest, db: Session = Depends(get_db)) -> DefinitionResponse:
    item = admin_service.update_document_type(db, item_id, payload.name, payload.slug, payload.description, payload.priority, payload.is_active)
    return DefinitionResponse(success=True, message="Document type updated", data=_serialize_document_type(item))


@router.delete("/document-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_type(item_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_document_type(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/authority-levels", response_model=DefinitionListResponse)
def list_authority_levels(db: Session = Depends(get_db)) -> DefinitionListResponse:
    items = [_serialize_authority_level(item) for item in admin_service.list_authority_levels(db)]
    return DefinitionListResponse(success=True, message="Authority levels fetched", data=items)


@router.post("/authority-levels", response_model=DefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_authority_level(payload: CreateDefinitionRequest, db: Session = Depends(get_db)) -> DefinitionResponse:
    item = admin_service.create_authority_level(db, payload.name, payload.slug, payload.description, payload.priority)
    return DefinitionResponse(success=True, message="Authority level created", data=_serialize_authority_level(item))


@router.put("/authority-levels/{item_id}", response_model=DefinitionResponse)
def update_authority_level(item_id: int, payload: UpdateDefinitionRequest, db: Session = Depends(get_db)) -> DefinitionResponse:
    item = admin_service.update_authority_level(db, item_id, payload.name, payload.slug, payload.description, payload.priority, payload.is_active)
    return DefinitionResponse(success=True, message="Authority level updated", data=_serialize_authority_level(item))


@router.delete("/authority-levels/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_authority_level(item_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_authority_level(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/metadata-ai-settings", response_model=MetadataAISettingsResponse)
def get_metadata_ai_settings() -> MetadataAISettingsResponse:
    return MetadataAISettingsResponse(success=True, message="Metadata AI settings fetched", data=admin_settings_service.build_metadata_ai_settings())


@router.put("/metadata-ai-settings", response_model=MetadataAISettingsResponse)
def update_metadata_ai_settings(payload: UpdateMetadataAISettingsRequest) -> MetadataAISettingsResponse:
    return MetadataAISettingsResponse(success=True, message="Metadata AI settings updated", data=admin_settings_service.update_metadata_ai_settings(payload))


@router.put("/embedding-ai-settings", response_model=BaseResponse[EmbeddingAISettingsPayload])
def update_embedding_ai_settings(payload: UpdateEmbeddingAISettingsRequest):
    return {"success": True, "message": "Embedding AI settings updated", "data": admin_settings_service.update_embedding_ai_settings(payload)}


@router.put("/chatbot-ai-settings", response_model=BaseResponse[ChatbotAISettingsPayload])
def update_chatbot_ai_settings(payload: UpdateChatbotAISettingsRequest):
    return {"success": True, "message": "Chatbot AI settings updated", "data": admin_settings_service.update_chatbot_ai_settings(payload)}


@router.put("/graph-backend-settings", response_model=BaseResponse[GraphBackendSettingsPayload])
def update_graph_backend_settings(payload: UpdateGraphBackendSettingsRequest):
    return {"success": True, "message": "Graph backend settings updated", "data": admin_settings_service.update_graph_backend_settings(payload)}


@router.post("/documents", response_model=BaseResponse[DocumentItem], status_code=status.HTTP_201_CREATED)
def create_document(payload: CreateDocumentRequest, db: Session = Depends(get_db)):
    document = admin_service.create_document(
        db,
        payload.title,
        payload.file_name,
        payload.source_type,
        payload.legal_domain,
        payload.authority_level,
        payload.issuing_authority,
        payload.document_code,
        payload.document_type,
        payload.normative_level,
        payload.signed_date,
        payload.source_reference,
        payload.storage_path,
        payload.summary,
        payload.effective_date,
        payload.expiry_date,
        payload.legal_status,
        payload.is_active,
        payload.duplicate_action,
    )
    return {"success": True, "message": "Document created", "data": _serialize_document(db, document)}


@router.post("/documents/upload", response_model=UploadedDocumentFileResponse, status_code=status.HTTP_201_CREATED)
def upload_document_file(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadedDocumentFileResponse:
    payload = admin_upload_service.store_uploaded_document_file(file, db)
    return UploadedDocumentFileResponse(success=True, message="Document file uploaded", data=payload)


@router.post("/documents/ocr-correction-preview", response_model=OcrCorrectionPreviewResponse)
def preview_ocr_correction(payload: OcrCorrectionPreviewRequest) -> OcrCorrectionPreviewResponse:
    result = OcrCorrectionPreviewPayload.model_validate(knowledge_service.preview_legal_ocr_correction(payload.text))
    return OcrCorrectionPreviewResponse(success=True, message="OCR correction preview generated", data=result)


@router.post("/documents/upload-and-ingest", response_model=AutoIngestedDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_and_ingest_document_file(
    file: UploadFile = File(...),
    duplicate_action: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> AutoIngestedDocumentResponse:
    result = admin_upload_service.upload_and_ingest_document_file(file, duplicate_action, db)
    payload = AutoIngestedDocumentPayload(
        uploaded_file=result.uploaded_file,
        document=_serialize_document(db, result.document),
        extracted_characters=result.extracted_characters,
        chunk_count=result.chunk_count,
    )
    return AutoIngestedDocumentResponse(success=True, message="Document uploaded and ingested", data=payload)


@router.get("/documents/{document_id}/download")
def download_document_source(document_id: int, db: Session = Depends(get_db)) -> FileResponse:
    document = admin_service.get_document(db, document_id)
    source_path = Path(document.storage_path)
    if not source_path.exists() or not source_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")
    return FileResponse(path=source_path, filename=document.file_name, media_type="application/octet-stream")


def _store_uploaded_document_file(file: UploadFile, db: Session) -> UploadedDocumentFile:
    return admin_upload_service.store_uploaded_document_file(file, db)


def _extract_document_metadata(file_path: Path, source_type: str, db: Session, preview_text: str | None = None) -> dict[str, object | None]:
    return document_metadata_inference_service.extract_document_metadata(file_path, source_type, db, preview_text)


def _extract_preview_text(file_path: Path, source_type: str) -> str:
    return upload_text_preview_service.extract_preview_text(file_path, source_type)


def _extract_full_text(file_path: Path, source_type: str) -> tuple[str, bool, dict[str, object] | None]:
    return upload_text_preview_service.extract_full_text(file_path, source_type, knowledge_service=knowledge_service)


def _guess_title(preview_text: str) -> str | None:
    return document_metadata_inference_service.guess_title(preview_text)


def _guess_document_code(preview_text: str) -> str | None:
    return document_metadata_inference_service.guess_document_code(preview_text)


def _guess_document_type(preview_text: str) -> str | None:
    return document_metadata_inference_service.guess_document_type(preview_text)


def _infer_normative_level(db: Session, document_type: str | None) -> int | None:
    return document_metadata_inference_service.infer_normative_level(db, document_type)


def _default_legal_domain(db: Session) -> str:
    return document_metadata_inference_service.default_legal_domain(db)


def _normalize_search_text(value: str) -> str:
    return document_metadata_inference_service.normalize_search_text(value)


def _guess_legal_domain(preview_text: str, db: Session) -> str:
    return document_metadata_inference_service.guess_legal_domain(preview_text, db)


def _guess_issuing_authority(preview_text: str) -> str | None:
    return document_metadata_inference_service.guess_issuing_authority(preview_text)


def _guess_authority_level(db: Session, issuing_authority: str | None) -> str | None:
    return document_metadata_inference_service.guess_authority_level(db, issuing_authority)


def _guess_signed_date(preview_text: str):
    return document_metadata_inference_service.guess_signed_date(preview_text)


def _guess_effective_date(preview_text: str):
    return document_metadata_inference_service.guess_effective_date(preview_text)


def _guess_expiry_date(preview_text: str):
    return document_metadata_inference_service.guess_expiry_date(preview_text)


def _guess_legal_status(preview_text: str, effective_date_value, expiry_date_value) -> str:
    return document_metadata_inference_service.guess_legal_status(preview_text, effective_date_value, expiry_date_value)


def _guess_summary(preview_text: str, title: str | None) -> str | None:
    return document_metadata_inference_service.guess_summary(preview_text, title)


def _parse_ai_date(value: str | None):
    return document_metadata_inference_service.parse_ai_date(value)


def _normalize_ai_legal_status(value: str | None) -> str | None:
    return document_metadata_inference_service.normalize_ai_legal_status(value)


@router.put("/documents/{document_id}", response_model=BaseResponse[DocumentItem])
def update_document(document_id: int, payload: UpdateDocumentRequest, db: Session = Depends(get_db)):
    document = admin_service.update_document(
        db,
        document_id,
        payload.title,
        payload.file_name,
        payload.source_type,
        payload.legal_domain,
        payload.authority_level,
        payload.issuing_authority,
        payload.document_code,
        payload.document_type,
        payload.normative_level,
        payload.signed_date,
        payload.source_reference,
        payload.storage_path,
        payload.summary,
        payload.effective_date,
        payload.expiry_date,
        payload.legal_status,
        payload.is_active,
    )
    return {"success": True, "message": "Document updated", "data": _serialize_document(db, document)}


@router.post("/documents/{document_id}/review", response_model=DocumentReviewResponse)
def review_document(document_id: int, payload: DocumentReviewRequest, db: Session = Depends(get_db)) -> DocumentReviewResponse:
    document = admin_service.mark_document_metadata_reviewed(db, document_id, payload.notes)
    return DocumentReviewResponse(success=True, message="Document metadata reviewed", data=_serialize_document(db, document))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_document(db, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/graph-backend/status", response_model=GraphBackendStatusResponse)
def graph_backend_status() -> GraphBackendStatusResponse:
    payload = admin_graph_operations_service.backend_status()
    return GraphBackendStatusResponse(success=True, message="Graph backend status fetched", data=payload)


@router.post("/graph-backend/sync", response_model=GraphProjectionSyncResponse)
def sync_graph_projection(document_id: int | None = None, db: Session = Depends(get_db)) -> GraphProjectionSyncResponse:
    payload = admin_graph_operations_service.sync_projection(db, document_id)
    return GraphProjectionSyncResponse(success=True, message="Neo4j graph projection synced", data=payload)


@router.get("/graph-backend/benchmark", response_model=BaseResponse[GraphBackendBenchmarkPayload])
def benchmark_graph_backends(
    document_ids: str = "10,24,51",
    depths: str = "1,2",
    runs: int = 2,
    db: Session = Depends(get_db),
):
    benchmark_payload = admin_graph_operations_service.benchmark_backends(db, document_ids=document_ids, depths=depths, runs=runs)
    return {"success": True, "message": "Graph backend benchmark fetched", "data": benchmark_payload}


@router.get("/graph-backend/parity", response_model=BaseResponse[GraphBackendParityPayload])
def parity_graph_backends(
    document_ids: str = "10,24,51",
    depths: str = "1,2",
    db: Session = Depends(get_db),
):
    parity_payload = admin_graph_operations_service.parity_backends(db, document_ids=document_ids, depths=depths)
    return {"success": True, "message": "Graph backend parity fetched", "data": parity_payload}


@router.get("/corpus/quality-report", response_model=CorpusQualityReportResponse)
def corpus_quality_report(include_reviewed: bool = True, db: Session = Depends(get_db)) -> CorpusQualityReportResponse:
    payload = CorpusQualityReportPayload.model_validate(corpus_quality_report_service.build_report(db, include_reviewed=include_reviewed))
    return CorpusQualityReportResponse(success=True, message="Corpus quality report fetched", data=payload)


def _load_graph_backend_insights() -> GraphBackendInsightsPayload | None:
    return admin_graph_operations_service.load_insights()


def _build_graph_backend_recommendation(
    benchmark: GraphBackendBenchmarkPayload | None,
    parity: GraphBackendParityPayload | None,
) -> GraphBackendRecommendationPayload | None:
    if benchmark is None or parity is None or not benchmark.results or not parity.results:
        return None
    return admin_graph_operations_service.build_recommendation(benchmark, parity)


def _persist_graph_backend_insights(
    benchmark: GraphBackendBenchmarkPayload | None = None,
    parity: GraphBackendParityPayload | None = None,
) -> GraphBackendInsightsPayload:
    admin_graph_operations_service.persist_insights(benchmark=benchmark, parity=parity)
    persisted = admin_graph_operations_service.load_insights()
    if persisted is None:
        raise RuntimeError("Graph backend insights were not persisted")
    return persisted


@router.get("/operations", response_model=AdminOperationsResponse)
def operations(include_heavy: bool = False, db: Session = Depends(get_db)) -> AdminOperationsResponse:
    documents = admin_service.list_documents(db)
    document_metrics = _build_document_metrics(db, [item.id for item in documents])
    payload = AdminOperationsPayload(
        overview=AdminOverviewPayload.model_validate(admin_service.build_overview(db)),
        users=[_serialize_user(item) for item in admin_service.list_users(db)],
        documents=[_serialize_document(item, document_metrics.get(item.id)) for item in documents],
        categories=[CategoryItem.model_validate(item) for item in admin_service.list_categories(db)],
        content_articles=[ContentArticleItem.model_validate(item) for item in admin_service.list_content_articles(db)],
        lawyer_profiles=[LawyerProfileItem.model_validate(item) for item in admin_service.list_lawyer_profiles(db)],
        document_types=[_serialize_document_type(item) for item in admin_service.list_document_types(db)],
        authority_levels=[_serialize_authority_level(item) for item in admin_service.list_authority_levels(db)],
        activities=[AdminActivityItem.model_validate(item) for item in admin_service.recent_activity(db)] if include_heavy else [],
        metadata_ai_settings=_build_metadata_ai_settings(),
        embedding_ai_settings=_build_embedding_ai_settings(),
        chatbot_ai_settings=_build_chatbot_ai_settings(),
        graph_backend_settings=_build_graph_backend_settings(),
        graph_backend_insights=_load_graph_backend_insights(),
        ai_usage_overview=ai_usage_service.build_usage_overview(db),
        ai_usage_by_day=ai_usage_service.build_usage_by_day(db) if include_heavy else [],
        ai_usage_by_document=ai_usage_service.build_usage_by_document(db) if include_heavy else [],
        recent_ai_requests=ai_usage_service.list_recent_requests(db) if include_heavy else [],
        recent_legal_cases=[LegalCaseItem.model_validate(item) for item in admin_service.list_recent_legal_cases(db)] if include_heavy else [],
        recent_planner_runs=[PlannerRunItem.model_validate(item) for item in admin_service.list_recent_planner_runs(db)] if include_heavy else [],
        recent_validation_runs=[ValidationRunItem.model_validate({
            "id": item.id,
            "case_id": item.case_id,
            "planner_run_id": item.planner_run_id,
            "reasoning_run_id": item.reasoning_run_id,
            "response_text": item.response_text,
            "validation_status": item.validation_status,
            "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
            "escalation_recommended": item.escalation_recommended,
            "findings_json": item.findings_json,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }) for item in admin_service.list_recent_validation_runs(db)] if include_heavy else [],
    )
    return AdminOperationsResponse(success=True, message="Admin operations payload fetched", data=payload)


def _build_document_metrics(db: Session, document_ids: list[int]) -> dict[int, dict[str, int | str]]:
    if not document_ids:
        return {}

    chunk_counts = {
        int(document_id): int(count or 0)
        for document_id, count in (
            db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
            .filter(DocumentChunk.document_id.in_(document_ids))
            .group_by(DocumentChunk.document_id)
            .all()
        )
    }
    relation_counts = {
        int(document_id): int(count or 0)
        for document_id, count in (
            db.query(DocumentRelation.source_document_id, func.count(DocumentRelation.id))
            .filter(DocumentRelation.source_document_id.in_(document_ids))
            .group_by(DocumentRelation.source_document_id)
            .all()
        )
    }
    vector_rows = (
        db.query(
            DocumentChunk.document_id,
            func.sum(case((DocumentChunkVector.embedding_status == "indexed", 1), else_=0)).label("indexed_count"),
            func.sum(case((DocumentChunkVector.embedding_status == "failed", 1), else_=0)).label("failed_count"),
        )
        .join(DocumentChunkVector, DocumentChunkVector.chunk_id == DocumentChunk.id)
        .filter(DocumentChunk.document_id.in_(document_ids))
        .group_by(DocumentChunk.document_id)
        .all()
    )
    vector_counts = {
        int(document_id): {
            "indexed_count": int(indexed_count or 0),
            "failed_count": int(failed_count or 0),
        }
        for document_id, indexed_count, failed_count in vector_rows
    }

    metrics: dict[int, dict[str, int | str]] = {}
    embedding_enabled = settings.ai_embedding_enabled and (settings.embedding_provider == "local" or bool(settings.openai_api_key))
    for document_id in document_ids:
        chunk_count = chunk_counts.get(document_id, 0)
        indexed_count = int(vector_counts.get(document_id, {}).get("indexed_count", 0))
        failed_count = int(vector_counts.get(document_id, {}).get("failed_count", 0))
        if chunk_count == 0:
            embedding_status = "not_indexed"
        elif indexed_count == chunk_count:
            embedding_status = "indexed"
        elif failed_count > 0 and indexed_count > 0:
            embedding_status = "partial"
        elif failed_count > 0:
            embedding_status = "failed"
        elif embedding_enabled:
            embedding_status = "pending"
        else:
            embedding_status = "disabled"

        metrics[document_id] = {
            "chunk_count": chunk_count,
            "embedded_chunk_count": indexed_count,
            "relation_count": relation_counts.get(document_id, 0),
            "embedding_status": embedding_status,
        }
    return metrics


def _serialize_document(item, metrics: dict[str, int | str] | None = None) -> DocumentItem:
    resolved_metrics = metrics or {}
    return DocumentItem.model_validate({
        "id": item.id,
        "title": item.title,
        "file_name": item.file_name,
        "source_type": item.source_type,
        "legal_domain": item.legal_domain,
        "authority_level": item.authority_level,
        "issuing_authority": item.issuing_authority,
        "document_code": item.document_code,
        "document_type": item.document_type,
        "normative_level": item.normative_level,
        "signed_date": item.signed_date,
        "source_reference": item.source_reference,
        "storage_path": item.storage_path,
        "summary": item.summary,
        "effective_date": item.effective_date,
        "expiry_date": item.expiry_date,
        "legal_status": item.legal_status,
        "metadata_review_status": item.metadata_review_status,
        "metadata_review_notes": item.metadata_review_notes,
        "metadata_last_reviewed_at": item.metadata_last_reviewed_at,
        "content_sha256": item.content_sha256,
        "source_identity": item.source_identity,
        "ingestion_quality_status": item.ingestion_quality_status,
        "ingestion_quality_notes": item.ingestion_quality_notes,
        "retrieval_visibility": item.retrieval_visibility,
        "ocr_quality_score": float(item.ocr_quality_score) if item.ocr_quality_score is not None else None,
        "ocr_quality_label": item.ocr_quality_label,
        "relation_sync_status": item.relation_sync_status,
        "relation_sync_details": item.relation_sync_details,
        "relation_count": int(resolved_metrics.get("relation_count", 0)),
        "is_seed": item.is_seed,
        "is_active": item.is_active,
        "chunk_count": int(resolved_metrics.get("chunk_count", 0)),
        "embedded_chunk_count": int(resolved_metrics.get("embedded_chunk_count", 0)),
        "embedding_status": str(resolved_metrics.get("embedding_status", "not_indexed")),
    })


def _serialize_user(item) -> AdminUserItem:
    return AdminUserItem.model_validate({
        "id": item.id,
        "full_name": item.full_name,
        "email": item.email,
        "role": item.role,
        "is_active": item.is_active,
        "created_at": item.created_at,
    })


def _slugify_filename(value: str) -> str:
    return admin_upload_service.slugify_filename(value)


def _humanize_filename(value: str) -> str:
    return admin_upload_service.humanize_filename(value)


def _remove_uploaded_file(storage_path: str) -> None:
    admin_upload_service.remove_uploaded_file(storage_path)


def _build_metadata_ai_settings() -> MetadataAISettingsPayload:
    return admin_settings_service.build_metadata_ai_settings()


def _build_embedding_ai_settings() -> EmbeddingAISettingsPayload:
    return admin_settings_service.build_embedding_ai_settings()


def _build_chatbot_ai_settings() -> ChatbotAISettingsPayload:
    return admin_settings_service.build_chatbot_ai_settings()


def _build_graph_backend_settings() -> GraphBackendSettingsPayload:
    return admin_settings_service.build_graph_backend_settings()


def _metadata_model_options_for_provider(provider: str) -> tuple[str, ...]:
    return admin_settings_service.metadata_model_options_for_provider(provider)


def _chat_model_options_for_provider(provider: str) -> tuple[str, ...]:
    return admin_settings_service.chat_model_options_for_provider(provider)


def _serialize_document_type(item) -> DefinitionItem:
    return DefinitionItem.model_validate({
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "description": item.description,
        "priority": item.normative_level,
        "is_active": item.is_active,
    })


def _serialize_authority_level(item) -> DefinitionItem:
    return DefinitionItem.model_validate({
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "description": item.description,
        "priority": item.hierarchy_rank,
        "is_active": item.is_active,
    })


def _persist_env_value(key: str, value: str) -> None:
    admin_settings_service.persist_env_value(key, value)
