from src.services.neo4j_projection_service import Neo4jProjectionSyncSummary


def test_neo4j_projection_sync_summary_shape() -> None:
    summary = Neo4jProjectionSyncSummary(
        mode="full",
        document_id=None,
        document_count=10,
        provision_count=30,
        document_relation_count=12,
        provision_relation_count=18,
    )

    assert summary.mode == "full"
    assert summary.document_count == 10
    assert summary.provision_count == 30
