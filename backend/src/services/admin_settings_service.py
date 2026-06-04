from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

from src.core.config import settings
from src.schemas.admin_schema import (
    ChatbotAISettingsPayload,
    EmbeddingAISettingsPayload,
    GraphBackendSettingsPayload,
    MetadataAISettingsPayload,
    UpdateChatbotAISettingsRequest,
    UpdateEmbeddingAISettingsRequest,
    UpdateGraphBackendSettingsRequest,
    UpdateMetadataAISettingsRequest,
)
from src.services.graph_backend_service import graph_backend_service


METADATA_MODEL_OPTIONS = (
    "cx/gpt-5.5",
    "cx/gpt-5.4",
    "cx/gpt-5.2",
    "cx/gpt-5.3-codex-high",
    "cx/gpt-5.3-codex-low",
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4.1",
    "gpt-4.1-mini",
)
CHATBOT_MODEL_OPTIONS = (
    "cx/gpt-5.5",
    "cx/gpt-5.4",
    "cx/gpt-5.2",
    "cx/gpt-5.3-codex-high",
    "cx/gpt-5.3-codex-low",
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4.1",
    "gpt-4.1-mini",
)
EMBEDDING_MODEL_OPTIONS = ("intfloat/multilingual-e5-small", "text-embedding-3-small", "text-embedding-3-large")
CLAUDE_MODEL_OPTIONS = ("claude-3-5-haiku-latest", "claude-3-7-sonnet-latest")
AI_PROVIDER_OPTIONS = ("openai", "anthropic")
GRAPH_BACKEND_OPTIONS = ("relational", "neo4j")


class AdminSettingsService:
    def update_metadata_ai_settings(self, payload: UpdateMetadataAISettingsRequest) -> MetadataAISettingsPayload:
        if payload.provider not in AI_PROVIDER_OPTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported metadata AI provider")
        if payload.model not in self.metadata_model_options_for_provider(payload.provider):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported metadata AI model")

        settings.document_metadata_ai_enabled = payload.enabled
        settings.metadata_ai_provider = payload.provider
        if payload.provider == "anthropic":
            settings.anthropic_metadata_model = payload.model
        else:
            settings.openai_metadata_model = payload.model
        settings.document_metadata_web_search_enabled = payload.web_search_enabled
        self.persist_env_value("DOCUMENT_METADATA_AI_ENABLED", "true" if payload.enabled else "false")
        self.persist_env_value("METADATA_AI_PROVIDER", payload.provider)
        self.persist_env_value("ANTHROPIC_METADATA_MODEL" if payload.provider == "anthropic" else "OPENAI_METADATA_MODEL", payload.model)
        self.persist_env_value("DOCUMENT_METADATA_WEB_SEARCH_ENABLED", "true" if payload.web_search_enabled else "false")
        return self.build_metadata_ai_settings()

    def update_embedding_ai_settings(self, payload: UpdateEmbeddingAISettingsRequest) -> EmbeddingAISettingsPayload:
        if payload.model not in EMBEDDING_MODEL_OPTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported embedding model")
        settings.ai_embedding_enabled = payload.enabled
        if payload.model.startswith("intfloat/"):
            settings.embedding_provider = "local"
            settings.local_embedding_model = payload.model
            self.persist_env_value("EMBEDDING_PROVIDER", "local")
            self.persist_env_value("LOCAL_EMBEDDING_MODEL", payload.model)
        else:
            settings.embedding_provider = "openai"
            settings.openai_embedding_model = payload.model
            self.persist_env_value("EMBEDDING_PROVIDER", "openai")
            self.persist_env_value("OPENAI_EMBEDDING_MODEL", payload.model)
        self.persist_env_value("AI_EMBEDDING_ENABLED", "true" if payload.enabled else "false")
        return self.build_embedding_ai_settings()

    def update_chatbot_ai_settings(self, payload: UpdateChatbotAISettingsRequest) -> ChatbotAISettingsPayload:
        if payload.provider not in AI_PROVIDER_OPTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported chatbot provider")
        available_models = self.chat_model_options_for_provider(payload.provider)
        if payload.public_model not in available_models:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported public chatbot model")
        if payload.customer_model not in available_models:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported customer chatbot model")
        if payload.consultant_model not in available_models:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported consultant chatbot model")

        settings.ai_chat_enabled = payload.enabled
        settings.chatbot_ai_provider = payload.provider
        if payload.provider == "anthropic":
            settings.anthropic_public_chat_model = payload.public_model
            settings.anthropic_customer_chat_model = payload.customer_model
            settings.anthropic_consultant_assist_model = payload.consultant_model
        else:
            settings.openai_public_chat_model = payload.public_model
            settings.openai_customer_chat_model = payload.customer_model
            settings.openai_chat_model = payload.customer_model
            settings.openai_consultant_assist_model = payload.consultant_model
        self.persist_env_value("AI_CHAT_ENABLED", "true" if payload.enabled else "false")
        self.persist_env_value("CHATBOT_AI_PROVIDER", payload.provider)
        if payload.provider == "anthropic":
            self.persist_env_value("ANTHROPIC_PUBLIC_CHAT_MODEL", payload.public_model)
            self.persist_env_value("ANTHROPIC_CUSTOMER_CHAT_MODEL", payload.customer_model)
            self.persist_env_value("ANTHROPIC_CONSULTANT_ASSIST_MODEL", payload.consultant_model)
        else:
            self.persist_env_value("OPENAI_PUBLIC_CHAT_MODEL", payload.public_model)
            self.persist_env_value("OPENAI_CUSTOMER_CHAT_MODEL", payload.customer_model)
            self.persist_env_value("OPENAI_CHAT_MODEL", payload.customer_model)
            self.persist_env_value("OPENAI_CONSULTANT_ASSIST_MODEL", payload.consultant_model)
        return self.build_chatbot_ai_settings()

    def update_graph_backend_settings(self, payload: UpdateGraphBackendSettingsRequest) -> GraphBackendSettingsPayload:
        if payload.backend not in GRAPH_BACKEND_OPTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported graph backend")
        if payload.backend == "neo4j" and not graph_backend_service.backend_overview()["neo4j"].get("configured"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Neo4j backend is not configured")
        settings.graph_backend = payload.backend
        self.persist_env_value("GRAPH_BACKEND", payload.backend)
        return self.build_graph_backend_settings()

    def build_metadata_ai_settings(self) -> MetadataAISettingsPayload:
        provider = settings.metadata_ai_provider
        model = settings.anthropic_metadata_model if provider == "anthropic" else settings.openai_metadata_model
        provider_enabled = bool(settings.anthropic_api_key) if provider == "anthropic" else bool(settings.openai_api_key)
        return MetadataAISettingsPayload(
            enabled=settings.document_metadata_ai_enabled and provider_enabled,
            provider=provider,
            model=model,
            web_search_enabled=settings.document_metadata_web_search_enabled,
            available_providers=list(AI_PROVIDER_OPTIONS),
            available_models=list(self.metadata_model_options_for_provider(provider)),
        )

    def build_embedding_ai_settings(self) -> EmbeddingAISettingsPayload:
        provider_ready = True if settings.embedding_provider == "local" else bool(settings.openai_api_key)
        model = settings.local_embedding_model if settings.embedding_provider == "local" else settings.openai_embedding_model
        return EmbeddingAISettingsPayload(enabled=settings.ai_embedding_enabled and provider_ready, model=model, available_models=list(EMBEDDING_MODEL_OPTIONS))

    def build_chatbot_ai_settings(self) -> ChatbotAISettingsPayload:
        provider = settings.chatbot_ai_provider
        customer_model = settings.anthropic_customer_chat_model if provider == "anthropic" else settings.openai_customer_chat_model
        provider_enabled = bool(settings.anthropic_api_key) if provider == "anthropic" else bool(settings.openai_api_key)
        return ChatbotAISettingsPayload(
            enabled=settings.ai_chat_enabled and provider_enabled,
            provider=provider,
            model=customer_model,
            public_model=settings.anthropic_public_chat_model if provider == "anthropic" else settings.openai_public_chat_model,
            customer_model=customer_model,
            consultant_model=settings.anthropic_consultant_assist_model if provider == "anthropic" else settings.openai_consultant_assist_model,
            available_providers=list(AI_PROVIDER_OPTIONS),
            available_models=list(self.chat_model_options_for_provider(provider)),
        )

    def build_graph_backend_settings(self) -> GraphBackendSettingsPayload:
        overview = graph_backend_service.backend_overview()
        neo4j = overview.get("neo4j", {})
        return GraphBackendSettingsPayload(
            backend=settings.graph_backend,
            available_backends=list(GRAPH_BACKEND_OPTIONS),
            neo4j_configured=bool(neo4j.get("configured")),
            neo4j_available=bool(neo4j.get("available")),
            neo4j_database=str(neo4j.get("database")) if neo4j.get("database") is not None else None,
            neo4j_sync_enabled=bool(neo4j.get("sync_enabled")),
        )

    def metadata_model_options_for_provider(self, provider: str) -> tuple[str, ...]:
        return CLAUDE_MODEL_OPTIONS if provider == "anthropic" else METADATA_MODEL_OPTIONS

    def chat_model_options_for_provider(self, provider: str) -> tuple[str, ...]:
        return CLAUDE_MODEL_OPTIONS if provider == "anthropic" else CHATBOT_MODEL_OPTIONS

    def persist_env_value(self, key: str, value: str) -> None:
        env_path = settings.project_root / ".env"
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        updated = False
        next_lines: list[str] = []
        for line in lines:
            if line.startswith(f"{key}="):
                next_lines.append(f"{key}={value}")
                updated = True
            else:
                next_lines.append(line)
        if not updated:
            next_lines.append(f"{key}={value}")
        env_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


admin_settings_service = AdminSettingsService()
