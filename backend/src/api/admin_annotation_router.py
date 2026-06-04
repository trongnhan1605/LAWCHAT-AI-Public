from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user, require_roles
from src.schemas.annotation_schema import (
    AnnotationGroundTruthSavePayload,
    AnnotationGroundTruthSaveRequest,
    AnnotationGroundTruthSaveResponse,
    AnnotationImportSummaryPayload,
    AnnotationVendorExportPayload,
    AnnotationVendorExportResponse,
    AnnotationVendorImportPreviewItem,
    AnnotationVendorImportPreviewPayload,
    AnnotationVendorImportPreviewResponse,
    AnnotationVendorImportRequest,
)
from src.services.annotation_ground_truth_service import annotation_ground_truth_service
from src.services.annotation_import_service import AnnotationImportSummary, annotation_import_service
from src.services.annotation_prelabel_service import annotation_prelabel_service
from src.services.annotation_vendor_adapter_service import (
    UnsupportedAnnotationVendorError,
    annotation_vendor_adapter_service,
)

router = APIRouter(prefix="/admin/annotation", tags=["admin-annotation"], dependencies=[Depends(require_roles("admin"))])


@router.get("/label-studio/export-preview/{document_id}", response_model=AnnotationVendorExportResponse)
def export_label_studio_annotation_preview(document_id: int, db: Session = Depends(get_db)) -> AnnotationVendorExportResponse:
    try:
        internal_payload = annotation_prelabel_service.build_document_payload(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    task = annotation_prelabel_service.build_label_studio_task(internal_payload)
    summary = annotation_import_service.summarize(internal_payload)
    payload = AnnotationVendorExportPayload(
        vendor="label_studio",
        document_id=document_id,
        task=task,
        internal_payload=internal_payload,
        import_summary=_summary_payload(summary),
    )
    return AnnotationVendorExportResponse(success=True, message="Label Studio annotation preview generated", data=payload)


@router.post("/import-preview", response_model=AnnotationVendorImportPreviewResponse)
def import_annotation_preview(payload: AnnotationVendorImportRequest) -> AnnotationVendorImportPreviewResponse:
    items: list[AnnotationVendorImportPreviewItem] = []

    for index, raw_item in enumerate(payload.items):
        try:
            internal_payload = annotation_vendor_adapter_service.to_document_payload(payload.vendor, raw_item)
        except UnsupportedAnnotationVendorError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        summary = annotation_import_service.summarize(internal_payload)
        items.append(
            AnnotationVendorImportPreviewItem(
                index=index,
                internal_payload=internal_payload,
                import_summary=_summary_payload(summary),
            )
        )

    response_payload = AnnotationVendorImportPreviewPayload(
        vendor=payload.vendor,
        item_count=len(items),
        items=items,
    )
    return AnnotationVendorImportPreviewResponse(success=True, message="Annotation import preview generated", data=response_payload)


@router.post("/ground-truth/save", response_model=AnnotationGroundTruthSaveResponse)
def save_annotation_ground_truth(
    payload: AnnotationGroundTruthSaveRequest,
    current_user=Depends(get_current_user),
) -> AnnotationGroundTruthSaveResponse:
    result = annotation_ground_truth_service.save_review_bundle(payload.payload, reviewer_user_id=current_user.id)
    response_payload = AnnotationGroundTruthSavePayload(
        file_name=result.file_name,
        download_url=f"/admin/annotation/ground-truth/download/{result.file_name}",
        saved_at=result.saved_at,
        import_summary=_summary_payload(result.summary),
        bundle_counts=result.bundle_counts,
    )
    return AnnotationGroundTruthSaveResponse(success=True, message="Annotation ground-truth saved", data=response_payload)


@router.get("/ground-truth/download/{file_name}")
def download_annotation_ground_truth(file_name: str) -> FileResponse:
    try:
        file_path = annotation_ground_truth_service.resolve_file(file_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ground-truth file not found") from exc
    return FileResponse(file_path, filename=file_path.name, media_type="application/json")


def _summary_payload(summary: AnnotationImportSummary) -> AnnotationImportSummaryPayload:
    return AnnotationImportSummaryPayload(
        vendor=summary.vendor,
        document_id=summary.document_id,
        source_file_name=summary.source_file_name,
        entity_count=summary.entity_count,
        relation_count=summary.relation_count,
        metadata_fields=summary.metadata_fields,
        provision_count=summary.provision_count,
        provision_relation_count=summary.provision_relation_count,
        semantic_entity_count=summary.semantic_entity_count,
        warnings=summary.warnings,
    )
