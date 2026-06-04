from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class BenchmarkHistoryService:
    def __init__(self, report_dir: Path | None = None) -> None:
        self.report_dir = report_dir or Path(__file__).resolve().parents[2] / "benchmark_reports"

    def record_report(
        self,
        report: dict[str, Any],
        *,
        cases_path: str,
        schema_summary: dict[str, Any] | None = None,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        report_dir = output_dir or self.report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        run_id = f"{created_at.replace(':', '').replace('+', 'Z')}_{uuid4().hex[:8]}"
        payload = {
            "run_id": run_id,
            "created_at": created_at,
            "cases_path": cases_path,
            "schema_summary": schema_summary or {},
            "summary": self._summarize_report(report),
            "report": report,
        }
        path = report_dir / f"benchmark_run_{run_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["source_path"] = str(path)
        return payload

    def list_runs(self, *, limit: int = 20, report_dir: Path | None = None) -> list[dict[str, Any]]:
        target_dir = report_dir or self.report_dir
        if not target_dir.exists():
            return []
        runs: list[dict[str, Any]] = []
        for path in sorted(target_dir.glob("benchmark_run_*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            runs.append(
                {
                    "run_id": str(payload.get("run_id") or path.stem),
                    "created_at": str(payload.get("created_at") or ""),
                    "cases_path": str(payload.get("cases_path") or ""),
                    "source_path": str(path),
                    **self._summarize_report(dict(payload.get("report") or payload.get("summary") or {})),
                }
            )
            if len(runs) >= limit:
                break
        return runs

    def list_failure_items(self, *, limit: int = 20, report_dir: Path | None = None) -> list[dict[str, Any]]:
        target_dir = report_dir or self.report_dir
        items: list[dict[str, Any]] = []
        for run in self._load_runs(target_dir):
            report = dict(run.get("report") or {})
            for result in report.get("results") or []:
                if not isinstance(result, dict) or result.get("status") != "fail":
                    continue
                failed_checks = [
                    str(check.get("name"))
                    for check in result.get("checks") or []
                    if isinstance(check, dict) and check.get("passed") is False
                ]
                items.append(
                    {
                        "queue": "benchmark_failures",
                        "source_type": "benchmark_case",
                        "source_id": str(result.get("id") or ""),
                        "title": f"Benchmark case {result.get('id')}",
                        "status": "failed",
                        "severity": "high",
                        "detail": ", ".join(failed_checks) if failed_checks else "Runtime benchmark case failed.",
                        "action": "Inspect benchmark report and create retrieval/validation backlog item.",
                        "created_at": str(run.get("created_at") or ""),
                        "source_path": str(run.get("source_path") or ""),
                    }
                )
                if len(items) >= limit:
                    return items
        return items

    def _load_runs(self, report_dir: Path) -> list[dict[str, Any]]:
        if not report_dir.exists():
            return []
        runs: list[dict[str, Any]] = []
        for path in sorted(report_dir.glob("benchmark_run_*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payload["source_path"] = str(path)
            runs.append(payload)
        return runs

    def _summarize_report(self, report: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": str(report.get("status") or "unknown"),
            "total": int(report.get("total") or 0),
            "passed": int(report.get("passed") or 0),
            "failed": int(report.get("failed") or 0),
            "skipped": int(report.get("skipped") or 0),
            "pass_rate": float(report.get("pass_rate") or 0.0),
            "quick": bool(report.get("quick") or False),
            "allow_unreviewed": bool(report.get("allow_unreviewed") or False),
        }


benchmark_history_service = BenchmarkHistoryService()
