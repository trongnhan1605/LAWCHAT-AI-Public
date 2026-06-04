from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from src.core.database import SessionLocal
from src.services.graph_service import graph_service
from src.services.neo4j_graph_service import neo4j_graph_service


DOCUMENT_IDS = [10, 24, 51]
DEPTHS = [1, 2]
RUNS_PER_CASE = 3


def benchmark_case(db, document_id: int, depth: int, backend: str) -> dict[str, object]:
    service = neo4j_graph_service if backend == "neo4j" else graph_service
    timings_ms: list[float] = []
    payload = None
    for _ in range(RUNS_PER_CASE):
        started = time.perf_counter()
        payload = service.get_document_graph(db, document_id, depth=depth)
        timings_ms.append((time.perf_counter() - started) * 1000)

    return {
        "backend": backend,
        "document_id": document_id,
        "depth": depth,
        "runs": RUNS_PER_CASE,
        "avg_ms": round(statistics.mean(timings_ms), 2),
        "min_ms": round(min(timings_ms), 2),
        "max_ms": round(max(timings_ms), 2),
        "node_count": len(payload["nodes"]) if payload else 0,
        "edge_count": len(payload["edges"]) if payload else 0,
    }


def main() -> None:
    db = SessionLocal()
    try:
        results: list[dict[str, object]] = []
        for document_id in DOCUMENT_IDS:
            for depth in DEPTHS:
                results.append(benchmark_case(db, document_id, depth, "relational"))
                results.append(benchmark_case(db, document_id, depth, "neo4j"))

        report = {
            "document_ids": DOCUMENT_IDS,
            "depths": DEPTHS,
            "runs_per_case": RUNS_PER_CASE,
            "results": results,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
