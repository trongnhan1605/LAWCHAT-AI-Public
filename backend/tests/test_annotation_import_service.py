from src.schemas.annotation_schema import AnnotationDocumentPayload
from src.services.annotation_import_service import annotation_import_service


def test_annotation_import_service_extracts_document_metadata() -> None:
    payload = AnnotationDocumentPayload(
        document_id=12,
        vendor="ubiai",
        source_file_name="nghi-dinh.pdf",
        entities=[
            {"id": "m1", "label": "DOCUMENT_TYPE", "text": "Nghị định"},
            {"id": "m2", "label": "DOCUMENT_CODE", "text": "291/2025/NĐ-CP"},
            {"id": "m3", "label": "ISSUING_AUTHORITY", "text": "Chính phủ"},
        ],
    )

    metadata = annotation_import_service.extract_document_metadata(payload)

    assert metadata == {
        "document_type": "Nghị định",
        "document_code": "291/2025/NĐ-CP",
        "issuing_authority": "Chính phủ",
    }


def test_annotation_import_service_builds_provision_payloads_and_relations() -> None:
    payload = AnnotationDocumentPayload(
        vendor="ubiai",
        entities=[
            {
                "id": "a1",
                "label": "ARTICLE",
                "text": "Điều 1. Phạm vi điều chỉnh",
                "start": 0,
                "attributes": {"article_number": "1", "heading": "Phạm vi điều chỉnh", "content": "Nội dung điều 1"},
            },
            {
                "id": "c1",
                "label": "CLAUSE",
                "text": "1. Khoản mẫu",
                "start": 30,
                "attributes": {"article_number": "1", "clause_number": "1", "content": "Nội dung khoản 1"},
            },
            {
                "id": "a2",
                "label": "ARTICLE",
                "text": "Điều 2. Căn cứ",
                "start": 60,
                "attributes": {"article_number": "2", "heading": "Căn cứ", "content": "Nội dung điều 2"},
            },
        ],
        relations=[
            {
                "id": "r1",
                "relation_type": "LEGAL_BASIS",
                "source_entity_id": "c1",
                "target_entity_id": "a2",
                "confidence_score": 0.95,
            }
        ],
    )

    provisions = annotation_import_service.build_provision_payloads(payload)
    relations = annotation_import_service.build_provision_relation_payloads(payload)

    assert len(provisions) == 3
    assert provisions[0]["provision_level"] == "article"
    assert provisions[1]["provision_level"] == "clause"
    assert provisions[1]["parent_provision_id"] == 1
    assert provisions[2]["article_number"] == "2"
    assert len(relations) == 1
    assert relations[0]["relation_type"] == "LEGAL_BASIS_PROVISION"


def test_annotation_import_service_summarizes_annotation_payload() -> None:
    payload = AnnotationDocumentPayload(
        document_id=99,
        vendor="ubiai",
        source_file_name="trial.pdf",
        entities=[
            {"id": "a1", "label": "ARTICLE", "text": "Điều 1", "start": 0, "attributes": {"article_number": "1"}},
            {"id": "s1", "label": "SUBJECT", "text": "Người sử dụng đất", "start": 10},
        ],
        relations=[
            {
                "id": "rel-x",
                "relation_type": "LEGAL_BASIS",
                "source_entity_id": "a1",
                "target_entity_id": "missing",
            }
        ],
    )

    summary = annotation_import_service.summarize(payload)

    assert summary.vendor == "ubiai"
    assert summary.document_id == 99
    assert summary.entity_count == 2
    assert summary.relation_count == 1
    assert summary.provision_count == 1
    assert summary.semantic_entity_count == 1
    assert summary.warnings


def test_annotation_import_service_builds_semantic_bundle() -> None:
    payload = AnnotationDocumentPayload(
        document_id=7,
        vendor="ubiai",
        source_file_name="semantic.pdf",
        entities=[
            {"id": "art-1", "label": "ARTICLE", "text": "Điều 1", "start": 0, "attributes": {"article_number": "1"}},
            {"id": "sub-1", "label": "SUBJECT", "text": "Nhà đầu tư nước ngoài", "start": 10},
            {"id": "act-1", "label": "ACTION", "text": "thực hiện", "start": 36},
            {"id": "obj-1", "label": "LEGAL_OBJECT", "text": "dự án đầu tư", "start": 48},
            {"id": "cond-1", "label": "CONDITION", "text": "khi đáp ứng điều kiện", "start": 70},
            {"id": "review-1", "label": "NEEDS_REVIEW", "text": "đoạn mơ hồ", "start": 100},
        ],
        relations=[
            {
                "id": "sr-1",
                "relation_type": "SUBJECT_OF",
                "source_entity_id": "sub-1",
                "target_entity_id": "act-1",
                "confidence_score": 0.93,
            },
            {
                "id": "sr-2",
                "relation_type": "ACTS_ON",
                "source_entity_id": "act-1",
                "target_entity_id": "obj-1",
                "confidence_score": 0.91,
            },
            {
                "id": "sr-3",
                "relation_type": "HAS_CONDITION",
                "source_entity_id": "act-1",
                "target_entity_id": "cond-1",
                "confidence_score": 0.88,
            },
        ],
    )

    bundle = annotation_import_service.build_import_bundle(payload)

    assert bundle.metadata_fields == {}
    assert len(bundle.provisions) == 1
    assert len(bundle.semantic_entities) == 4
    assert len(bundle.concept_candidates) == 2
    assert len(bundle.norm_statements) == 3
    assert any("Review-required labels detected" in warning for warning in bundle.warnings)
