import importlib
from types import SimpleNamespace

from src.retrieval.legal_retrieval import legal_retrieval_service


search_law_module = importlib.import_module("src.tools.search_law")


def test_legal_retrieval_service_delegates_chunk_search(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_search_chunks(db, query: str, limit: int, preferred_terms: list[str] | None = None, legal_domain: str | None = None, allow_unreviewed: bool = True):
        captured["db"] = db
        captured["query"] = query
        captured["limit"] = limit
        captured["preferred_terms"] = preferred_terms
        captured["legal_domain"] = legal_domain
        captured["allow_unreviewed"] = allow_unreviewed
        return []

    monkeypatch.setattr("src.retrieval.legal_retrieval.knowledge_service.search_chunks", fake_search_chunks)

    fake_db = object()
    result = legal_retrieval_service.search_chunks(fake_db, "dat dai", limit=7, preferred_terms=["so do"])

    assert result == []
    assert captured == {"db": fake_db, "query": "dat dai", "limit": 7, "preferred_terms": ["so do"], "legal_domain": None, "allow_unreviewed": False}


def test_search_law_uses_retrieval_boundary(monkeypatch) -> None:
    document = SimpleNamespace(id=1, title="Luat Dat dai", legal_status="active", source_reference="https://example.test")
    chunk = SimpleNamespace(id=2, citation_label="Dieu 1", hierarchy_path="Chuong I > Dieu 1", content="Noi dung phap ly")

    monkeypatch.setattr(search_law_module.legal_retrieval_service, "search_chunks", lambda *_args, **_kwargs: [(document, chunk, 91)])

    result = search_law_module.search_law(object(), "query")

    assert len(result) == 1
    assert result[0].document_id == 1
    assert result[0].chunk_id == 2
    assert result[0].score == 91
