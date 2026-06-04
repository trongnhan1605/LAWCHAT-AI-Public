from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.core.config import settings
from src.schemas.admin_schema import (
    GraphBackendBenchmarkPayload,
    GraphBackendInsightsPayload,
    GraphBackendParityPayload,
    GraphBackendRecommendationPayload,
    GraphBackendStatusPayload,
    GraphProjectionSyncPayload,
)
from src.services.graph_backend_service import graph_backend_service
from src.services.graph_service import graph_service
from src.services.neo4j_projection_service import neo4j_projection_service


GRAPH_BACKEND_INSIGHTS_PATH = Path("backend/storage/graph_backend_insights.json")


class AdminGraphOperationsService:
    def backend_status(self) -> GraphBackendStatusPayload:
        return GraphBackendStatusPayload.model_validate(graph_backend_service.backend_overview())

    def sync_projection(self, db: Session, document_id: int | None = None) -> GraphProjectionSyncPayload:
        summary = neo4j_projection_service.sync_all(db) if document_id is None else neo4j_projection_service.sync_document(db, document_id)
        return GraphProjectionSyncPayload.model_validate(
            {
                "mode": summary.mode,
                "document_id": summary.document_id,
                "document_count": summary.document_count,
                "provision_count": summary.provision_count,
                "document_relation_count": summary.document_relation_count,
                "provision_relation_count": summary.provision_relation_count,
            }
        )

    def benchmark_backends(self, db: Session, document_ids: str = "10,24,51", depths: str = "1,2", runs: int = 2) -> GraphBackendBenchmarkPayload:
        parsed_document_ids = self._parse_int_list(document_ids)
        parsed_depths = self._parse_int_list(depths)
        parsed_runs = max(1, min(runs, 5))
        results: list[dict[str, object]] = []

        for document_id in parsed_document_ids:
            for depth in parsed_depths:
                for backend_name, service in (("relational", graph_service), ("neo4j", graph_backend_service)):
                    timings_ms: list[float] = []
                    payload = None
                    original_backend = settings.graph_backend
                    settings.graph_backend = backend_name
                    try:
                        for _ in range(parsed_runs):
                            started = time.perf_counter()
                            payload = service.get_document_graph(db, document_id, depth=depth)
                            timings_ms.append((time.perf_counter() - started) * 1000)
                    finally:
                        settings.graph_backend = original_backend

                    results.append(
                        {
                            "backend": backend_name,
                            "document_id": document_id,
                            "depth": depth,
                            "runs": parsed_runs,
                            "avg_ms": round(sum(timings_ms) / len(timings_ms), 2),
                            "min_ms": round(min(timings_ms), 2),
                            "max_ms": round(max(timings_ms), 2),
                            "node_count": len(payload["nodes"]) if payload else 0,
                            "edge_count": len(payload["edges"]) if payload else 0,
                        }
                    )

        payload = GraphBackendBenchmarkPayload.model_validate({"document_ids": parsed_document_ids, "depths": parsed_depths, "runs_per_case": parsed_runs, "results": results})
        self.persist_insights(benchmark=payload)
        return payload

    def parity_backends(self, db: Session, document_ids: str = "10,24,51", depths: str = "1,2") -> GraphBackendParityPayload:
        parsed_document_ids = self._parse_int_list(document_ids)
        parsed_depths = self._parse_int_list(depths)
        results: list[dict[str, object]] = []

        for document_id in parsed_document_ids:
            for depth in parsed_depths:
                relational_payload = graph_service.get_document_graph(db, document_id, depth=depth)
                original_backend = settings.graph_backend
                try:
                    settings.graph_backend = "neo4j"
                    neo4j_payload = graph_backend_service.get_document_graph(db, document_id, depth=depth)
                finally:
                    settings.graph_backend = original_backend

                relational_edge_keys = {
                    (
                        int(edge["source"]) if isinstance(edge["source"], int | float) else edge["source"],
                        int(edge["target"]) if isinstance(edge["target"], int | float) else edge["target"],
                        str(edge["relation_type"]),
                    )
                    for edge in relational_payload["edges"]
                }
                neo4j_edge_keys = {
                    (
                        int(edge["source"]) if isinstance(edge["source"], int | float) else edge["source"],
                        int(edge["target"]) if isinstance(edge["target"], int | float) else edge["target"],
                        str(edge["relation_type"]),
                    )
                    for edge in neo4j_payload["edges"]
                }
                relational_anchor_map = {str(edge["id"]): (edge.get("target_anchor"), edge.get("target_excerpt")) for edge in relational_payload["edges"]}
                neo4j_anchor_map = {str(edge["id"]): (edge.get("target_anchor"), edge.get("target_excerpt")) for edge in neo4j_payload["edges"]}

                results.append(
                    {
                        "document_id": document_id,
                        "depth": depth,
                        "node_count_relational": len(relational_payload["nodes"]),
                        "node_count_neo4j": len(neo4j_payload["nodes"]),
                        "edge_count_relational": len(relational_payload["edges"]),
                        "edge_count_neo4j": len(neo4j_payload["edges"]),
                        "node_count_match": len(relational_payload["nodes"]) == len(neo4j_payload["nodes"]),
                        "edge_count_match": len(relational_payload["edges"]) == len(neo4j_payload["edges"]),
                        "edge_identity_match": relational_edge_keys == neo4j_edge_keys,
                        "anchor_match": relational_anchor_map == neo4j_anchor_map,
                    }
                )

        payload = GraphBackendParityPayload.model_validate({"document_ids": parsed_document_ids, "depths": parsed_depths, "results": results})
        self.persist_insights(parity=payload)
        return payload

    def load_insights(self) -> GraphBackendInsightsPayload | None:
        if not GRAPH_BACKEND_INSIGHTS_PATH.exists():
            return None
        try:
            raw = json.loads(GRAPH_BACKEND_INSIGHTS_PATH.read_text(encoding="utf-8"))
            return GraphBackendInsightsPayload.model_validate(raw)
        except (OSError, ValueError):
            return None

    def persist_insights(self, *, benchmark: GraphBackendBenchmarkPayload | None = None, parity: GraphBackendParityPayload | None = None) -> None:
        GRAPH_BACKEND_INSIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = self.load_insights()
        merged_benchmark = benchmark or (existing.benchmark if existing else None)
        merged_parity = parity or (existing.parity if existing else None)
        payload = GraphBackendInsightsPayload(
            benchmark=merged_benchmark,
            parity=merged_parity,
            recommendation=self.build_recommendation(merged_benchmark, merged_parity),
            updated_at=datetime.now(timezone.utc),
        )
        GRAPH_BACKEND_INSIGHTS_PATH.write_text(payload.model_dump_json(indent=2), encoding="utf-8")

    def build_recommendation(
        self,
        benchmark: GraphBackendBenchmarkPayload | None,
        parity: GraphBackendParityPayload | None,
    ) -> GraphBackendRecommendationPayload:
        if not benchmark or not benchmark.results or not parity or not parity.results:
            return GraphBackendRecommendationPayload(
                recommended_backend="relational",
                summary="Chưa đủ dữ liệu benchmark/parity để chuyển backend graph runtime.",
                reasons=[
                    "Cần chạy cả benchmark và parity trên cùng tập document/depth.",
                    "Relational vẫn là source of truth cho runtime cho tới khi parity đủ rõ.",
                ],
            )

        relational_runs = [item for item in benchmark.results if item.backend == "relational"]
        neo4j_runs = [item for item in benchmark.results if item.backend == "neo4j"]
        parity_matches = [
            item
            for item in parity.results
            if item.node_count_match and item.edge_count_match and item.edge_identity_match and item.anchor_match
        ]
        parity_total = len(parity.results)
        avg_relational = sum(item.avg_ms for item in relational_runs) / len(relational_runs) if relational_runs else 0.0
        avg_neo4j = sum(item.avg_ms for item in neo4j_runs) / len(neo4j_runs) if neo4j_runs else 0.0
        parity_ok = parity_total > 0 and len(parity_matches) == parity_total

        if parity_ok and avg_relational > 0 and avg_neo4j > avg_relational * 1.5:
            return GraphBackendRecommendationPayload(
                recommended_backend="relational",
                summary="Nên tiếp tục dùng relational cho runtime hiện tại; Neo4j phù hợp cho benchmark, path traversal và mở rộng semantic graph sau này.",
                reasons=[
                    f"Parity đang khớp {len(parity_matches)}/{parity_total} case mẫu.",
                    f"Relational nhanh hơn rõ ràng: trung bình {avg_relational:.2f} ms so với {avg_neo4j:.2f} ms của Neo4j.",
                    "Neo4j hiện phù hợp nhất để demo graph-native query, parity và mở rộng ontology/reasoning graph.",
                ],
            )

        if parity_ok:
            return GraphBackendRecommendationPayload(
                recommended_backend="neo4j",
                summary="Neo4j đã đạt parity và hiệu năng chấp nhận được trên tập test hiện tại; có thể cân nhắc dùng cho document graph/query graph.",
                reasons=[
                    f"Parity đang khớp {len(parity_matches)}/{parity_total} case mẫu.",
                    f"Hiệu năng trung bình: relational {avg_relational:.2f} ms, neo4j {avg_neo4j:.2f} ms.",
                    "Neo4j có lợi thế cho multi-hop traversal, path explanation và semantic graph mở rộng.",
                ],
            )

        return GraphBackendRecommendationPayload(
            recommended_backend="relational",
            summary="Chưa nên chuyển runtime sang Neo4j vì parity chưa đạt hoàn toàn.",
            reasons=[
                f"Parity mới khớp {len(parity_matches)}/{parity_total} case mẫu.",
                f"Hiệu năng trung bình: relational {avg_relational:.2f} ms, neo4j {avg_neo4j:.2f} ms.",
                "Cần tiếp tục chỉnh projection/query để đạt độ đúng thông tin trước khi đổi backend runtime.",
            ],
        )

    def _parse_int_list(self, value: str) -> list[int]:
        return [int(item.strip()) for item in value.split(",") if item.strip()]


admin_graph_operations_service = AdminGraphOperationsService()
