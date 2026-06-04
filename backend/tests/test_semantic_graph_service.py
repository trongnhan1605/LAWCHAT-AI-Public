from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401
from src.core.database import Base
from src.services.bootstrap_service import ensure_seed_data
from src.services.legal_semantic_graph_service import legal_semantic_graph_service


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = session_factory()
    ensure_seed_data(session)
    return session


def test_match_concepts_maps_query_to_seeded_concepts() -> None:
    db = create_test_session()

    result = legal_semantic_graph_service.match_concepts(
        db,
        "Nhà đầu tư nước ngoài thành lập doanh nghiệp tại Việt Nam có được nhận chuyển nhượng quyền sử dụng đất không?",
    )

    matched_slugs = [item["concept"].slug for item in result]
    assert "nha-dau-tu-nuoc-ngoai" in matched_slugs
    assert "thanh-lap-doanh-nghiep-tai-viet-nam" in matched_slugs
    assert "quyen-su-dung-dat" in matched_slugs


def test_explain_query_returns_multi_hop_semantic_edges() -> None:
    db = create_test_session()

    payload = legal_semantic_graph_service.explain_query(
        db,
        "Nhà đầu tư nước ngoài thành lập doanh nghiệp tại Việt Nam có được nhận chuyển nhượng quyền sử dụng đất không?",
        depth=3,
    )

    edge_types = {edge["edge_type"] for edge in payload["edges"]}
    assert "REQUIRES_PROCEDURE" in edge_types
    assert "CREATES_ENTITY" in edge_types
    assert "ENABLES_RIGHT" in edge_types

    node_labels = {node["label"] for node in payload["nodes"]}
    assert "Nhà đầu tư nước ngoài" in node_labels
    assert "Doanh nghiệp có vốn đầu tư nước ngoài (FDI)" in node_labels
    assert "Quyền sử dụng đất" in node_labels