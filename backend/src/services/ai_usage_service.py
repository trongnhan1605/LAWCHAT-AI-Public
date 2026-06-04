from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.core.logging import logger
from src.models.ai_request_usage import AIRequestUsage
from src.models.document import Document


@dataclass(slots=True)
class UsageBreakdown:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    total_tokens: int = 0
    web_search_calls: int = 0
    estimated_cost_usd: Decimal | None = None
    raw_usage_json: str | None = None
    request_identifier: str | None = None


class AIUsageService:
    MODEL_PRICING: dict[str, dict[str, Decimal]] = {
        "gpt-4.1": {
            "input": Decimal("2.00"),
            "cached_input": Decimal("0.50"),
            "output": Decimal("8.00"),
        },
        "gpt-4.1-mini": {
            "input": Decimal("0.40"),
            "cached_input": Decimal("0.10"),
            "output": Decimal("1.60"),
        },
        "gpt-5.4": {
            "input": Decimal("2.50"),
            "cached_input": Decimal("0.25"),
            "output": Decimal("15.00"),
        },
        "gpt-5.4-mini": {
            "input": Decimal("0.60"),
            "cached_input": Decimal("0.10"),
            "output": Decimal("2.40"),
        },
        "gpt-5.4-nano": {
            "input": Decimal("0.15"),
            "cached_input": Decimal("0.03"),
            "output": Decimal("0.60"),
        },
        "text-embedding-3-small": {
            "input": Decimal("0.02"),
            "cached_input": Decimal("0.00"),
            "output": Decimal("0.00"),
        },
    }
    WEB_SEARCH_CALL_PRICE_USD = Decimal("0.01")

    def extract_usage_breakdown(self, payload: dict | None, *, model: str) -> UsageBreakdown:
        if not payload:
            return UsageBreakdown()

        usage = payload.get("usage") or {}
        input_details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        cached_input_tokens = int(input_details.get("cached_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
        web_search_calls = sum(1 for item in payload.get("output") or [] if item.get("type") == "web_search_call")
        raw_usage_json = json.dumps(usage, ensure_ascii=False) if usage else None
        request_identifier = str(payload.get("id") or "").strip() or None

        estimated_cost = self._estimate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            web_search_calls=web_search_calls,
        )
        return UsageBreakdown(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            total_tokens=total_tokens,
            web_search_calls=web_search_calls,
            estimated_cost_usd=estimated_cost,
            raw_usage_json=raw_usage_json,
            request_identifier=request_identifier,
        )

    def log_request(
        self,
        *,
        request_type: str,
        endpoint: str,
        provider: str,
        model: str,
        document_id: int | None = None,
        document_title_snapshot: str | None = None,
        file_name_snapshot: str | None = None,
        storage_path_snapshot: str | None = None,
        chunk_count: int | None = None,
        payload: dict | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        try:
            breakdown = self.extract_usage_breakdown(payload, model=model)
            with SessionLocal() as db:
                row = AIRequestUsage(
                    request_type=request_type,
                    endpoint=endpoint,
                    provider=provider,
                    model=model,
                    request_identifier=breakdown.request_identifier,
                    document_id=document_id,
                    document_title_snapshot=document_title_snapshot,
                    file_name_snapshot=file_name_snapshot,
                    storage_path_snapshot=storage_path_snapshot,
                    chunk_count=chunk_count,
                    input_tokens=breakdown.input_tokens,
                    output_tokens=breakdown.output_tokens,
                    cached_input_tokens=breakdown.cached_input_tokens,
                    total_tokens=breakdown.total_tokens,
                    web_search_calls=breakdown.web_search_calls,
                    estimated_cost_usd=float(breakdown.estimated_cost_usd) if breakdown.estimated_cost_usd is not None else None,
                    status=status,
                    error_message=error_message,
                    raw_usage_json=breakdown.raw_usage_json,
                )
                db.add(row)
                db.commit()
        except Exception as exc:  # pragma: no cover - telemetry must not break product flow
            logger.warning("AI usage logging failed: %s", exc)

    def attach_document_usage(self, *, storage_path: str | None, document_id: int, document_title: str, file_name: str) -> None:
        if not storage_path:
            return

        try:
            with SessionLocal() as db:
                rows = (
                    db.query(AIRequestUsage)
                    .filter(AIRequestUsage.document_id.is_(None))
                    .filter(AIRequestUsage.storage_path_snapshot == storage_path)
                    .all()
                )
                for row in rows:
                    row.document_id = document_id
                    row.document_title_snapshot = document_title
                    row.file_name_snapshot = file_name
                db.commit()
        except Exception as exc:  # pragma: no cover - telemetry must not break product flow
            logger.warning("AI usage attachment failed for document %s: %s", document_id, exc)

    def build_usage_overview(self, db: Session) -> dict:
        rows = db.query(AIRequestUsage).order_by(AIRequestUsage.created_at.desc()).all()
        total_cost = sum((Decimal(str(row.estimated_cost_usd or 0)) for row in rows), Decimal("0"))
        return {
            "total_requests": len(rows),
            "metadata_requests": sum(1 for row in rows if row.request_type == "metadata"),
            "embedding_requests": sum(1 for row in rows if row.request_type == "embedding"),
            "total_input_tokens": sum(row.input_tokens for row in rows),
            "total_output_tokens": sum(row.output_tokens for row in rows),
            "total_cached_input_tokens": sum(row.cached_input_tokens for row in rows),
            "total_web_search_calls": sum(row.web_search_calls for row in rows),
            "total_estimated_cost_usd": float(total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        }

    def build_usage_by_day(self, db: Session, *, limit: int = 14) -> list[dict]:
        grouped: dict[date, dict] = {}
        rows = db.query(AIRequestUsage).order_by(AIRequestUsage.created_at.desc()).all()
        for row in rows:
            day = row.created_at.date()
            bucket = grouped.setdefault(day, {
                "day": day,
                "request_count": 0,
                "metadata_requests": 0,
                "embedding_requests": 0,
                "web_search_calls": 0,
                "estimated_cost_usd": Decimal("0"),
            })
            bucket["request_count"] += 1
            bucket["metadata_requests"] += 1 if row.request_type == "metadata" else 0
            bucket["embedding_requests"] += 1 if row.request_type == "embedding" else 0
            bucket["web_search_calls"] += row.web_search_calls
            bucket["estimated_cost_usd"] += Decimal(str(row.estimated_cost_usd or 0))

        items = sorted(grouped.values(), key=lambda item: item["day"], reverse=True)[:limit]
        for item in items:
            item["estimated_cost_usd"] = float(item["estimated_cost_usd"].quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        return items

    def build_usage_by_document(self, db: Session, *, limit: int = 20) -> list[dict]:
        grouped: dict[str, dict] = {}
        rows = db.query(AIRequestUsage).order_by(AIRequestUsage.created_at.desc()).all()
        documents = {
            document.id: document
            for document in db.query(Document).all()
        }
        for row in rows:
            title = row.document_title_snapshot or (documents.get(row.document_id).title if row.document_id in documents else None) or "Unknown document"
            file_name = row.file_name_snapshot or (documents.get(row.document_id).file_name if row.document_id in documents else None)
            group_key = f"{row.document_id or 'none'}::{title}::{file_name or ''}"
            bucket = grouped.setdefault(group_key, {
                "document_id": row.document_id,
                "title": title,
                "file_name": file_name,
                "models_used": set(),
                "request_count": 0,
                "metadata_requests": 0,
                "embedding_requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "web_search_calls": 0,
                "estimated_cost_usd": Decimal("0"),
            })
            bucket["request_count"] += 1
            bucket["metadata_requests"] += 1 if row.request_type == "metadata" else 0
            bucket["embedding_requests"] += 1 if row.request_type == "embedding" else 0
            bucket["input_tokens"] += row.input_tokens
            bucket["output_tokens"] += row.output_tokens
            bucket["web_search_calls"] += row.web_search_calls
            bucket["estimated_cost_usd"] += Decimal(str(row.estimated_cost_usd or 0))
            model_label = row.model
            if row.request_type == "metadata":
                model_label = f"{row.model} ({'web search' if row.web_search_calls else 'no search'})"
            bucket["models_used"].add(model_label)

        items = sorted(grouped.values(), key=lambda item: (item["estimated_cost_usd"], item["request_count"]), reverse=True)[:limit]
        for item in items:
            item["estimated_cost_usd"] = float(item["estimated_cost_usd"].quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            item["models_used"] = sorted(item["models_used"])
        return items

    def list_recent_requests(self, db: Session, *, limit: int = 100) -> list[dict]:
        rows = (
            db.query(AIRequestUsage)
            .order_by(AIRequestUsage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": row.id,
                "created_at": row.created_at,
                "request_type": row.request_type,
                "endpoint": row.endpoint,
                "provider": row.provider,
                "model": row.model,
                "request_identifier": row.request_identifier,
                "document_id": row.document_id,
                "document_title": row.document_title_snapshot,
                "file_name": row.file_name_snapshot,
                "chunk_count": row.chunk_count,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cached_input_tokens": row.cached_input_tokens,
                "total_tokens": row.total_tokens,
                "web_search_calls": row.web_search_calls,
                "estimated_cost_usd": float(Decimal(str(row.estimated_cost_usd or 0)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
                "status": row.status,
                "error_message": row.error_message,
            }
            for row in rows
        ]

    def _estimate_cost(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int,
        web_search_calls: int,
    ) -> Decimal | None:
        pricing = self.MODEL_PRICING.get(model)
        total_cost = Decimal("0")
        if pricing:
            uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)
            total_cost += (Decimal(uncached_input_tokens) / Decimal("1000000")) * pricing["input"]
            total_cost += (Decimal(cached_input_tokens) / Decimal("1000000")) * pricing["cached_input"]
            total_cost += (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
        if web_search_calls:
            total_cost += Decimal(web_search_calls) * self.WEB_SEARCH_CALL_PRICE_USD
        if not pricing and not web_search_calls:
            return None
        return total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


ai_usage_service = AIUsageService()