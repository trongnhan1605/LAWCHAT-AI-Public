import json
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging import logger
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.services.ai_usage_service import ai_usage_service


@dataclass
class EmbeddingIndexResult:
    indexed_count: int
    failed_count: int
    status: str


class EmbeddingService:
    PROVIDER = "openai"
    LOCAL_PROVIDER = "local"
    _local_model = None
    _local_model_name: str | None = None

    def is_enabled(self) -> bool:
        if not settings.ai_embedding_enabled:
            return False
        if settings.embedding_provider == self.LOCAL_PROVIDER:
            return True
        return bool(settings.openai_api_key)

    def active_provider(self) -> str:
        return self.LOCAL_PROVIDER if settings.embedding_provider == self.LOCAL_PROVIDER else self.PROVIDER

    def active_model(self) -> str:
        return settings.local_embedding_model if self.active_provider() == self.LOCAL_PROVIDER else settings.openai_embedding_model

    def index_document_chunks(self, db: Session, chunks: list[DocumentChunk]) -> EmbeddingIndexResult:
        if not chunks:
            return EmbeddingIndexResult(indexed_count=0, failed_count=0, status="not_indexed")

        if not self.is_enabled():
            return EmbeddingIndexResult(indexed_count=0, failed_count=0, status="disabled")

        indexed_count = 0
        failed_count = 0
        batch_size = max(1, int(settings.local_embedding_batch_size or 32)) if self.active_provider() == self.LOCAL_PROVIDER else 128
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            try:
                embedding_texts = [self._build_embedding_text(chunk) for chunk in batch]
                embeddings, payload = self._embed_texts(embedding_texts, input_type="passage")
                self._persist_embeddings(db, batch, embeddings)
                indexed_count += len(batch)
                ai_usage_service.log_request(
                    request_type="embedding",
                    endpoint="local" if self.active_provider() == self.LOCAL_PROVIDER else "embeddings",
                    provider=self.active_provider(),
                    model=self.active_model(),
                    document_id=batch[0].document_id if batch else None,
                    chunk_count=len(batch),
                    payload=payload,
                    status="success",
                )
            except Exception as exc:  # pragma: no cover - defensive guard around external/local model
                logger.warning("Embedding generation failed for %s chunks: %s", len(batch), exc)
                self._mark_failed(db, batch, str(exc))
                failed_count += len(batch)
                ai_usage_service.log_request(
                    request_type="embedding",
                    endpoint="local" if self.active_provider() == self.LOCAL_PROVIDER else "embeddings",
                    provider=self.active_provider(),
                    model=self.active_model(),
                    document_id=batch[0].document_id if batch else None,
                    document_title_snapshot=None,
                    file_name_snapshot=None,
                    storage_path_snapshot=None,
                    chunk_count=len(batch),
                    status="failed",
                    error_message=str(exc),
                )

        if indexed_count and failed_count:
            return EmbeddingIndexResult(indexed_count=indexed_count, failed_count=failed_count, status="partial")
        if failed_count:
            return EmbeddingIndexResult(indexed_count=0, failed_count=failed_count, status="failed")
        return EmbeddingIndexResult(indexed_count=indexed_count, failed_count=0, status="indexed")

    def embed_query(self, query: str, preferred_terms: list[str] | None = None) -> list[float] | None:
        if not self.is_enabled():
            return None

        query_text = self._build_query_embedding_text(query, preferred_terms or [])
        try:
            embeddings, payload = self._embed_texts([query_text], input_type="query")
        except Exception as exc:  # pragma: no cover - defensive guard around external API
            logger.warning("Query embedding generation failed: %s", exc)
            ai_usage_service.log_request(
                request_type="embedding",
                endpoint="embeddings",
                provider=self.active_provider(),
                model=self.active_model(),
                chunk_count=1,
                status="failed",
                error_message=str(exc),
            )
            return None

        ai_usage_service.log_request(
            request_type="embedding",
            endpoint="embeddings",
            provider=self.active_provider(),
            model=self.active_model(),
            chunk_count=1,
            payload=payload,
            status="success",
        )
        return embeddings[0] if embeddings else None

    def _build_embedding_text(self, chunk: DocumentChunk) -> str:
        metadata = self._parse_chunk_metadata(chunk)
        parent_context = metadata.get("parent_context") if isinstance(metadata.get("parent_context"), dict) else {}

        context_lines = [
            f"[Ten van ban: {metadata.get('title') or parent_context.get('document_title') or 'Khong ro'}]",
            f"[So hieu: {metadata.get('document_code') or 'Khong ro'}]",
            f"[Linh vuc: {metadata.get('legal_domain') or 'Khong ro'}]",
            f"[Loai van ban: {metadata.get('document_type') or 'Khong ro'}]",
            f"[Muc: {metadata.get('section') or parent_context.get('section') or parent_context.get('chapter') or parent_context.get('part') or 'Khong ro'}]",
            f"[Tieu muc: {metadata.get('subsection') or parent_context.get('point_heading') or parent_context.get('clause_heading') or 'Khong ro'}]",
            f"[Dieu: {metadata.get('article_ref') or parent_context.get('article_heading') or 'Khong ro'}]",
            f"[Trich dan: {chunk.citation_label or 'Khong ro'}]",
            "[Noi dung]",
            chunk.content,
        ]
        return "\n".join(context_lines)

    def _build_query_embedding_text(self, query: str, preferred_terms: list[str]) -> str:
        hint_text = ", ".join(term for term in preferred_terms if term)
        context_lines = [
            "[Loai truy van: legal_research_query]",
            f"[Tu khoa uu tien: {hint_text or 'Khong co'}]",
            "[Cau hoi]",
            query.strip(),
        ]
        return "\n".join(context_lines)

    def _parse_chunk_metadata(self, chunk: DocumentChunk) -> dict:
        if not chunk.metadata_json:
            return {}
        try:
            parsed = json.loads(chunk.metadata_json)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _embed_texts(self, texts: list[str], *, input_type: str) -> tuple[list[list[float]], dict]:
        if self.active_provider() == self.LOCAL_PROVIDER:
            return self._embed_texts_locally(texts, input_type=input_type)
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_embedding_model,
                "input": texts,
            },
            timeout=settings.ai_embedding_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or []
        return [item.get("embedding") or [] for item in data], payload

    def _embed_texts_locally(self, texts: list[str], *, input_type: str) -> tuple[list[list[float]], dict]:
        model = self._load_local_model()
        prefixed_texts = [self._prefix_local_text(text, input_type=input_type) for text in texts]
        vectors = model.encode(
            prefixed_texts,
            batch_size=max(1, int(settings.local_embedding_batch_size or 32)),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = [vector.astype(float).tolist() if hasattr(vector, "astype") else list(vector) for vector in vectors]
        return embeddings, {"provider": self.LOCAL_PROVIDER, "model": settings.local_embedding_model, "input_count": len(texts)}

    def _load_local_model(self):
        if self._local_model is not None and self._local_model_name == settings.local_embedding_model:
            return self._local_model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Local embeddings require `sentence-transformers`. Install backend requirements in a Python 3.11/3.12 environment.") from exc
        self._local_model = SentenceTransformer(settings.local_embedding_model, device=settings.local_embedding_device)
        self._local_model_name = settings.local_embedding_model
        return self._local_model

    def _prefix_local_text(self, text: str, *, input_type: str) -> str:
        if settings.local_embedding_model.startswith("intfloat/multilingual-e5"):
            prefix = "query" if input_type == "query" else "passage"
            return f"{prefix}: {text}"
        return text

    def _persist_embeddings(self, db: Session, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        indexed_at = datetime.now(timezone.utc)
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            vector_row = db.query(DocumentChunkVector).filter(DocumentChunkVector.chunk_id == chunk.id).first()
            if vector_row is None:
                vector_row = DocumentChunkVector(
                    chunk_id=chunk.id,
                    provider=self.active_provider(),
                    embedding_model=self.active_model(),
                    embedding_status="indexed",
                )
                db.add(vector_row)

            vector_row.provider = self.active_provider()
            vector_row.embedding_model = self.active_model()
            vector_row.embedding_dimensions = len(embedding)
            vector_row.embedding_status = "indexed"
            vector_row.embedding_json = json.dumps(embedding)
            vector_row.error_message = None
            vector_row.indexed_at = indexed_at

        db.flush()

    def _mark_failed(self, db: Session, chunks: list[DocumentChunk], error_message: str) -> None:
        for chunk in chunks:
            vector_row = db.query(DocumentChunkVector).filter(DocumentChunkVector.chunk_id == chunk.id).first()
            if vector_row is None:
                vector_row = DocumentChunkVector(
                    chunk_id=chunk.id,
                    provider=self.active_provider(),
                    embedding_model=self.active_model(),
                    embedding_status="failed",
                )
                db.add(vector_row)

            vector_row.provider = self.active_provider()
            vector_row.embedding_model = self.active_model()
            vector_row.embedding_dimensions = None
            vector_row.embedding_status = "failed"
            vector_row.embedding_json = None
            vector_row.error_message = error_message[:4000]
            vector_row.indexed_at = None


embedding_service = EmbeddingService()
