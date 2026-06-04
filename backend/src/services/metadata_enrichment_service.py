import json
import re

import httpx

from src.core.config import settings
from src.core.logging import logger
from src.services.ai_usage_service import ai_usage_service


class MetadataEnrichmentService:
    def is_enabled(self) -> bool:
        if not settings.document_metadata_ai_enabled:
            return False
        if settings.metadata_ai_provider == "anthropic":
            return bool(settings.anthropic_api_key)
        return bool(settings.openai_api_key)

    def enrich_document_metadata(
        self,
        *,
        title: str | None,
        preview_text: str,
        allowed_domains: list[tuple[str, str]],
        allowed_document_types: list[tuple[str, str]],
        allowed_authority_levels: list[tuple[str, str]],
        file_name: str | None = None,
        storage_path: str | None = None,
        document_id: int | None = None,
    ) -> dict[str, str | None]:
        if not self.is_enabled() or not title:
            return {}

        domain_lines = "\n".join(f"- {slug}: {name}" for slug, name in allowed_domains)
        preview_excerpt = self._first_words(preview_text, 1500)
        authority_level_lines = "\n".join(f"- {slug}: {name}" for slug, name in allowed_authority_levels)
        document_type_lines = "\n".join(f"- {slug}: {name}" for slug, name in allowed_document_types)
        uses_web_search = settings.document_metadata_web_search_enabled
        prompt_sections = [
            "Nhiệm vụ: trích xuất metadata pháp lý cho một văn bản Việt Nam từ đoạn trích đầu văn bản"
            f"{' và nguồn web đáng tin cậy nếu web search đang được bật' if uses_web_search else ''}.",
            "Yêu cầu bắt buộc:",
        ]
        if uses_web_search:
            prompt_sections.append("- Phải ưu tiên tra cứu các nguồn chính thống hoặc nguồn pháp lý đáng tin cậy trên internet nếu có.")
        prompt_sections.append("- Không được suy đoán. Nếu không xác nhận được một trường thì trả về null.")
        prompt_sections.append("- Không được lấy số hiệu, ngày ký, ngày hiệu lực hoặc ngày hết hiệu lực của văn bản được viện dẫn; chỉ lấy metadata của chính văn bản hiện tại.")
        if uses_web_search:
            prompt_sections.append("- Nếu thông tin trong web mâu thuẫn với đoạn trích đầu văn bản, ưu tiên trả về null thay vì bịa.")
            prompt_sections.append("- Summary chỉ được tóm tắt từ nội dung có thật trong đoạn trích hoặc nguồn web đã xác nhận.")
        else:
            prompt_sections.append("- Summary chỉ được tóm tắt từ nội dung có thật trong đoạn trích.")
        prompt_sections.extend([
            "- Chỉ trả về JSON theo schema yêu cầu.",
            "",
            "Danh sách legal_domain hợp lệ:",
            domain_lines,
            "",
            "Danh sách authority_level hợp lệ:",
            authority_level_lines,
            "",
            "Danh sách document_type hợp lệ:",
            document_type_lines,
            "",
            f"Tiêu đề đã trích được:\n{title}",
            "",
            f"1500 từ đầu văn bản:\n{preview_excerpt}",
        ])
        prompt = "\n".join(prompt_sections)

        provider = settings.metadata_ai_provider
        model = settings.anthropic_metadata_model if provider == "anthropic" else settings.openai_metadata_model
        try:
            if provider == "anthropic":
                payload = self._request_anthropic_metadata(prompt=prompt, model=model)
            else:
                payload = self._request_openai_metadata(prompt=prompt, model=model, uses_web_search=uses_web_search)
        except Exception as exc:  # pragma: no cover - defensive external API boundary
            logger.warning("%s metadata enrichment failed: %s", provider, exc)
            ai_usage_service.log_request(
                request_type="metadata",
                endpoint="messages" if provider == "anthropic" else "responses",
                provider=provider,
                model=model,
                document_id=document_id,
                document_title_snapshot=title,
                file_name_snapshot=file_name,
                storage_path_snapshot=storage_path,
                status="failed",
                error_message=str(exc),
            )
            return {}

        try:
            raw_text = self._extract_response_text(payload, provider=provider)
            if not raw_text:
                return {}

            match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
            parsed = json.loads(match.group(0) if match else raw_text)
        except Exception as exc:  # pragma: no cover - defensive parsing guard
            logger.warning("%s metadata payload parsing failed: %s", provider, exc)
            ai_usage_service.log_request(
                request_type="metadata",
                endpoint="messages" if provider == "anthropic" else "responses",
                provider=provider,
                model=model,
                document_id=document_id,
                document_title_snapshot=title,
                file_name_snapshot=file_name,
                storage_path_snapshot=storage_path,
                payload=locals().get("payload"),
                status="failed",
                error_message=str(exc),
            )
            return {}

        result: dict[str, str | None] = {}
        for key in (
            "title",
            "document_code",
            "document_type",
            "legal_domain",
            "authority_level",
            "issuing_authority",
            "signed_date",
            "effective_date",
            "expiry_date",
            "legal_status",
            "summary",
        ):
            value = parsed.get(key)
            if value is None:
                result[key] = None
                continue
            normalized = str(value).strip()
            if self._is_empty_value(normalized):
                result[key] = None
            else:
                result[key] = normalized
        ai_usage_service.log_request(
            request_type="metadata",
            endpoint="messages" if provider == "anthropic" else "responses",
            provider=provider,
            model=model,
            document_id=document_id,
            document_title_snapshot=title,
            file_name_snapshot=file_name,
            storage_path_snapshot=storage_path,
            payload=payload,
            status="success",
        )
        return result

    def _request_openai_metadata(self, *, prompt: str, model: str, uses_web_search: bool) -> dict:
        request_payload = {
            "model": model,
            "instructions": (
                "Bạn là chuyên gia tra cứu văn bản pháp luật Việt Nam. "
                + ("Chỉ dùng web search khi cần xác minh metadata và tuyệt đối không bịa thông tin." if uses_web_search else "Chỉ dùng nội dung đoạn trích để trích xuất metadata và tuyệt đối không bịa thông tin.")
            ),
            "input": prompt,
            "tool_choice": "auto",
            "max_output_tokens": 1400,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "legal_document_metadata",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": ["string", "null"]},
                            "document_code": {"type": ["string", "null"]},
                            "document_type": {"type": ["string", "null"]},
                            "legal_domain": {"type": ["string", "null"]},
                            "authority_level": {"type": ["string", "null"]},
                            "issuing_authority": {"type": ["string", "null"]},
                            "signed_date": {"type": ["string", "null"]},
                            "effective_date": {"type": ["string", "null"]},
                            "expiry_date": {"type": ["string", "null"]},
                            "legal_status": {"type": ["string", "null"]},
                            "summary": {"type": ["string", "null"]},
                        },
                        "required": ["title", "document_code", "document_type", "legal_domain", "authority_level", "issuing_authority", "signed_date", "effective_date", "expiry_date", "legal_status", "summary"],
                    },
                }
            },
        }
        if uses_web_search:
            request_payload["tools"] = [{"type": "web_search", "user_location": {"type": "approximate", "country": "VN"}}]
            request_payload["include"] = ["web_search_call.action.sources"]

        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json=request_payload,
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _request_anthropic_metadata(self, *, prompt: str, model: str) -> dict:
        response = httpx.post(
            f"{settings.anthropic_base_url.rstrip('/')}/messages",
            headers={
                "x-api-key": str(settings.anthropic_api_key),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1400,
                "system": "Bạn là chuyên gia tra cứu văn bản pháp luật Việt Nam. Chỉ dùng nội dung được cung cấp, không bịa thông tin, và luôn trả về JSON hợp lệ.",
                "messages": [{"role": "user", "content": prompt + "\n\nChỉ trả về duy nhất một object JSON."}],
            },
            timeout=settings.document_metadata_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _extract_response_text(self, payload: dict, *, provider: str) -> str:
        if provider == "anthropic":
            texts: list[str] = []
            for item in payload.get("content") or []:
                if item.get("type") == "text" and item.get("text"):
                    texts.append(str(item.get("text")).strip())
            return "\n".join(part for part in texts if part).strip()

        raw_text = str(payload.get("output_text") or "").strip()
        if raw_text:
            return raw_text
        for item in payload.get("output") or []:
            if item.get("type") != "message":
                continue
            for content_item in item.get("content") or []:
                if content_item.get("type") == "output_text" and content_item.get("text"):
                    return str(content_item.get("text")).strip()
        return ""

    def _first_words(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])

    def _is_empty_value(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in {"", "null", "none", "khong co", "không có", "chua ro", "chưa rõ", "n/a", "unknown"}


metadata_enrichment_service = MetadataEnrichmentService()
