from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.knowledge_service import knowledge_service


class LegalRetrievalService:
    def search_chunks(
        self,
        db: Session,
        query: str,
        *,
        limit: int = 5,
        preferred_terms: list[str] | None = None,
        legal_domain: str | None = None,
        allow_unreviewed: bool = False,
    ) -> list[tuple[Document, DocumentChunk, int]]:
        return knowledge_service.search_chunks(db, query, limit=limit, preferred_terms=preferred_terms, legal_domain=legal_domain, allow_unreviewed=allow_unreviewed)

    def preview_document_retrieval(
        self,
        db: Session,
        *,
        document_id: int,
        query: str,
        limit: int = 5,
        allow_unreviewed: bool = True,
    ) -> list[tuple[DocumentChunk, int]]:
        return knowledge_service.retrieval_preview(db, document_id, query, limit=limit, allow_unreviewed=allow_unreviewed)


legal_retrieval_service = LegalRetrievalService()
