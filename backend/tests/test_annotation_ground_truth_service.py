from pathlib import Path
from uuid import uuid4

from src.schemas.annotation_schema import AnnotationDocumentPayload
from src.services.annotation_ground_truth_service import AnnotationGroundTruthService


def _test_storage_dir() -> Path:
    storage_dir = Path("backend/.tmp-annotation-ground-truth-tests") / uuid4().hex
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def test_annotation_ground_truth_service_saves_review_bundle() -> None:
    service = AnnotationGroundTruthService(storage_dir=_test_storage_dir())
    payload = AnnotationDocumentPayload(
        document_id=15,
        vendor="internal_review",
        source_file_name="luat-test.pdf",
        source_text="Điều 1. Người sử dụng đất phải đăng ký.",
        entities=[
            {"id": "a1", "label": "ARTICLE", "text": "Điều 1", "start": 0, "end": 6, "attributes": {"article_number": "1"}},
            {"id": "s1", "label": "SUBJECT", "text": "Người sử dụng đất", "start": 8, "end": 25},
        ],
        relations=[],
    )

    result = service.save_review_bundle(payload, reviewer_user_id=9)

    assert result.file_name.startswith("document_15_")
    assert result.file_path.exists()
    assert result.summary.entity_count == 2
    assert result.summary.provision_count == 1
    assert result.bundle_counts["concept_candidates"] == 1
    assert '"reviewer_user_id": 9' in result.file_path.read_text(encoding="utf-8")


def test_annotation_ground_truth_service_resolves_only_saved_json() -> None:
    storage_dir = _test_storage_dir()
    service = AnnotationGroundTruthService(storage_dir=storage_dir)
    file_path = storage_dir / "document_1_ground_truth.json"
    file_path.write_text("{}", encoding="utf-8")

    assert service.resolve_file(file_path.name) == file_path.resolve()
