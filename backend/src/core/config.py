from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LawChat-AI API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/lawchat_ai"
    secret_key: str = "replace-this-secret-before-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    auto_create_tables: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]
    ai_embedding_enabled: bool = False
    embedding_provider: str = "local"
    ai_chat_enabled: bool = True
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    metadata_ai_provider: str = "openai"
    chatbot_ai_provider: str = "openai"
    openai_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "intfloat/multilingual-e5-small"
    local_embedding_batch_size: int = 32
    local_embedding_device: str = "cpu"
    openai_public_chat_model: str = "gpt-4.1-mini"
    openai_customer_chat_model: str = "gpt-4.1-mini"
    openai_consultant_assist_model: str = "gpt-4.1-mini"
    openai_chat_model: str = "gpt-4.1-mini"
    openai_metadata_model: str = "gpt-4.1-mini"
    anthropic_public_chat_model: str = "claude-3-5-haiku-latest"
    anthropic_customer_chat_model: str = "claude-3-7-sonnet-latest"
    anthropic_consultant_assist_model: str = "claude-3-7-sonnet-latest"
    anthropic_metadata_model: str = "claude-3-7-sonnet-latest"
    ai_embedding_timeout_seconds: int = 30
    chat_response_timeout_seconds: int = 45
    document_metadata_ai_enabled: bool = False
    document_metadata_web_search_enabled: bool = False
    document_metadata_timeout_seconds: int = 45
    legal_structure_ai_fallback_enabled: bool = False
    legal_structure_ai_fallback_threshold: float = 60.0
    graph_backend: str = "relational"
    neo4j_uri: str | None = None
    neo4j_user: str | None = Field(default=None, validation_alias=AliasChoices("NEO4J_USER", "NEO4J_USERNAME"))
    neo4j_password: str | None = None
    neo4j_database: str = "neo4j"
    neo4j_sync_enabled: bool = False
    neo4j_trust_all_certificates: bool = False

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return False

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use PostgreSQL. SQLite and SQL Server are no longer supported in this project.")
        return normalized

    @field_validator("ai_embedding_enabled", "ai_chat_enabled", mode="before")
    @classmethod
    def normalize_ai_boolean_enabled(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
        return False

    @field_validator("document_metadata_ai_enabled", "document_metadata_web_search_enabled", "legal_structure_ai_fallback_enabled", "neo4j_sync_enabled", "neo4j_trust_all_certificates", mode="before")
    @classmethod
    def normalize_document_metadata_toggle(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
        return False

    @field_validator("metadata_ai_provider", "chatbot_ai_provider", mode="before")
    @classmethod
    def normalize_ai_provider(cls, value: str) -> str:
        normalized = str(value or "openai").strip().lower()
        if normalized not in {"openai", "anthropic"}:
            return "openai"
        return normalized

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def normalize_embedding_provider(cls, value: str) -> str:
        normalized = str(value or "local").strip().lower()
        if normalized not in {"local", "openai"}:
            return "local"
        return normalized

    @field_validator("graph_backend", mode="before")
    @classmethod
    def normalize_graph_backend(cls, value: str) -> str:
        normalized = str(value or "relational").strip().lower()
        if normalized not in {"relational", "neo4j"}:
            return "relational"
        return normalized

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def legal_sources_dir(self) -> Path:
        return self.project_root / "docs" / "legal_sources"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
