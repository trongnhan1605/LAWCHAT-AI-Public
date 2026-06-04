from datetime import date

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.services.annotation_prelabel_service import annotation_prelabel_service


def test_annotation_prelabel_service_builds_label_studio_task() -> None:
    document = Document(
        id=21,
        title="Luat Dat dai",
        file_name="luat-dat-dai.pdf",
        source_type="pdf",
        legal_domain="dat_dai",
        storage_path="x",
        document_type="Luat",
        document_code="45/2013/QH13",
        issuing_authority="Quoc hoi",
        signed_date=date(2013, 11, 29),
        effective_date=date(2014, 7, 1),
        legal_status="active",
        is_active=True,
    )
    article = LegalProvision(
        id=100,
        document_id=21,
        parent_provision_id=None,
        provision_level="article",
        article_number="1",
        clause_number=None,
        point_code=None,
        heading="Pham vi dieu chinh",
        content="Noi dung dieu 1",
        citation_label="Dieu 1",
        sort_key="1",
        is_active=True,
    )
    clause = LegalProvision(
        id=101,
        document_id=21,
        parent_provision_id=100,
        provision_level="clause",
        article_number="1",
        clause_number="1",
        point_code=None,
        heading=None,
        content="Nguoi su dung dat phai nop ho so khi dang ky, tru truong hop duoc mien; neu vi pham se bi thu hoi giay chung nhan.",
        citation_label="Khoan 1 Dieu 1",
        sort_key="2",
        is_active=True,
    )
    article_chunk = DocumentChunk(
        id=501,
        document_id=21,
        chunk_index=1,
        chunk_type="article",
        citation_label="Dieu 1",
        article_number="1",
        clause_number=None,
        point_number=None,
        content="Dieu 1\nPham vi dieu chinh\nNoi dung dieu 1",
        char_count=39,
    )
    clause_chunk = DocumentChunk(
        id=502,
        document_id=21,
        chunk_index=2,
        chunk_type="clause",
        citation_label="Khoan 1 Dieu 1",
        article_number="1",
        clause_number="1",
        point_number=None,
        content="Khoan 1 Dieu 1\nNguoi su dung dat phai nop ho so khi dang ky, tru truong hop duoc mien; neu vi pham se bi thu hoi giay chung nhan.",
        char_count=132,
    )
    relation = ProvisionRelation(
        id=301,
        source_document_id=21,
        source_provision_id=101,
        target_document_id=21,
        target_provision_id=100,
        relation_type="LEGAL_BASIS_PROVISION",
        relation_label="Can cu",
        source_excerpt=None,
        target_excerpt=None,
        extraction_method="rule",
        is_active=True,
    )

    payload = annotation_prelabel_service._build_payload_from_records(document, [article_chunk, clause_chunk], [article, clause], [relation])
    task = annotation_prelabel_service.build_label_studio_task(payload)

    assert payload.review_status == "predicted"
    assert payload.source_text
    assert payload.vendor == "internal_structure_prelabel"
    assert "Loai van ban" not in payload.source_text
    assert all(entity.label != "DOCUMENT_TITLE" for entity in payload.entities)
    assert any(entity.attributes.get("prediction_provenance") == "parser" for entity in payload.entities if entity.label == "ARTICLE")
    assert any(entity.label == "SUBJECT" for entity in payload.entities)
    assert any(entity.label == "ACTION" for entity in payload.entities)
    assert any(entity.label == "LEGAL_OBJECT" for entity in payload.entities)
    assert any(entity.label == "CONDITION" for entity in payload.entities)
    assert any(entity.label == "EXCEPTION" for entity in payload.entities)
    assert any(entity.label == "CONSEQUENCE" for entity in payload.entities)
    assert task["data"]["document_id"] == 21
    assert task["data"]["metadata_prelabels"]
    assert any(item["label"] == "DOCUMENT_CODE" and item["text"] == "45/2013/QH13" for item in task["data"]["metadata_prelabels"])
    assert "predictions" in task
    result = task["predictions"][0]["result"]
    assert any(item["type"] == "labels" and item["value"]["labels"] == ["ARTICLE"] for item in result)
    assert any(item["type"] == "relation" and item["labels"] == ["LEGAL_BASIS"] for item in result)
    assert any(item["type"] == "labels" and item["value"]["labels"] == ["SUBJECT"] for item in result)
    assert any(item["type"] == "relation" and item["labels"] == ["SUBJECT_OF"] for item in result)
    assert any(item["type"] == "relation" and item["labels"] == ["ACTS_ON"] for item in result)
    assert all(item["value"]["labels"] != ["DOCUMENT_TYPE"] for item in result if item["type"] == "labels")
