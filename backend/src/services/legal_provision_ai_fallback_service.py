from __future__ import annotations

import json
from collections.abc import Sequence

import httpx

from src.core.config import settings
from src.core.logging import logger
from src.services.legal_provision_parser_service import legal_provision_parser_service


class LegalProvisionAIFallbackService:
    def is_enabled(self) -> bool:
        if not settings.legal_structure_ai_fallback_enabled:
            return False
        if settings.metadata_ai_provider == "anthropic":
            return bool(settings.anthropic_api_key)
        return bool(settings.openai_api_key)

    def parse_text(self, *, document_id: int, text: str) -> list[dict[str, object | None]]:
        if not self.is_enabled():
            return []

        payload = self._request_structure_parse(text=text)
        items = self._extract_items(payload)
        return self._sanitize_items(document_id=document_id, items=items)

    def _request_structure_parse(self, *, text: str) -> dict:
        provider = settings.metadata_ai_provider
        model = settings.anthropic_metadata_model if provider == "anthropic" else settings.openai_metadata_model
        if provider == "anthropic":
            return self._request_anthropic(text=text, model=model)
        return self._request_openai(text=text, model=model)

    def _request_openai(self, *, text: str, model: str) -> dict:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "max_output_tokens": 4000,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "legal_provision_parse",
                        "schema": self._response_schema(),
                    }
                },
                "input": self._build_messages(text),
            },
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _request_anthropic(self, *, text: str, model: str) -> dict:
        response = httpx.post(
            f"{settings.anthropic_base_url.rstrip('/')}/messages",
            headers={
                "x-api-key": str(settings.anthropic_api_key),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4000,
                "temperature": 0,
                "system": self._system_prompt(),
                "messages": [
                    {
                        "role": "user",
                        "content": self._user_prompt(text),
                    }
                ],
            },
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _extract_items(self, payload: dict) -> list[dict]:
        provider = settings.metadata_ai_provider
        if provider == "anthropic":
            text_chunks = [
                item.get("text", "")
                for item in payload.get("content", [])
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            raw_text = "\n".join(chunk for chunk in text_chunks if chunk).strip()
            if not raw_text:
                return []
            parsed = json.loads(raw_text)
        else:
            parsed = payload
            if isinstance(payload.get("output"), list):
                for output_item in payload["output"]:
                    if not isinstance(output_item, dict):
                        continue
                    for content_item in output_item.get("content", []):
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            text_value = content_item.get("text", "")
                            if text_value:
                                parsed = json.loads(text_value)
                                break

        items = parsed.get("provisions", []) if isinstance(parsed, dict) else []
        return items if isinstance(items, list) else []

    def _sanitize_items(self, *, document_id: int, items: Sequence[dict]) -> list[dict[str, object | None]]:
        normalized_payloads: list[dict[str, object | None]] = []
        normalized_id_map: dict[str, int] = {}
        sequence_index = 0

        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            provision_level = str(raw_item.get("provision_level") or "").strip().lower()
            if provision_level not in {"article", "clause", "point"}:
                continue

            article_number = self._clean_value(raw_item.get("article_number"))
            clause_number = self._clean_value(raw_item.get("clause_number"))
            point_code = self._clean_value(raw_item.get("point_code"))
            heading = self._clean_value(raw_item.get("heading"))
            content = self._clean_value(raw_item.get("content"))
            if not content:
                continue

            sequence_index += 1
            node_id = self._clean_value(raw_item.get("node_id")) or f"node-{sequence_index}"
            parent_node_id = self._clean_value(raw_item.get("parent_node_id"))

            article_sort = legal_provision_parser_service._sort_fragment(article_number)
            clause_sort = legal_provision_parser_service._sort_fragment(clause_number)
            point_sort = legal_provision_parser_service._point_sort_fragment(point_code)
            citation_parts = []
            if article_number:
                citation_parts.append(f"Điều {article_number}")
            if clause_number:
                citation_parts.append(f"Khoản {clause_number}")
            if point_code:
                citation_parts.append(f"Điểm {point_code}")
            citation_label = " ".join(citation_parts) or heading or f"{provision_level.title()} {sequence_index}"

            metadata_json = json.dumps(
                {
                    "parser_source": "ai_fallback",
                    "ai_provider": settings.metadata_ai_provider,
                    "requires_review": True,
                    "heading": heading[:500] if heading else None,
                },
                ensure_ascii=False,
            )
            normalized_id_map[node_id] = sequence_index
            normalized_payloads.append(
                {
                    "document_id": document_id,
                    "parent_provision_id": parent_node_id,
                    "provision_level": provision_level,
                    "article_number": article_number,
                    "clause_number": clause_number,
                    "point_code": point_code,
                    "heading": heading[:500] if heading else None,
                    "content": content,
                    "citation_label": citation_label[:255],
                    "sort_key": f"{article_sort}.{clause_sort}.{point_sort}",
                    "metadata_json": metadata_json,
                }
            )

        for payload in normalized_payloads:
            parent_node_id = payload["parent_provision_id"]
            payload["parent_provision_id"] = normalized_id_map.get(parent_node_id) if isinstance(parent_node_id, str) else None

        return normalized_payloads

    def _clean_value(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _system_prompt(self) -> str:
        return (
            "You are a legal document structure parser. "
            "Return only valid JSON with a provisions array. "
            "Identify article, clause, and point hierarchy from Vietnamese legal text. "
            "Do not invent content that is not present."
        )

    def _user_prompt(self, text: str) -> str:
        return (
            "Parse the Vietnamese legal text into hierarchical provisions.\n"
            "Return JSON only with this shape:\n"
            "{\"provisions\":[{\"node_id\":\"...\",\"parent_node_id\":\"... or null\",\"provision_level\":\"article|clause|point\",\"article_number\":\"... or null\",\"clause_number\":\"... or null\",\"point_code\":\"... or null\",\"heading\":\"... or null\",\"content\":\"...\"}]}\n"
            "Rules:\n"
            "- Preserve only structure supported by the text.\n"
            "- node_id must be unique.\n"
            "- parent_node_id of an article must be null.\n"
            "- clause should point to its article.\n"
            "- point should point to its clause.\n"
            "- content must be concise but keep the legal sentence text.\n\n"
            f"TEXT:\n{text[:120000]}"
        )

    def _build_messages(self, text: str) -> list[dict[str, object]]:
        return [
            {"role": "system", "content": [{"type": "input_text", "text": self._system_prompt()}]},
            {"role": "user", "content": [{"type": "input_text", "text": self._user_prompt(text)}]},
        ]

    def _response_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "provisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string"},
                            "parent_node_id": {"type": ["string", "null"]},
                            "provision_level": {"type": "string", "enum": ["article", "clause", "point"]},
                            "article_number": {"type": ["string", "null"]},
                            "clause_number": {"type": ["string", "null"]},
                            "point_code": {"type": ["string", "null"]},
                            "heading": {"type": ["string", "null"]},
                            "content": {"type": "string"},
                        },
                        "required": ["node_id", "parent_node_id", "provision_level", "article_number", "clause_number", "point_code", "heading", "content"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["provisions"],
            "additionalProperties": False,
        }


legal_provision_ai_fallback_service = LegalProvisionAIFallbackService()
