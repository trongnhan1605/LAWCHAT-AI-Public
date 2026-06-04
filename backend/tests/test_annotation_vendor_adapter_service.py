from src.services.annotation_vendor_adapter_service import (
    UnsupportedAnnotationVendorError,
    annotation_vendor_adapter_service,
)


def test_label_studio_adapter_builds_internal_payload() -> None:
    raw_item = {
        "id": 10,
        "data": {
            "document_id": 77,
            "source_file_name": "luat-dat-dai.pdf",
            "language": "vi",
            "text": "Điều 1 Nhà đầu tư thực hiện dự án đầu tư",
            "metadata_prelabels": [
                {
                    "id": "meta-1",
                    "label": "DOCUMENT_CODE",
                    "text": "45/2013/QH13",
                    "normalized_value": "45/2013/QH13",
                    "attributes": {"review_mode": "structured_field"},
                }
            ],
        },
        "annotations": [
            {
                "result": [
                    {
                        "id": "e1",
                        "type": "labels",
                        "value": {
                            "start": 0,
                            "end": 6,
                            "text": "Điều 1",
                            "labels": ["ARTICLE"],
                            "article_number": "1",
                        },
                    },
                    {
                        "id": "e2",
                        "type": "labels",
                        "value": {
                            "start": 7,
                            "end": 18,
                            "text": "Nhà đầu tư",
                            "labels": ["SUBJECT"],
                        },
                        "score": 0.94,
                    },
                    {
                        "id": "e3",
                        "type": "labels",
                        "value": {
                            "start": 19,
                            "end": 29,
                            "text": "thực hiện",
                            "labels": ["ACTION"],
                        },
                    },
                    {
                        "id": "r1",
                        "type": "relation",
                        "from_id": "e2",
                        "to_id": "e3",
                        "labels": ["SUBJECT_OF"],
                        "direction": "right",
                    },
                ]
            }
        ],
    }

    payload = annotation_vendor_adapter_service.to_document_payload("label_studio", raw_item)

    assert payload.vendor == "label_studio"
    assert payload.document_id == 77
    assert payload.source_file_name == "luat-dat-dai.pdf"
    assert payload.source_text == "Điều 1 Nhà đầu tư thực hiện dự án đầu tư"
    assert payload.review_status == "reviewed"
    assert len(payload.entities) == 4
    assert payload.entities[0].label == "DOCUMENT_CODE"
    assert payload.entities[0].normalized_value == "45/2013/QH13"
    assert payload.entities[1].label == "ARTICLE"
    assert payload.entities[1].attributes["article_number"] == "1"
    assert payload.entities[2].attributes["prediction_score"] == 0.94
    assert len(payload.relations) == 1
    assert payload.relations[0].relation_type == "SUBJECT_OF"
    assert payload.relations[0].attributes["direction"] == "right"


def test_annotation_vendor_adapter_service_rejects_unknown_vendor() -> None:
    try:
        annotation_vendor_adapter_service.to_document_payload("ubiai", {})
    except UnsupportedAnnotationVendorError as exc:
        assert "label_studio" in str(exc)
    else:
        raise AssertionError("Expected UnsupportedAnnotationVendorError")

def test_label_studio_adapter_flattens_relation_value_attributes() -> None:
    raw_item = {
        "data": {"document_id": 78, "text": "Điều 1. Test"},
        "predictions": [
            {
                "result": [
                    {"id": "e1", "type": "labels", "value": {"start": 0, "end": 6, "text": "Điều 1", "labels": ["ARTICLE"]}},
                    {"id": "e2", "type": "labels", "value": {"start": 8, "end": 12, "text": "Test", "labels": ["CLAUSE"]}},
                    {
                        "id": "r1",
                        "type": "relation",
                        "from_id": "e1",
                        "to_id": "e2",
                        "labels": ["LEGAL_BASIS"],
                        "value": {"source": "LawChat_semantic_prelabel", "prediction_provenance": "rule"},
                    },
                ]
            }
        ],
    }

    payload = annotation_vendor_adapter_service.to_document_payload("label_studio", raw_item)

    assert payload.review_status == "predicted"
    assert payload.relations[0].attributes["source"] == "LawChat_semantic_prelabel"
    assert payload.relations[0].attributes["prediction_provenance"] == "rule"
    assert "value" not in payload.relations[0].attributes
