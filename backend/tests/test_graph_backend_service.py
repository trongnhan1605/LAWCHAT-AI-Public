from src.services.graph_backend_service import graph_backend_service


def test_graph_backend_overview_defaults_to_relational() -> None:
    payload = graph_backend_service.backend_overview()

    assert payload["default_backend"] in {"relational", "neo4j"}
    assert payload["relational"]["provider"] == "relational"
    assert payload["neo4j"]["provider"] == "neo4j"
    assert payload["relational"]["available"] is True
