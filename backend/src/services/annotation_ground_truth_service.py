from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from src.schemas.annotation_schema import AnnotationDocumentPayload
from src.services.annotation_import_service import AnnotationImportSummary, annotation_import_service


@dataclass(slots=True)
class AnnotationGroundTruthSaveResult:
    file_name: str
    file_path: Path
    saved_at: str
    summary: AnnotationImportSummary
    bundle_counts: dict[str, int]


class AnnotationGroundTruthService:
    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or Path("backend/storage/annotation_ground_truth")

    def save_review_bundle(
        self,
        payload: AnnotationDocumentPayload,
        *,
        reviewer_user_id: int | None = None,
    ) -> AnnotationGroundTruthSaveResult:
        saved_at = datetime.now(timezone.utc).isoformat()
        normalized_payload = payload.model_copy(update={"review_status": "reviewed"})
        bundle = annotation_import_service.build_import_bundle(normalized_payload)
        summary = annotation_import_service.summarize(normalized_payload)
        bundle_counts = {
            "metadata_fields": len(bundle.metadata_fields),
            "provisions": len(bundle.provisions),
            "provision_relations": len(bundle.provision_relations),
            "semantic_entities": len(bundle.semantic_entities),
            "concept_candidates": len(bundle.concept_candidates),
            "norm_statements": len(bundle.norm_statements),
            "warnings": len(bundle.warnings),
        }

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        file_name = self._build_file_name(normalized_payload, saved_at)
        file_path = self.storage_dir / file_name
        export_payload = {
            "schema_version": "annotation_ground_truth.v1",
            "saved_at": saved_at,
            "reviewer_user_id": reviewer_user_id,
            "document_id": normalized_payload.document_id,
            "payload": normalized_payload.model_dump(mode="json"),
            "import_summary": {
                "vendor": summary.vendor,
                "document_id": summary.document_id,
                "source_file_name": summary.source_file_name,
                "entity_count": summary.entity_count,
                "relation_count": summary.relation_count,
                "metadata_fields": summary.metadata_fields,
                "provision_count": summary.provision_count,
                "provision_relation_count": summary.provision_relation_count,
                "semantic_entity_count": summary.semantic_entity_count,
                "warnings": summary.warnings,
            },
            "import_bundle": {
                "metadata_fields": bundle.metadata_fields,
                "provisions": bundle.provisions,
                "provision_relations": bundle.provision_relations,
                "semantic_entities": bundle.semantic_entities,
                "concept_candidates": bundle.concept_candidates,
                "norm_statements": bundle.norm_statements,
                "warnings": bundle.warnings,
            },
            "bundle_counts": bundle_counts,
        }
        file_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return AnnotationGroundTruthSaveResult(
            file_name=file_name,
            file_path=file_path,
            saved_at=saved_at,
            summary=summary,
            bundle_counts=bundle_counts,
        )

    def resolve_file(self, file_name: str) -> Path:
        safe_name = Path(file_name).name
        if safe_name != file_name or not safe_name.endswith(".json"):
            raise ValueError("Invalid ground-truth file name")
        file_path = (self.storage_dir / safe_name).resolve()
        storage_root = self.storage_dir.resolve()
        if storage_root not in file_path.parents:
            raise ValueError("Invalid ground-truth file path")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(safe_name)
        return file_path

    def _build_file_name(self, payload: AnnotationDocumentPayload, saved_at: str) -> str:
        document_part = f"document_{payload.document_id}" if payload.document_id is not None else "document_unknown"
        timestamp = re.sub(r"[^0-9]", "", saved_at)[:14]
        source_part = self._slugify(Path(payload.source_file_name or "").stem)
        parts = [document_part]
        if source_part:
            parts.append(source_part[:48])
        parts.extend([timestamp, "ground_truth"])
        return "_".join(parts) + ".json"

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return normalized


annotation_ground_truth_service = AnnotationGroundTruthService()
