from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.schemas.base import BaseResponse


class AnnotationEntityAttributePayload(BaseModel):
    key: str
    value: str | int | float | bool | None


class AnnotationEntityPayload(BaseModel):
    id: str
    label: str
    text: str
    start: int | None = None
    end: int | None = None
    normalized_value: str | None = None
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AnnotationRelationPayload(BaseModel):
    id: str
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    confidence_score: float | None = None
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AnnotationDocumentPayload(BaseModel):
    document_id: int | None = None
    vendor: str = "internal"
    source_file_name: str | None = None
    source_text: str | None = None
    language: str = "vi"
    review_status: str = "draft"
    entities: list[AnnotationEntityPayload] = Field(default_factory=list)
    relations: list[AnnotationRelationPayload] = Field(default_factory=list)


class AnnotationImportSummaryPayload(BaseModel):
    vendor: str
    document_id: int | None = None
    source_file_name: str | None = None
    entity_count: int
    relation_count: int
    metadata_fields: dict[str, str] = Field(default_factory=dict)
    provision_count: int
    provision_relation_count: int
    semantic_entity_count: int
    warnings: list[str] = Field(default_factory=list)


class AnnotationImportSummaryResponse(BaseResponse[AnnotationImportSummaryPayload]):
    pass


class AnnotationVendorExportPayload(BaseModel):
    vendor: str
    document_id: int
    task: dict[str, Any]
    internal_payload: AnnotationDocumentPayload
    import_summary: AnnotationImportSummaryPayload


class AnnotationVendorExportResponse(BaseResponse[AnnotationVendorExportPayload]):
    pass


class AnnotationVendorImportRequest(BaseModel):
    vendor: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class AnnotationVendorImportPreviewItem(BaseModel):
    index: int
    internal_payload: AnnotationDocumentPayload
    import_summary: AnnotationImportSummaryPayload


class AnnotationVendorImportPreviewPayload(BaseModel):
    vendor: str
    item_count: int
    items: list[AnnotationVendorImportPreviewItem] = Field(default_factory=list)


class AnnotationVendorImportPreviewResponse(BaseResponse[AnnotationVendorImportPreviewPayload]):
    pass


class AnnotationGroundTruthSaveRequest(BaseModel):
    payload: AnnotationDocumentPayload


class AnnotationGroundTruthSavePayload(BaseModel):
    file_name: str
    download_url: str
    saved_at: str
    import_summary: AnnotationImportSummaryPayload
    bundle_counts: dict[str, int] = Field(default_factory=dict)


class AnnotationGroundTruthSaveResponse(BaseResponse[AnnotationGroundTruthSavePayload]):
    pass
