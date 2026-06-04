from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.exceptions import ValidationException
from src.core.logging import logger
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_provision import LegalProvision
from src.services.ai_usage_service import ai_usage_service
from src.services.corpus_quality_report_service import corpus_quality_report_service


class AICorpusReviewAgentService:
    def is_enabled(self) -> bool:
        if settings.metadata_ai_provider == "anthropic":
            return bool(settings.anthropic_api_key)
        return bool(settings.openai_api_key)

    def review_pending_documents(
        self,
        db: Session,
        *,
        max_documents: int | None = None,
        include_reviewed: bool = False,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            raise ValidationException("AI review agent is not configured")

        report = corpus_quality_report_service.build_report(db, include_reviewed=include_reviewed)
        items = list(report["items"])
        if max_documents is not None:
            items = items[:max_documents]

        reviews = []
        for item in items:
            document = db.query(Document).filter(Document.id == int(item["document_id"])).first()
            if document is None:
                continue
            reviews.append(self.review_document(db, document=document, quality_item=item))

        return {
            "agent": "ai_corpus_review_v0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": self._model_name(),
            "policy": {
                "ai_is_authoritative": False,
                "requires_human_review": True,
                "may_mark_document_reviewed": False,
            },
            "source_report_summary": report["summary"],
            "review_count": len(reviews),
            "reviews": reviews,
        }

    def review_document(self, db: Session, *, document: Document, quality_item: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(
            document=document,
            quality_item=quality_item,
            chunk_excerpts=self._load_chunk_excerpts(db, document.id),
            provision_excerpts=self._load_provision_excerpts(db, document.id),
        )
        provider = settings.metadata_ai_provider
        model = self._model_name()
        try:
            if provider == "anthropic":
                payload = self._request_anthropic(prompt=prompt, model=model)
            else:
                payload = self._request_openai(prompt=prompt, model=model)
            raw_text = self._extract_response_text(payload, provider=provider)
            parsed = self._parse_json_object(raw_text)
            parsed["document_id"] = document.id
            parsed["file_name"] = document.file_name
            parsed["requires_human_review"] = True
            parsed["ai_is_authoritative"] = False
            ai_usage_service.log_request(
                request_type="ai_corpus_review",
                endpoint="messages" if provider == "anthropic" else "responses",
                provider=provider,
                model=model,
                document_id=document.id,
                document_title_snapshot=document.title,
                file_name_snapshot=document.file_name,
                storage_path_snapshot=document.storage_path,
                payload=payload,
                status="success",
            )
            return parsed
        except Exception as exc:  # pragma: no cover - external API defensive guard
            logger.warning("AI corpus review failed for document %s: %s", document.id, exc)
            ai_usage_service.log_request(
                request_type="ai_corpus_review",
                endpoint="messages" if provider == "anthropic" else "responses",
                provider=provider,
                model=model,
                document_id=document.id,
                document_title_snapshot=document.title,
                file_name_snapshot=document.file_name,
                storage_path_snapshot=document.storage_path,
                status="failed",
                error_message=str(exc),
            )
            return {
                "document_id": document.id,
                "file_name": document.file_name,
                "ai_review_status": "failed",
                "risk_level": "high",
                "requires_human_review": True,
                "ai_is_authoritative": False,
                "reviewer_notes": f"AI review failed: {exc}",
                "metadata_findings": [],
                "parser_findings": [],
                "relation_findings": [],
                "suggested_metadata_updates": {},
                "retrieval_decision": "keep_unreviewed",
                "confidence": 0.0,
            }

    def save_report(self, report: dict[str, Any], output_path: str | Path | None = None) -> Path:
        target = Path(output_path) if output_path else settings.project_root / "docs" / "legal_sources" / "ai_review_reports" / f"ai_corpus_review_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def _build_prompt(
        self,
        *,
        document: Document,
        quality_item: dict[str, Any],
        chunk_excerpts: list[dict[str, Any]],
        provision_excerpts: list[dict[str, Any]],
    ) -> str:
        payload = {
            "document": {
                "id": document.id,
                "title": document.title,
                "file_name": document.file_name,
                "document_code": document.document_code,
                "document_type": document.document_type,
                "legal_domain": document.legal_domain,
                "authority_level": document.authority_level,
                "issuing_authority": document.issuing_authority,
                "signed_date": document.signed_date.isoformat() if document.signed_date else None,
                "effective_date": document.effective_date.isoformat() if document.effective_date else None,
                "expiry_date": document.expiry_date.isoformat() if document.expiry_date else None,
                "legal_status": document.legal_status,
                "metadata_review_status": document.metadata_review_status,
                "ingestion_quality_status": document.ingestion_quality_status,
                "retrieval_visibility": document.retrieval_visibility,
                "content_sha256": document.content_sha256,
                "source_identity": document.source_identity,
            },
            "automated_quality_item": quality_item,
            "chunk_excerpts": chunk_excerpts,
            "provision_excerpts": provision_excerpts,
        }
        return (
            "Bạn là AI reviewer vòng 0 cho hệ thống LawChat-AI. "
            "Nhiệm vụ là phát hiện rủi ro dữ liệu, không phải xác nhận tính đúng pháp lý cuối cùng.\n"
            "Quy tắc bắt buộc:\n"
            "- Không được bịa metadata hoặc kết luận ngoài dữ liệu được cung cấp.\n"
            "- Nếu không chắc, ghi needs_human_review.\n"
            "- Không được đề xuất mark reviewed nếu còn metadata/parser/relation issue.\n"
            "- Output chỉ là pre-review, không authoritative.\n"
            "- Trả về JSON đúng schema.\n\n"
            f"Dữ liệu review:\n{json.dumps(payload, ensure_ascii=False)}"
        )

    def _load_chunk_excerpts(self, db: Session, document_id: int, limit: int = 8) -> list[dict[str, Any]]:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "chunk_index": chunk.chunk_index,
                "citation_label": chunk.citation_label,
                "hierarchy_path": chunk.hierarchy_path,
                "article_number": chunk.article_number,
                "content_excerpt": " ".join(chunk.content.split())[:900],
            }
            for chunk in chunks
        ]

    def _load_provision_excerpts(self, db: Session, document_id: int, limit: int = 12) -> list[dict[str, Any]]:
        provisions = (
            db.query(LegalProvision)
            .filter(LegalProvision.document_id == document_id)
            .order_by(LegalProvision.sort_key.asc(), LegalProvision.id.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "provision_level": provision.provision_level,
                "citation_label": provision.citation_label,
                "article_number": provision.article_number,
                "clause_number": provision.clause_number,
                "point_code": provision.point_code,
                "content_excerpt": " ".join(provision.content.split())[:700],
            }
            for provision in provisions
        ]

    def _request_openai(self, *, prompt: str, model: str) -> dict:
        request_payload = {
            "model": model,
            "instructions": "Bạn là AI reviewer dữ liệu pháp lý. Chỉ phân tích dữ liệu được cung cấp, không bịa, luôn yêu cầu human review.",
            "input": prompt,
            "max_output_tokens": 1800,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_corpus_review",
                    "strict": True,
                    "schema": self._review_schema(),
                },
            },
        }
        try:
            response = httpx.post(
                f"{settings.openai_base_url.rstrip('/')}/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=request_payload,
                timeout=settings.document_metadata_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("OpenAI-compatible responses review call failed, falling back to chat completions: %s", exc.response.text[:500])
            return self._request_openai_chat(prompt=prompt, model=model)

    def _request_openai_chat(self, *, prompt: str, model: str) -> dict:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Bạn là AI reviewer dữ liệu pháp lý. Chỉ phân tích dữ liệu được cung cấp, không bịa, "
                            "luôn yêu cầu human review. Chỉ trả về JSON hợp lệ theo các field: "
                            "ai_review_status, risk_level, metadata_findings, parser_findings, relation_findings, "
                            "suggested_metadata_updates, retrieval_decision, reviewer_notes, confidence."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 1800,
            },
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _request_anthropic(self, *, prompt: str, model: str) -> dict:
        response = httpx.post(
            f"{settings.anthropic_base_url.rstrip('/')}/messages",
            headers={
                "x-api-key": str(settings.anthropic_api_key),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1800,
                "system": "Bạn là AI reviewer dữ liệu pháp lý. Chỉ phân tích dữ liệu được cung cấp, không bịa, luôn yêu cầu human review.",
                "messages": [{"role": "user", "content": prompt + "\n\nChỉ trả về duy nhất một object JSON."}],
            },
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _review_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "ai_review_status": {"type": "string", "enum": ["likely_ok", "needs_human_review", "reject_prelabel", "failed"]},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "metadata_findings": {"type": "array", "items": {"type": "string"}},
                "parser_findings": {"type": "array", "items": {"type": "string"}},
                "relation_findings": {"type": "array", "items": {"type": "string"}},
                "suggested_metadata_updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "field": {"type": "string"},
                            "suggested_value": {"type": ["string", "null"]},
                            "reason": {"type": "string"},
                        },
                        "required": ["field", "suggested_value", "reason"],
                    },
                },
                "retrieval_decision": {"type": "string", "enum": ["keep_blocked", "keep_unreviewed", "candidate_for_verified_after_human_review"]},
                "reviewer_notes": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": [
                "ai_review_status",
                "risk_level",
                "metadata_findings",
                "parser_findings",
                "relation_findings",
                "suggested_metadata_updates",
                "retrieval_decision",
                "reviewer_notes",
                "confidence",
            ],
        }

    def _extract_response_text(self, payload: dict, *, provider: str) -> str:
        if provider == "anthropic":
            return "\n".join(str(item.get("text", "")).strip() for item in payload.get("content") or [] if item.get("type") == "text").strip()
        choices = payload.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            if message.get("content"):
                return str(message["content"]).strip()
        if payload.get("output_text"):
            return str(payload["output_text"]).strip()
        for item in payload.get("output") or []:
            if item.get("type") != "message":
                continue
            for content_item in item.get("content") or []:
                if content_item.get("type") == "output_text" and content_item.get("text"):
                    return str(content_item["text"]).strip()
        return ""

    def _parse_json_object(self, raw_text: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        return json.loads(match.group(0) if match else raw_text)

    def _model_name(self) -> str:
        return settings.anthropic_metadata_model if settings.metadata_ai_provider == "anthropic" else settings.openai_metadata_model


ai_corpus_review_agent_service = AICorpusReviewAgentService()
