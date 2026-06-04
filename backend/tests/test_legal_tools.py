from __future__ import annotations

from datetime import date, timedelta
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.models.citation import Citation
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.rules.legal_hierarchy import HierarchySnapshot, compare_hierarchy
from src.services.document_benchmark_service import document_benchmark_service
from src.services.document_relation_service import document_relation_service
from src.services.graph_service import graph_service
from src.services.legal_metadata_parser_service import legal_metadata_parser_service
from src.services.legal_provision_parser_service import legal_provision_parser_service
from src.services.provision_relation_service import provision_relation_service
from src.services.ocr_service import OcrDiagnosticResult, OcrPageResult
from src.tools.check_validity import evaluate_document_validity
from src.tools.get_related_articles import get_related_articles
from src.tools.resolve_conflict import resolve_document_conflict
from src.tools.search_law import search_law
from src.validation.legal_validation_coordinator import legal_validation_coordinator
from src.validation.legal_response_validator import validate_legal_response


search_law_module = importlib.import_module("src.tools.search_law")


def make_document(**overrides: object) -> Document:
    today = date.today()
    defaults = {
        "title": "Luat Lao dong",
        "file_name": "luat-lao-dong.txt",
        "source_type": "txt",
        "legal_domain": "lao-dong",
        "storage_path": "docs/legal/luat-lao-dong.txt",
        "document_type": "luat",
        "authority_level": "quoc-hoi",
        "normative_level": None,
        "signed_date": today - timedelta(days=30),
        "effective_date": today - timedelta(days=15),
        "expiry_date": None,
        "legal_status": "active",
    }
    defaults.update(overrides)
    return Document(**defaults)


def make_chunk(**overrides: object) -> DocumentChunk:
    defaults = {
        "document_id": 1,
        "chunk_index": 1,
        "section_title": "Dieu 1",
        "chunk_type": "article",
        "citation_label": "Dieu 1",
        "hierarchy_path": "Chuong I > Dieu 1",
        "article_number": "1",
        "clause_number": None,
        "point_number": None,
        "retrieval_text": "Dieu 1",
        "content": "Noi dung phap ly mau",
        "metadata_json": None,
        "char_count": 120,
    }
    defaults.update(overrides)
    return DocumentChunk(**defaults)


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return session_factory()


def test_evaluate_document_validity_marks_active_document_as_authoritative() -> None:
    result = evaluate_document_validity(make_document())

    assert result.status == "active"
    assert result.is_currently_effective is True
    assert result.is_authoritative is True
    assert result.reasons == ["Document is active within the evaluated date range."]


def test_evaluate_document_validity_rejects_expired_document() -> None:
    result = evaluate_document_validity(
        make_document(
            legal_status="expired",
            expiry_date=date.today() - timedelta(days=1),
        )
    )

    assert result.is_currently_effective is False
    assert result.is_authoritative is False
    assert any("expired" in reason.lower() for reason in result.reasons)


def test_resolve_document_conflict_prefers_authoritative_document() -> None:
    authoritative = make_document(id=1, legal_status="active")
    draft = make_document(id=2, legal_status="draft")

    result = resolve_document_conflict(authoritative, draft)

    assert result.winner_document_id == 1
    assert result.loser_document_id == 2
    assert result.resolution_basis == "validity"


def test_resolve_document_conflict_uses_hierarchy_before_signed_date() -> None:
    lower = make_document(id=10, document_type="thong-tu", authority_level="bo")
    higher = make_document(id=20, document_type="luat", authority_level="quoc-hoi")

    result = resolve_document_conflict(lower, higher)

    assert result.winner_document_id == 20
    assert result.resolution_basis == "hierarchy"


def test_compare_hierarchy_prefers_explicit_normative_level() -> None:
    left = HierarchySnapshot(document_type="thong-tu", authority_level="bo", normative_level=120)
    right = HierarchySnapshot(document_type="luat", authority_level="quoc-hoi", normative_level=95)

    assert compare_hierarchy(left, right) == 1


def test_validate_legal_response_marks_missing_evidence_for_review() -> None:
    result = validate_legal_response(
        retrieved_results=[],
        authoritative_result_count=0,
        unresolved_conflict=False,
        detected_complexity="low",
    )

    assert result.validation_status == "needs_review"
    assert result.escalation_recommended is True
    assert result.confidence_score == 0.5
    assert "No legal evidence was retrieved." in result.findings


def test_validate_legal_response_passes_with_authoritative_evidence() -> None:
    evidence = [
        SimpleNamespace(
            document_id=1,
            chunk_id=10,
            document_title="Bo luat Lao dong",
            citation_label="Dieu 10",
            hierarchy_path="Phan I > Dieu 10",
            legal_status="active",
            source_reference="https://example.test/luat",
            score=92,
            excerpt="Noi dung co can cu phap ly.",
        )
    ]

    result = validate_legal_response(
        retrieved_results=evidence,
        authoritative_result_count=1,
        unresolved_conflict=False,
        detected_complexity="low",
    )

    assert result.validation_status == "passed"
    assert result.escalation_recommended is False
    assert result.warning_text is None
    assert result.findings == ["Only one evidence item was retrieved."]


def test_search_law_maps_chunk_results_and_truncates_excerpt(monkeypatch) -> None:
    captured: dict[str, object] = {}
    long_excerpt = " ".join(["can-cu"] * 400)
    document = make_document(id=7, title="Luat Dat dai", source_reference="https://example.test/dat-dai")
    chunk = SimpleNamespace(
        id=99,
        citation_label="Dieu 12",
        hierarchy_path="Chuong II > Dieu 12",
        content=long_excerpt,
    )

    def fake_search_chunks(db, query: str, limit: int, preferred_terms: list[str] | None = None, legal_domain: str | None = None, allow_unreviewed: bool = False):
        captured["db"] = db
        captured["query"] = query
        captured["limit"] = limit
        captured["preferred_terms"] = preferred_terms
        captured["legal_domain"] = legal_domain
        captured["allow_unreviewed"] = allow_unreviewed
        return [(document, chunk, 88)]

    monkeypatch.setattr(search_law_module.legal_retrieval_service, "search_chunks", fake_search_chunks)

    fake_db = object()
    result = search_law(fake_db, "kiem tra hieu luc", limit=3, preferred_terms=["hieu luc"], legal_domain="lao-dong", allow_unreviewed=True)

    assert captured["db"] is fake_db
    assert captured["query"] == "kiem tra hieu luc"
    assert captured["limit"] == 3
    assert captured["preferred_terms"] == ["hieu luc"]
    assert captured["legal_domain"] == "lao-dong"
    assert captured["allow_unreviewed"] is True
    assert len(result) == 1
    assert result[0].document_id == 7
    assert result[0].chunk_id == 99
    assert result[0].citation_label == "Dieu 12"
    assert result[0].source_reference == "https://example.test/dat-dai"
    assert result[0].score == 88
    assert len(result[0].excerpt) == 323
    assert result[0].excerpt.endswith("...")


def test_get_related_articles_returns_same_document_context_and_document_relations() -> None:
    db = create_test_session()
    source_document = make_document(id=1, title="Luat Dat dai")
    related_document = make_document(id=2, title="Nghi dinh Huong dan", source_reference="https://example.test/nghi-dinh")
    db.add_all(
        [
            source_document,
            related_document,
            make_chunk(id=100, document_id=1, chunk_index=1, article_number="12", citation_label="Dieu 12"),
            make_chunk(id=101, document_id=1, chunk_index=2, article_number="12", citation_label="Khoan 1 Dieu 12"),
            make_chunk(id=200, document_id=2, chunk_index=1, article_number="3", citation_label="Dieu 3"),
            DocumentRelation(
                source_document_id=1,
                target_document_id=2,
                relation_type="amends",
                relation_label="Sua doi, bo sung",
                legal_basis="Dieu 3",
                confidence_score=0.9,
                is_active=True,
                metadata_json=None,
            ),
        ]
    )
    db.commit()

    search_results = [
        SimpleNamespace(
            document_id=1,
            chunk_id=100,
            document_title="Luat Dat dai",
            citation_label="Dieu 12",
            hierarchy_path="Chuong II > Dieu 12",
            legal_status="active",
            source_reference="https://example.test/dat-dai",
            score=91,
            excerpt="Noi dung dieu 12",
        )
    ]

    result = get_related_articles(db, search_results, limit=4)

    assert len(result) == 2
    assert result[0].relation_type == "same_document_context"
    assert result[0].chunk_id == 101
    assert result[1].relation_type == "amends"
    assert result[1].document_id == 2

    db.close()


def test_legal_validation_coordinator_penalizes_missing_citation_metadata() -> None:
    document = make_document(id=1)
    retrieved_results = [
        SimpleNamespace(
            document_id=1,
            chunk_id=10,
            document_title=document.title,
            citation_label=None,
            hierarchy_path="Chuong I > Dieu 1",
            legal_status="active",
            source_reference=None,
            score=82,
            excerpt="Noi dung lien quan.",
        )
    ]

    result = legal_validation_coordinator.evaluate(
        retrieved_results=retrieved_results,
        evidence_documents={1: document},
        unresolved_conflict=False,
        detected_complexity="low",
        related_articles=[],
    )

    assert result.validation_status == "passed"
    assert result.escalation_recommended is False
    assert result.authoritative_result_count == 1
    assert result.citation_coverage_score == 0.0
    assert "Some retrieved evidence is missing complete citation integrity metadata." in result.findings
    assert "Citation for document id 1 is missing citation label." in result.findings
    assert result.confidence_score == 0.68


def test_legal_validation_coordinator_warns_on_missing_legal_status_metadata() -> None:
    document = make_document(id=9, legal_status=None, effective_date=None)
    retrieved_results = [
        SimpleNamespace(
            document_id=9,
            chunk_id=90,
            document_title=document.title,
            citation_label="Dieu 1",
            hierarchy_path="Chuong I > Dieu 1",
            legal_status=None,
            source_reference="https://example.test/luat",
            score=82,
            excerpt="Noi dung lien quan.",
        )
    ]

    result = legal_validation_coordinator.evaluate(
        retrieved_results=retrieved_results,
        evidence_documents={9: document},
        unresolved_conflict=False,
        detected_complexity="low",
        related_articles=[],
    )

    assert result.validation_status == "needs_review"
    assert result.escalation_recommended is True
    assert "Document id 9 is missing legal_status metadata." in result.findings
    assert "Document id 9 is missing effective_date metadata." in result.findings


def test_legal_validation_coordinator_checks_response_citation_consistency() -> None:
    document = make_document(id=12, title="Luat Dat dai", legal_domain="dat-dai")
    retrieved_results = [
        SimpleNamespace(
            document_id=12,
            chunk_id=120,
            document_title=document.title,
            citation_label="Dieu 75",
            hierarchy_path="Chuong VI > Dieu 75",
            legal_status="active",
            source_reference="https://example.test/dat-dai",
            score=90,
            excerpt="Nguoi su dung dat du dieu kien thi duoc boi thuong khi nha nuoc thu hoi dat.",
        )
    ]

    result = legal_validation_coordinator.evaluate(
        retrieved_results=retrieved_results,
        evidence_documents={12: document},
        unresolved_conflict=False,
        detected_complexity="low",
        related_articles=[],
        response_text="Ket luan: duoc boi thuong trong mot so truong hop.",
    )

    assert "Response text does not expose a legal basis section despite retrieved evidence." in result.findings
    assert "Response text omits top citation labels: Dieu 75." in result.findings
    assert result.confidence_score < 0.84


def test_legal_validation_coordinator_rewards_semantic_path_for_high_complexity() -> None:
    document = make_document(id=2, title="Luat Dat dai", legal_domain="dat-dai")
    retrieved_results = [
        SimpleNamespace(
            document_id=2,
            chunk_id=20,
            document_title=document.title,
            citation_label="Dieu 28",
            hierarchy_path="Chuong III > Dieu 28",
            legal_status="active",
            source_reference="https://example.test/dat-dai",
            score=90,
            excerpt="To chuc kinh te co von dau tu nuoc ngoai duoc xem xet quyen lien quan den dat dai.",
        )
    ]

    semantic_graph = {
        "matched_concepts": [
            {"id": 1, "label": "Nhà đầu tư nước ngoài"},
            {"id": 2, "label": "Doanh nghiệp có vốn đầu tư nước ngoài"},
            {"id": 3, "label": "Quyền sử dụng đất"},
        ],
        "edges": [
            {"source": 1, "target": 2, "edge_type": "CREATES_ENTITY", "label": "hình thành chủ thể"},
            {"source": 2, "target": 3, "edge_type": "ENABLES_RIGHT", "label": "mở ra quyền"},
        ],
    }

    result = legal_validation_coordinator.evaluate(
        retrieved_results=retrieved_results,
        evidence_documents={2: document},
        unresolved_conflict=False,
        detected_complexity="high",
        related_articles=[],
        semantic_graph=semantic_graph,
    )

    assert result.validation_status == "pass_with_warnings"
    assert result.escalation_recommended is False
    assert result.semantic_match_count == 3
    assert result.semantic_edge_count == 2
    assert "Semantic concept path was found to support multi-hop legal reasoning." in result.findings
    assert result.confidence_score == 0.68


def test_document_relation_service_extracts_amendment_relation() -> None:
    db = create_test_session()
    target_document = make_document(id=1, title="Bo luat Lao dong", document_code="45/2019/QH14")
    source_document = make_document(
        id=2,
        title="Luat sua doi Bo luat Lao dong",
        document_code="12/2026/QH15",
        summary="Van ban nay sua doi, bo sung Bo luat Lao dong so 45/2019/QH14.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(id=10, document_id=2, chunk_index=1, citation_label="Dieu 1", content="Van ban nay sua doi, bo sung Bo luat Lao dong so 45/2019/QH14."),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert summary.relation_types == {"amends": 1}
    assert relation.target_document_id == target_document.id
    assert relation.relation_type == "amends"

    db.close()


def test_document_relation_service_extracts_supplement_relation() -> None:
    db = create_test_session()
    target_document = make_document(id=31, title="Luat Dat dai", document_code="31/2024/QH15")
    source_document = make_document(
        id=32,
        title="Luat bo sung mot so dieu cua Luat Dat dai",
        document_code="14/2026/QH15",
        summary="Van ban nay bo sung mot so dieu cua Luat Dat dai so 31/2024/QH15.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=3201,
            document_id=32,
            chunk_index=1,
            citation_label="Dieu 1",
            content="Van ban nay bo sung mot so dieu cua Luat Dat dai so 31/2024/QH15.",
        ),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert summary.relation_types == {"supplements": 1}
    assert relation.relation_type == "supplements"

    db.close()


def test_document_relation_service_matches_imported_filename_code_alias() -> None:
    db = create_test_session()
    target_document = make_document(
        id=11,
        title="291 2025 ND CP 679921 [20260326_DD]",
        file_name="291_2025_ND-CP_679921.docx",
        document_code=None,
        source_type="docx",
    )
    source_document = make_document(
        id=12,
        title="Thong tu huong dan",
        document_code="19/2026/TT-BNNMT",
        summary="Can cu Nghi dinh so 291/2025/ND-CP ngay 31 thang 12 nam 2025 cua Chinh phu.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=1201,
            document_id=12,
            chunk_index=1,
            citation_label="Dieu 1",
            content="Can cu Nghi dinh so 291/2025/ND-CP ngay 31 thang 12 nam 2025 cua Chinh phu.",
        ),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert relation.target_document_id == target_document.id
    assert relation.relation_type == "legal_basis"

    db.close()


def test_legal_metadata_parser_normalizes_special_document_codes() -> None:
    preview_text = "\n".join(
        [
            "VAN BAN HOP NHAT",
            "So: 05/2024/VBHN-VPQH",
            "NGHI QUYET",
            "So: 12/2025/NQ-UBTVQH15",
            "THONG TU LIEN TICH",
            "So: 03/2024/TTLT-BTNMT-BTP",
        ]
    )

    mentions = legal_metadata_parser_service.extract_citation_code_mentions(preview_text)

    assert {item["code"] for item in mentions} >= {
        "05/2024/VBHN-VPQH",
        "12/2025/NQ-UBTVQH15",
        "03/2024/TTLT-BTNMT-BTP",
    }
    assert legal_metadata_parser_service.normalize_code(" 12 / 2024 / qh15 ") == "12/2024/QH15"


def test_legal_metadata_parser_infers_vbhn_metadata() -> None:
    inferred = legal_metadata_parser_service.infer_document_metadata(
        file_name="05_2024_VBHN-VPQH.docx",
        preview_text="\n".join(["VAN PHONG QUOC HOI", "VAN BAN HOP NHAT", "So: 05/2024/VBHN-VPQH", "Dat dai"]),
    )

    assert inferred["document_title"] == "Van ban hop nhat dat dai"
    assert inferred["document_code"] == "05/2024/VBHN-VPQH"
    assert inferred["document_type"] == "van-ban-hop-nhat"
    assert inferred["issuing_authority"] == "Văn phòng Quốc hội"
    assert inferred["authority_level"] == "van-phong-quoc-hoi"


def test_legal_metadata_parser_detects_placeholder_titles_from_file_name() -> None:
    assert legal_metadata_parser_service.looks_like_placeholder_title(
        "291 2025 ND CP 679921 [20260326_DD]",
        "291_2025_ND-CP_679921.docx",
    ) is True
    assert legal_metadata_parser_service.looks_like_placeholder_title(
        "Nghi dinh quy dinh chi tiet ve dat dai",
        "291_2025_ND-CP_679921.docx",
    ) is False


def test_document_relation_service_matches_ubtvqh_code_reference() -> None:
    db = create_test_session()
    target_document = make_document(
        id=13,
        title="Nghi quyet ve dat dai",
        file_name="12_2025_NQ-UBTVQH15.docx",
        document_code="12/2025/NQ-UBTVQH15",
        source_type="docx",
    )
    source_document = make_document(
        id=14,
        title="Thong tu trien khai",
        document_code="03/2026/TTLT-BTNMT-BTP",
        summary="Can cu Nghi quyet so 12/2025/NQ-UBTVQH15 cua Uy ban Thuong vu Quoc hoi.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=1401,
            document_id=14,
            chunk_index=1,
            citation_label="Dieu 1",
            content="Can cu Nghi quyet so 12/2025/NQ-UBTVQH15 cua Uy ban Thuong vu Quoc hoi.",
        ),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert relation.target_document_id == target_document.id
    assert relation.relation_type == "legal_basis"
    assert relation.confidence_score is not None and relation.confidence_score >= 0.68

    db.close()


def test_document_relation_service_extracts_consolidates_for_vbhn() -> None:
    db = create_test_session()
    target_document = make_document(id=41, title="Luat Dat dai", document_code="31/2024/QH15")
    source_document = make_document(
        id=42,
        title="Van ban hop nhat Luat Dat dai",
        document_code="05/2026/VBHN-VPQH",
        document_type="van-ban-hop-nhat",
        authority_level="van-phong-quoc-hoi",
        summary="Van ban hop nhat nay hop nhat noi dung cua Luat Dat dai so 31/2024/QH15 va cac van ban sua doi, bo sung.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=4201,
            document_id=42,
            chunk_index=1,
            citation_label="Can cu hop nhat",
            content="Van ban hop nhat nay hop nhat noi dung cua Luat Dat dai so 31/2024/QH15 va cac van ban sua doi, bo sung.",
        ),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert relation.target_document_id == target_document.id
    assert relation.relation_type == "consolidates"

    db.close()


def test_document_relation_service_splits_general_reference() -> None:
    db = create_test_session()
    target_document = make_document(id=51, title="Luat Dat dai", document_code="31/2024/QH15")
    source_document = make_document(
        id=52,
        title="Thong tu trien khai nghiep vu",
        document_code="22/2026/TT-BNNMT",
        summary="Theo quy dinh tai Luat Dat dai so 31/2024/QH15, viec lap ho so dia chinh duoc thuc hien theo quy trinh thong nhat.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=5201,
            document_id=52,
            chunk_index=1,
            citation_label="Dieu 2",
            content="Theo quy dinh tai Luat Dat dai so 31/2024/QH15, viec lap ho so dia chinh duoc thuc hien theo quy trinh thong nhat.",
        ),
    ])
    db.commit()

    summary = document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert summary.created_relations == 1
    assert relation.target_document_id == target_document.id
    assert relation.relation_type == "general_reference"

    db.close()


def test_document_relation_service_preserves_vietnamese_context_for_display() -> None:
    db = create_test_session()
    target_document = make_document(id=61, title="Quyết định hỗ trợ việc làm", document_code="52/2012/QD-TTG")
    source_document = make_document(
        id=62,
        title="Thông tư hướng dẫn",
        document_code="01/2026/TT-BLDTBXH",
        summary="Thông tư này hướng dẫn thực hiện Quyết định số 52/2012/QĐ-TTg ngày 16/11/2012 của Thủ tướng Chính phủ.",
    )
    db.add_all([
        target_document,
        source_document,
        make_chunk(
            id=6201,
            document_id=62,
            chunk_index=1,
            citation_label="Điều 1",
            content="Thông tư này hướng dẫn thực hiện Quyết định số 52/2012/QĐ-TTg ngày 16/11/2012 của Thủ tướng Chính phủ.",
        ),
    ])
    db.commit()

    document_relation_service.sync_document_relations(db, source_document.id)
    relation = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == source_document.id).one()

    assert relation.legal_basis is not None
    assert "Quyết định số 52/2012/QĐ-TTg" in relation.legal_basis
    assert "Thủ tướng Chính phủ" in relation.legal_basis

    db.close()


def test_graph_service_includes_provision_relation_evidence_on_document_edges() -> None:
    db = create_test_session()
    source_document = make_document(id=71, title="Thong tu huong dan", document_code="01/2026/TT-BTNMT")
    target_document = make_document(id=72, title="Nghi dinh dat dai", document_code="291/2025/ND-CP")
    db.add_all([source_document, target_document])
    db.flush()

    db.add(
        DocumentRelation(
            source_document_id=source_document.id,
            target_document_id=target_document.id,
            relation_type="legal_basis",
            relation_label="Căn cứ",
            legal_basis="Căn cứ Nghị định số 291/2025/NĐ-CP.",
            confidence_score=0.94,
            metadata_json=json.dumps({"evidence": {"target_anchor": "Điều 2", "target_excerpt": "Nội dung mục tiêu"}}),
            is_active=True,
        )
    )
    source_provision = LegalProvision(
            document_id=source_document.id,
            parent_provision_id=None,
            provision_level="article",
            article_number="3",
            clause_number=None,
            point_code=None,
            heading="Điều 3. Căn cứ thực hiện",
            content="Căn cứ khoản 1 Điều 2 Nghị định số 291/2025/NĐ-CP.",
            citation_label="Điều 3",
            sort_key="003.000.000",
            legal_status="active",
            metadata_json="{}",
            is_active=True,
        )
    target_provision = LegalProvision(
            document_id=target_document.id,
            parent_provision_id=None,
            provision_level="clause",
            article_number="2",
            clause_number="1",
            point_code=None,
            heading="1. Quy định chi tiết",
            content="Nội dung mục tiêu",
            citation_label="Điều 2 Khoản 1",
            sort_key="002.001.000",
            legal_status="active",
            metadata_json="{}",
            is_active=True,
        )
    db.add_all([source_provision, target_provision])
    db.flush()
    db.add(
        ProvisionRelation(
            source_document_id=source_document.id,
            source_provision_id=source_provision.id,
            target_document_id=target_document.id,
            target_provision_id=target_provision.id,
            relation_type="LEGAL_BASIS_PROVISION",
            relation_label="Căn cứ điều khoản",
            source_excerpt="Căn cứ khoản 1 Điều 2 Nghị định số 291/2025/NĐ-CP.",
            target_excerpt="Nội dung mục tiêu",
            confidence_score=0.92,
            extraction_method="rule-based",
            metadata_json=json.dumps({"source_citation_label": "Điều 3", "target_citation_label": "Điều 2 Khoản 1"}, ensure_ascii=False),
            is_active=True,
        )
    )
    db.commit()

    payload = graph_service.get_document_graph(db, source_document.id, depth=1)

    assert payload["edges"]
    edge = payload["edges"][0]
    assert edge["relation_type"] == "legal_basis"
    assert edge["provision_relation_count"] == 1
    assert edge["provision_relation_types"] == ["LEGAL_BASIS_PROVISION"]
    assert edge["provision_relation_samples"][0]["relation_label"] == "Căn cứ điều khoản"

    db.close()


def test_document_benchmark_service_scores_metadata_chunks_and_retrieval(monkeypatch) -> None:
    db = create_test_session()
    document = make_document(id=1, title="Bo luat Lao dong", document_code="45/2019/QH14", summary="Tom tat")
    article_chunk = make_chunk(id=1, document_id=1, chunk_index=1, citation_label="Dieu 10", article_number="10", content="Noi dung Dieu 10")
    db.add_all([document, article_chunk])
    db.commit()

    def fake_search_chunks(_db, query: str, limit: int, preferred_terms: list[str] | None = None):
        return [(document, article_chunk, 95)]

    monkeypatch.setattr("src.services.document_benchmark_service.knowledge_service.search_chunks", fake_search_chunks)

    benchmark = document_benchmark_service.benchmark_document(db, document.id)

    assert benchmark["document_id"] == document.id
    assert benchmark["overall_score"] > 0.7
    assert any(item["name"] == "metadata_completeness" for item in benchmark["dimensions"])
    assert any(check["passed"] is True for check in benchmark["retrieval_checks"])

    db.close()


def test_ingest_document_uses_ocr_when_pdf_text_layer_is_empty(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "scan.pdf"
    document_path.write_bytes(b"%PDF-1.4\n%%EOF")
    document = make_document(id=21, title="Ban scan", source_type="pdf", storage_path=str(document_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr("src.services.knowledge_service.KnowledgeService._extract_segments", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "src.services.knowledge_service.ocr_service.diagnose_pdf",
        lambda *_args, **_kwargs: OcrDiagnosticResult(
            available=True,
            engine="tesseract",
            page_results=[OcrPageResult(page=1, text="Dieu 1 Noi dung OCR", average_confidence=91.2)],
        ),
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    ingested_document, extracted_characters, chunk_count = search_law_module.knowledge_service.ingest_document(db, document.id)

    assert extracted_characters > 0
    assert chunk_count >= 1
    assert ingested_document.metadata_review_status == "pending_review"
    assert ingested_document.metadata_review_notes is not None
    assert "OCR extraction was used" in ingested_document.metadata_review_notes
    assert ingested_document.ocr_quality_label in {"ocr_high", "ocr_medium", "ocr_low"}

    db.close()


def test_postprocess_legal_ocr_text_restores_article_clause_point_structure() -> None:
    processed = search_law_module.knowledge_service.postprocess_legal_ocr_text(
        "DIEU 1 Pham vi dieu chinh Khoan 1 Noi dung khoan mot Diem a Noi dung diem a Diem b Noi dung diem b DIEU 2 Dieu khoan thi hanh"
    )

    lines = processed.splitlines()

    assert lines[0] == "Điều 1. Phạm vi điều chỉnh"
    assert "1. Noi dung khoan mot" in lines
    assert "a) Noi dung diem a" in lines
    assert "b) Noi dung diem b" in lines
    assert lines[-1] == "Điều 2. Điều khoản thi hành"


def test_postprocess_legal_ocr_text_corrects_common_ocr_spelling_confusions() -> None:
    processed = search_law_module.knowledge_service.postprocess_legal_ocr_text(
        "D1EU 1 PHAM V1 D1EU CH1NH KH0AN 1 N01 DUNG D1EM a N01 DUNG D1EM a"
    )

    lines = processed.splitlines()

    assert lines[0] == "Điều 1. Phạm vi điều chỉnh"
    assert "1. NOI DUNG" in lines
    assert "a) NOI DUNG DIEM a" in lines


def test_postprocess_legal_ocr_text_merges_broken_heading_titles_and_wrapped_lines() -> None:
    processed = search_law_module.knowledge_service.postprocess_legal_ocr_text(
        "CHUONG II QUY DINH CHUNG DIEU 1 Pham vi dieu chinh To chuc, ca nhan nuoc ngoai duoc xet cap phep trong truong hop dac biet khi co du dieu kien"
    )

    lines = processed.splitlines()

    assert lines[0] == "Chương II QUY ĐỊNH CHUNG"
    assert lines[1] == "Điều 1. Phạm vi điều chỉnh"
    assert lines[2] == "To chuc, ca nhan nuoc ngoai duoc xet cap phep trong truong hop dac biet khi co du dieu kien"


def test_postprocess_legal_ocr_text_restores_common_legal_vietnamese_phrases() -> None:
    processed = search_law_module.knowledge_service.postprocess_legal_ocr_text(
        "CHINH PHU CONG HOA XA HOI CHU NGHIA VIET NAM Doc lap Tu do Hanh phuc NGHI DINH SUA DOI BO SUNG MOT SO DIEU CUA NGHI DINH SO 103/2024/ND-CP QUY DINH VE TIEN SU DUNG DAT TIEN THUE DAT CAN CU LUAT DAT DAI SO 31/2024/QH15"
    )

    assert "CHÍNH PHỦ" in processed
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in processed
    assert "Độc lập - Tự do - Hạnh phúc" in processed
    assert "NGHỊ ĐỊNH" in processed
    assert "sua doi bo sung mot so dieu" in legal_metadata_parser_service.normalize_search_text(processed)
    assert "quy dinh ve tien su dung dat tien thue dat" in legal_metadata_parser_service.normalize_search_text(processed)
    assert "Căn cứ Luật Đất đai số 31/2024/QH15" in processed


def test_preview_legal_ocr_correction_returns_review_suggestions() -> None:
    preview = search_law_module.knowledge_service.preview_legal_ocr_correction(
        "D1EU 1 PHAM V1 D1EU CH1NH KH0AN 1 N01 DUNG"
    )

    assert preview["corrected_text"].splitlines()[0] == "Điều 1. Phạm vi điều chỉnh"
    assert preview["review_required"] is True
    assert preview["changed_token_count"] >= 2
    assert any(item["reason"] in {"ocr_confusable_character", "legal_heading_accent"} for item in preview["suggestions"])


def test_upload_preview_keeps_pdf_text_layer_without_legal_ocr_postprocessing(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "text-layer.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "CHUONG II QUY DINH CHUNG DIEU 1 Pham vi dieu chinh To chuc, ca nhan nuoc ngoai duoc xet cap phep",
        ],
    )

    extracted, ocr_applied, ocr_preview = __import__("src.api.admin_router", fromlist=["_extract_full_text"])._extract_full_text(pdf_path, "pdf")

    assert extracted == "CHUONG II QUY DINH CHUNG DIEU 1 Pham vi dieu chinh To chuc, ca nhan nuoc ngoai duoc xet cap phep"
    assert ocr_applied is False
    assert ocr_preview is None


def test_ingest_document_uses_reviewer_edited_text_before_chunking(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "land-rights.txt"
    document_path.write_text("Ban goc khong dung", encoding="utf-8")
    document = make_document(
        id=22,
        title="Luat Dat dai",
        source_type="txt",
        storage_path=str(document_path),
    )
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    ingested_document, extracted_characters, chunk_count = search_law_module.knowledge_service.ingest_document(
        db,
        document.id,
        extracted_text_override="Dieu 1. To chuc kinh te co von dau tu nuoc ngoai duoc xem xet quyen su dung dat theo dieu kien cua luat nay.",
    )

    chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).one()

    assert extracted_characters > 0
    assert chunk_count == 1
    assert "quyen su dung dat" in chunk.content.lower()
    assert ingested_document.metadata_review_status == "reviewed"
    assert ingested_document.metadata_review_notes is not None
    assert "reviewer-edited extracted text" in ingested_document.metadata_review_notes

    db.close()


def test_ingest_document_infers_metadata_locally(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "291_2025_ND-CP_679921.docx"
    document_path.write_text("placeholder", encoding="utf-8")
    document = make_document(
        id=24,
        title="291 2025 ND CP 679921 [20260326_DD]",
        file_name="291_2025_ND-CP_679921.docx",
        source_type="docx",
        storage_path=str(document_path),
        document_code=None,
        document_type=None,
        issuing_authority=None,
        authority_level=None,
        signed_date=None,
    )
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "CHINH PHU",
            "NGHI DINH",
            "So: 291/2025/ND-CP",
            "Ha Noi, ngay 31 thang 12 nam 2025",
            "QUY DINH CHI TIET VE DAT DAI",
            "Dieu 1. Pham vi dieu chinh",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    ingested_document, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)

    assert ingested_document.title == "Nghi dinh quy dinh chi tiet ve dat dai"
    assert ingested_document.document_code == "291/2025/ND-CP"
    assert ingested_document.document_type == "nghi-dinh"
    assert ingested_document.issuing_authority == "Chính phủ"
    assert ingested_document.authority_level == "chinh-phu"
    assert ingested_document.signed_date == date(2025, 12, 31)
    assert ingested_document.ocr_quality_label == "direct_text_high"
    assert ingested_document.ocr_quality_score is not None and float(ingested_document.ocr_quality_score) >= 65

    db.close()


def test_direct_text_quality_reflects_metadata_completeness(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "raw.docx"
    document_path.write_text("placeholder", encoding="utf-8")

    strong = make_document(
        id=25,
        title="Nghi dinh dat dai",
        file_name="291_2025_ND-CP_679921.docx",
        source_type="docx",
        storage_path=str(document_path),
        document_code="291/2025/ND-CP",
        document_type="nghi-dinh",
        issuing_authority="Chính phủ",
        authority_level="chinh-phu",
        signed_date=date(2025, 12, 31),
    )
    weak = make_document(
        id=26,
        title="Tap tin thieu metadata",
        file_name="raw.docx",
        source_type="docx",
        storage_path=str(document_path),
        document_code=None,
        document_type=None,
        issuing_authority=None,
        authority_level=None,
        signed_date=None,
    )
    db.add_all([strong, weak])
    db.commit()

    segments = [
        "CHINH PHU",
        "NGHI DINH",
        "So: 291/2025/ND-CP",
        "Dieu 1. Quy dinh chi tiet ve dat dai",
        "1. Noi dung khoan mot",
        "a) Noi dung diem a",
    ]
    chunk_payloads = search_law_module.knowledge_service._build_chunk_payloads(segments)

    strong_score, strong_label = search_law_module.knowledge_service._derive_ocr_quality(
        document=strong,
        segments=segments,
        chunk_payloads=chunk_payloads,
        ocr_average_confidence=None,
        ocr_used=False,
    )
    weak_score, weak_label = search_law_module.knowledge_service._derive_ocr_quality(
        document=weak,
        segments=segments,
        chunk_payloads=chunk_payloads,
        ocr_average_confidence=None,
        ocr_used=False,
    )

    assert strong_label == "direct_text_high"
    assert weak_label in {"direct_text_medium", "direct_text_low"}
    assert strong_score is not None and weak_score is not None and strong_score > weak_score

    db.close()


def test_ingest_document_replaces_existing_chunks_after_clearing_vectors_and_citation_links(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "source.txt"
    document_path.write_text("Du lieu cu", encoding="utf-8")
    document = make_document(id=23, title="Van ban cap nhat", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.flush()

    old_chunk = make_chunk(id=2301, document_id=document.id, chunk_index=1, citation_label="Dieu 1", content="Noi dung cu")
    db.add(old_chunk)
    db.flush()
    old_chunk_id = old_chunk.id
    db.add(
        DocumentChunkVector(
            chunk_id=old_chunk_id,
            provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            embedding_status="indexed",
            embedding_json="[0.1, 0.2]",
        )
    )
    db.add(
        Citation(
            document_id=document.id,
            chunk_id=old_chunk_id,
            citation_type="legal_basis",
            document_title=document.title,
            citation_label=old_chunk.citation_label,
            hierarchy_path=old_chunk.hierarchy_path,
            excerpt=old_chunk.content,
        )
    )
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: ["Dieu 2. Noi dung cap nhat moi"],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    _, _, chunk_count = search_law_module.knowledge_service.ingest_document(db, document.id)

    remaining_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    remaining_vectors = db.query(DocumentChunkVector).all()
    citation = db.query(Citation).filter(Citation.document_id == document.id).one()

    assert chunk_count >= 1
    assert len(remaining_chunks) >= 1
    assert all(chunk.id != old_chunk_id for chunk in remaining_chunks)
    assert remaining_vectors == []
    assert citation.chunk_id is None

    db.close()


def test_diagnose_document_reports_ocr_availability_for_image_only_pdf(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "image-only.pdf"
    document_path.write_bytes(b"%PDF-1.4\n%%EOF")
    document = make_document(id=22, title="PDF scan", source_type="pdf", storage_path=str(document_path))
    db.add(document)
    db.commit()

    class FakePage:
        def extract_text(self) -> str:
            return ""

    class FakeReader:
        pages = [FakePage(), FakePage()]

        def __init__(self, *_args, **_kwargs) -> None:
            pass

    monkeypatch.setattr("src.services.knowledge_service.PdfReader", FakeReader)
    monkeypatch.setattr(
        "src.services.knowledge_service.ocr_service.diagnose_pdf",
        lambda *_args, **_kwargs: OcrDiagnosticResult(
            available=True,
            engine="tesseract",
            page_results=[OcrPageResult(page=1, text="Trang 1", average_confidence=88.5)],
        ),
    )

    diagnostics = search_law_module.knowledge_service.diagnose_document(db, document.id)

    assert diagnostics["is_extractable"] is False
    assert diagnostics["ocr_available"] is True
    assert diagnostics["ocr_recommended"] is True
    assert diagnostics["ocr_engine"] == "tesseract"
    assert diagnostics["ocr_average_confidence"] == 88.5
    assert diagnostics["ocr_sample_pages"][0]["page"] == 1

    db.close()


def test_legal_provision_parser_extracts_article_clause_and_point_hierarchy() -> None:
    text = """
    CHƯƠNG I
    QUY ĐỊNH CHUNG
    Điều 5. Quyền và nghĩa vụ
    1. Cá nhân có quyền sử dụng đất theo quy định của pháp luật.
    a) Được cấp Giấy chứng nhận quyền sử dụng đất.
    b) Được thực hiện giao dịch theo quy định.
    2. Nhà nước thu hồi đất trong trường hợp luật định.
    """.strip()

    provisions = legal_provision_parser_service.parse_text(text)

    assert len(provisions) == 5
    assert [item.provision_level for item in provisions] == ["article", "clause", "point", "point", "clause"]

    article = provisions[0]
    clause = provisions[1]
    point_a = provisions[2]
    point_b = provisions[3]
    clause_two = provisions[4]

    assert article.article_number == "5"
    assert article.parent_temp_id is None
    assert "Quyền và nghĩa vụ".lower() in (article.heading or "").lower()
    assert clause.parent_temp_id == article.temp_id
    assert clause.clause_number == "1"
    assert point_a.parent_temp_id == clause.temp_id
    assert point_a.point_code == "a"
    assert "Giấy chứng nhận" in point_a.content
    assert point_b.point_code == "b"
    assert point_b.sort_key == "005.001.002"
    assert clause_two.clause_number == "2"


def test_legal_provision_parser_builds_document_payloads_with_parent_ids() -> None:
    text = """
    Điều 12. Hỗ trợ
    1. Hộ gia đình được hỗ trợ.
    a) Hỗ trợ đào tạo nghề.
    """.strip()

    payloads = legal_provision_parser_service.build_document_payloads(document_id=99, text=text)

    assert len(payloads) == 3
    assert payloads[0]["document_id"] == 99
    assert payloads[0]["parent_provision_id"] is None
    assert payloads[1]["parent_provision_id"] == 1
    assert payloads[2]["parent_provision_id"] == 2
    assert payloads[2]["citation_label"] == "Điều 12 Khoản 1 Điểm a"


def test_legal_provision_parser_keeps_inline_article_content() -> None:
    drafts = legal_provision_parser_service.parse_text("Điều 7. Căn cứ khoản 1 Điều 2 của Nghị định này.")

    assert len(drafts) == 1
    assert drafts[0].provision_level == "article"
    assert "Căn cứ khoản 1 Điều 2" in drafts[0].content


def test_legal_provision_parser_normalizes_missing_heading_prefixes() -> None:
    drafts = legal_provision_parser_service.parse_text(
        "\n".join(
            [
                "Chuong I",
                "NHUNG QUY DINH CHUNG",
                "ieu 1. Pham vi dieu chinh",
                "1. Noi dung khoan mot",
                "iem a Quyen cua nguoi su dung dat",
            ]
        )
    )

    assert len(drafts) == 3
    assert drafts[0].heading == "Điều 1. Pham vi dieu chinh"
    assert drafts[1].citation_label == "Điều 1 Khoản 1"
    assert drafts[2].citation_label == "Điều 1 Khoản 1 Điểm a"


def test_legal_provision_parser_supports_roman_and_outline_structure() -> None:
    drafts = legal_provision_parser_service.parse_text(
        "\n".join(
            [
                "I. NHUNG VAN DE CHUNG",
                "1. Pham vi ap dung",
                "1.1. Doi tuong thu nhat",
                "1.2. Doi tuong thu hai",
                "II. NOI DUNG THUC HIEN",
                "2. Trach nhiem thi hanh",
            ]
        )
    )

    assert [item.provision_level for item in drafts] == ["article", "clause", "clause", "clause", "article", "clause"]
    assert drafts[0].citation_label.startswith("I.")
    assert drafts[1].clause_number == "1"
    assert drafts[2].clause_number == "1.1"
    assert drafts[4].citation_label.startswith("II.")


def test_ingest_document_creates_structured_legal_provisions(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "structured.txt"
    document_path.write_text("Du lieu provision", encoding="utf-8")
    document = make_document(id=31, title="Van ban co cau truc", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "Điều 1. Quy định chung",
            "1. Cá nhân có quyền sử dụng đất.",
            "a) Được cấp Giấy chứng nhận.",
            "2. Nhà nước thu hồi đất theo luật.",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    _, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)

    provisions = db.query(LegalProvision).filter(LegalProvision.document_id == document.id).order_by(LegalProvision.sort_key.asc()).all()

    assert len(provisions) == 4
    assert [item.provision_level for item in provisions] == ["article", "clause", "point", "clause"]
    assert provisions[1].parent_provision_id == provisions[0].id
    assert provisions[2].parent_provision_id == provisions[1].id

    db.close()


def test_ingest_document_replaces_existing_legal_provisions(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "replace-provisions.txt"
    document_path.write_text("Du lieu cu", encoding="utf-8")
    document = make_document(id=32, title="Van ban thay provision", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.flush()
    db.add(
        LegalProvision(
            document_id=document.id,
            parent_provision_id=None,
            provision_level="article",
            article_number="99",
            clause_number=None,
            point_code=None,
            heading="Điều 99. Nội dung cũ",
            content="Noi dung cu",
            citation_label="Điều 99",
            sort_key="099.000.000",
            legal_status="active",
            metadata_json="{}",
            is_active=True,
        )
    )
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "Điều 2. Nội dung mới",
            "1. Khoản mới.",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    _, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)

    provisions = db.query(LegalProvision).filter(LegalProvision.document_id == document.id).order_by(LegalProvision.sort_key.asc()).all()

    assert len(provisions) == 2
    assert provisions[0].article_number == "2"
    assert all(item.article_number != "99" for item in provisions)

    db.close()


def test_list_provisions_returns_sorted_document_provisions() -> None:
    db = create_test_session()
    document = make_document(id=41, title="Van ban danh sach provision")
    db.add(document)
    db.flush()
    db.add_all([
        LegalProvision(
            document_id=document.id,
            parent_provision_id=None,
            provision_level="clause",
            article_number="3",
            clause_number="2",
            point_code=None,
            heading="2. Khoản hai",
            content="Khoan hai",
            citation_label="Điều 3 Khoản 2",
            sort_key="003.002.000",
            legal_status="active",
            metadata_json="{}",
            is_active=True,
        ),
        LegalProvision(
            document_id=document.id,
            parent_provision_id=None,
            provision_level="article",
            article_number="3",
            clause_number=None,
            point_code=None,
            heading="Điều 3. Điều ba",
            content="Dieu ba",
            citation_label="Điều 3",
            sort_key="003.000.000",
            legal_status="active",
            metadata_json="{}",
            is_active=True,
        ),
    ])
    db.commit()

    provisions = search_law_module.knowledge_service.list_provisions(db, document.id)

    assert [item.sort_key for item in provisions] == ["003.000.000", "003.002.000"]

    db.close()


def test_ingest_document_creates_provision_relations_from_internal_citations(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "provision-relations.txt"
    document_path.write_text("Du lieu quan he provision", encoding="utf-8")
    document = make_document(id=42, title="Van ban quan he provision", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "Điều 2. Nguyên tắc xử lý hồ sơ.",
            "1. Hồ sơ phải đầy đủ.",
            "Điều 3. Căn cứ khoản 1 Điều 2 của Nghị định này để giải quyết.",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    _, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)

    relations = (
        db.query(ProvisionRelation)
        .filter(ProvisionRelation.source_document_id == document.id)
        .order_by(ProvisionRelation.id.asc())
        .all()
    )

    assert len(relations) == 1
    assert relations[0].relation_type == "LEGAL_BASIS_PROVISION"
    assert relations[0].relation_label == "Căn cứ điều khoản"
    assert relations[0].source_excerpt is not None and "Điều 3" in relations[0].source_excerpt
    assert relations[0].target_excerpt is not None and "Hồ sơ phải đầy đủ" in relations[0].target_excerpt

    db.close()


def test_provision_relation_service_extracts_relations_from_missing_prefix_citations() -> None:
    db = create_test_session()
    document = make_document(id=46, title="Van ban loi prefix")
    db.add(document)
    db.flush()
    article = LegalProvision(
        document_id=document.id,
        parent_provision_id=None,
        provision_level="article",
        article_number="8",
        clause_number=None,
        point_code=None,
        heading="Điều 8. Quy định chung",
        content="Noi dung dieu 8",
        citation_label="Điều 8",
        sort_key="008.000.000",
        legal_status="active",
        metadata_json="{}",
        is_active=True,
    )
    db.add(article)
    db.flush()
    clause = LegalProvision(
        document_id=document.id,
        parent_provision_id=article.id,
        provision_level="clause",
        article_number="8",
        clause_number="1",
        point_code=None,
        heading="1. Khoản một",
        content="Noi dung khoan mot",
        citation_label="Điều 8 Khoản 1",
        sort_key="008.001.000",
        legal_status="active",
        metadata_json="{}",
        is_active=True,
    )
    db.add(clause)
    db.flush()
    point = LegalProvision(
        document_id=document.id,
        parent_provision_id=clause.id,
        provision_level="point",
        article_number="8",
        clause_number="1",
        point_code="a",
        heading="a) Điểm a",
        content="Noi dung diem a",
        citation_label="Điều 8 Khoản 1 Điểm a",
        sort_key="008.001.001",
        legal_status="active",
        metadata_json="{}",
        is_active=True,
    )
    source = LegalProvision(
        document_id=document.id,
        parent_provision_id=None,
        provision_level="article",
        article_number="9",
        clause_number=None,
        point_code=None,
        heading="Điều 9. Dẫn chiếu",
        content="Can cu iem a khoan 1 ieu 8 cua van ban nay de thuc hien.",
        citation_label="Điều 9",
        sort_key="009.000.000",
        legal_status="active",
        metadata_json="{}",
        is_active=True,
    )
    db.add_all([point, source])
    db.commit()

    summary = provision_relation_service.sync_document_relations(db, document.id)
    relations = db.query(ProvisionRelation).filter(ProvisionRelation.source_document_id == document.id).all()

    assert summary.created_relations == 1
    assert relations[0].target_provision_id == point.id
    assert relations[0].relation_type == "LEGAL_BASIS_PROVISION"

    db.close()


def test_ingest_document_creates_provisions_from_outline_structure_without_dieu(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "outline-structure.txt"
    document_path.write_text("Du lieu outline", encoding="utf-8")
    document = make_document(id=47, title="Van ban outline", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "I. NHUNG VAN DE CHUNG",
            "1. Pham vi ap dung",
            "1.1. Doi tuong thu nhat",
            "II. NOI DUNG THUC HIEN",
            "2. Trach nhiem thi hanh",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.services.knowledge_service.provision_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    _, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)
    provisions = db.query(LegalProvision).filter(LegalProvision.document_id == document.id).order_by(LegalProvision.sort_key.asc()).all()

    assert len(provisions) == 5
    assert provisions[0].citation_label.startswith("I.")
    assert provisions[1].clause_number == "1"
    assert provisions[2].clause_number == "1.1"
    assert provisions[3].citation_label.startswith("II.")

    db.close()


def test_refresh_document_metadata_and_relations_resyncs_provisions_and_provision_relations(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    source_path = tmp_path / "refresh-provisions.txt"
    source_path.write_text("Noi dung can refresh", encoding="utf-8")
    document = make_document(id=43, title="Van ban refresh provision", source_type="txt", storage_path=str(source_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "Điều 5. Quy định chung.",
            "1. Áp dụng theo Điều 5 của văn bản này.",
        ],
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)

    refreshed = search_law_module.knowledge_service.refresh_document_metadata_and_relations(db, document.id)
    provisions = db.query(LegalProvision).filter(LegalProvision.document_id == document.id).order_by(LegalProvision.sort_key.asc()).all()
    relations = db.query(ProvisionRelation).filter(ProvisionRelation.source_document_id == document.id).all()

    assert refreshed.id == document.id
    assert len(provisions) == 2
    assert provisions[0].citation_label == "Điều 5"
    assert len(relations) == 1
    assert relations[0].relation_type == "CITES_PROVISION"

    db.close()


def test_ingest_document_uses_ai_fallback_parser_when_deterministic_structure_fails(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "fallback-structure.txt"
    document_path.write_text("Du lieu fallback", encoding="utf-8")
    document = make_document(id=44, title="Van ban can AI fallback", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: [
            "Quy dinh ve ho tro doi voi ho gia dinh bi thu hoi dat.",
            "Nguoi su dung dat duoc cap giay chung nhan theo quy dinh cua phap luat.",
        ],
    )
    monkeypatch.setattr(
        "src.services.knowledge_service.embedding_service.index_document_chunks",
        lambda *_args, **_kwargs: SimpleNamespace(status="disabled", failed_count=0),
    )
    monkeypatch.setattr("src.services.knowledge_service.document_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.services.knowledge_service.provision_relation_service.sync_document_relations", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.services.knowledge_service.settings.legal_structure_ai_fallback_enabled", True)
    monkeypatch.setattr("src.services.knowledge_service.settings.legal_structure_ai_fallback_threshold", 60.0)
    monkeypatch.setattr("src.services.legal_provision_ai_fallback_service.settings.legal_structure_ai_fallback_enabled", True)
    monkeypatch.setattr("src.services.legal_provision_ai_fallback_service.legal_provision_ai_fallback_service.is_enabled", lambda: True)
    monkeypatch.setattr(
        "src.services.legal_provision_ai_fallback_service.legal_provision_ai_fallback_service.parse_text",
        lambda **_kwargs: [
            {
                "document_id": document.id,
                "parent_provision_id": None,
                "provision_level": "article",
                "article_number": "1",
                "clause_number": None,
                "point_code": None,
                "heading": "Điều 1. Quy định hỗ trợ",
                "content": "Quy định về hỗ trợ đối với hộ gia đình bị thu hồi đất.",
                "citation_label": "Điều 1",
                "sort_key": "001.000.000",
                "metadata_json": "{\"parser_source\":\"ai_fallback\",\"requires_review\":true}",
            },
            {
                "document_id": document.id,
                "parent_provision_id": 1,
                "provision_level": "clause",
                "article_number": "1",
                "clause_number": "1",
                "point_code": None,
                "heading": "1. Người sử dụng đất được cấp giấy chứng nhận",
                "content": "Người sử dụng đất được cấp giấy chứng nhận theo quy định của pháp luật.",
                "citation_label": "Điều 1 Khoản 1",
                "sort_key": "001.001.000",
                "metadata_json": "{\"parser_source\":\"ai_fallback\",\"requires_review\":true}",
            },
        ],
    )

    ingested_document, _, _ = search_law_module.knowledge_service.ingest_document(db, document.id)
    provisions = db.query(LegalProvision).filter(LegalProvision.document_id == document.id).order_by(LegalProvision.sort_key.asc()).all()

    assert len(provisions) == 2
    assert provisions[0].article_number == "1"
    assert provisions[1].parent_provision_id == provisions[0].id
    assert ingested_document.metadata_review_status == "pending_review"
    assert ingested_document.metadata_review_notes is not None and "AI fallback parser" in ingested_document.metadata_review_notes

    db.close()


def test_diagnose_document_reports_ai_fallback_parser_status(monkeypatch, tmp_path: Path) -> None:
    db = create_test_session()
    document_path = tmp_path / "fallback-diagnostics.txt"
    document_path.write_text("Du lieu diagnostics", encoding="utf-8")
    document = make_document(id=45, title="Van ban diagnostics fallback", source_type="txt", storage_path=str(document_path))
    db.add(document)
    db.flush()
    db.add(
        LegalProvision(
            document_id=document.id,
            parent_provision_id=None,
            provision_level="article",
            article_number="7",
            clause_number=None,
            point_code=None,
            heading="Điều 7. Quy định chuyển tiếp",
            content="Quy định chuyển tiếp.",
            citation_label="Điều 7",
            sort_key="007.000.000",
            legal_status="active",
            metadata_json='{"parser_source":"ai_fallback","requires_review":true}',
            is_active=True,
        )
    )
    db.commit()

    monkeypatch.setattr(
        "src.services.knowledge_service.KnowledgeService._extract_segments",
        lambda *_args, **_kwargs: ["Van ban OCR xau khong con mau dieu khoan ro rang."],
    )

    diagnostics = search_law_module.knowledge_service.diagnose_document(db, document.id)

    assert diagnostics["parser_status"] == "parsed_with_ai_fallback"
    assert any("AI fallback parser" in note for note in diagnostics["parser_notes"])
    assert diagnostics["parser_provision_count"] == 1

    db.close()
