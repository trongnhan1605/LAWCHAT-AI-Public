from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.core.exceptions import ValidationException
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.services.embedding_service import embedding_service

MAX_LEXICAL_PREFILTER_ROWS = 5000
SEARCHABLE_RETRIEVAL_VISIBILITY = {"indexed_verified", "indexed_unreviewed"}
VERIFIED_RETRIEVAL_VISIBILITY = {"indexed_verified"}


@dataclass(frozen=True)
class ChunkRankingCallbacks:
    tokenize: Callable[[str], list[str]]
    extract_query_references: Callable[[str], dict[str, str | None]]
    build_scoring_text: Callable[[DocumentChunk], str]
    score_chunk: Callable[[str, list[str], list[str], int], int]
    score_semantic_similarity: Callable[[list[float] | None, str | None], float]
    score_legal_reference_match: Callable[[DocumentChunk, dict[str, str | None]], float]
    score_exact_citation_phrase: Callable[[DocumentChunk, str], float]
    document_priority_boost: Callable[[Document], int]


class HybridChunkRanker:
    def rank_chunks(
        self,
        db: Session,
        query: str,
        *,
        limit: int,
        preferred_terms: list[str] | None = None,
        document_id: int | None = None,
        legal_domain: str | None = None,
        allow_unreviewed: bool = True,
        callbacks: ChunkRankingCallbacks,
    ) -> list[tuple[Document, DocumentChunk, int]]:
        tokens = callbacks.tokenize(query)
        if not tokens:
            raise ValidationException("Query is too short for retrieval")

        preferred_terms = preferred_terms or []
        query_vector = embedding_service.embed_query(query, preferred_terms)
        query_references = callbacks.extract_query_references(query)
        allowed_visibility = SEARCHABLE_RETRIEVAL_VISIBILITY if allow_unreviewed else VERIFIED_RETRIEVAL_VISIBILITY

        if query_vector:
            rows_query = (
                db.query(DocumentChunk, Document, DocumentChunkVector)
                .join(Document, Document.id == DocumentChunk.document_id)
                .outerjoin(DocumentChunkVector, DocumentChunkVector.chunk_id == DocumentChunk.id)
                .filter(Document.is_active == True)
                .filter(Document.retrieval_visibility.in_(allowed_visibility))
            )
        else:
            rows_query = (
                db.query(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .filter(Document.is_active == True)
                .filter(Document.retrieval_visibility.in_(allowed_visibility))
            )
        if document_id is not None:
            rows_query = rows_query.filter(DocumentChunk.document_id == document_id)
        if legal_domain:
            rows_query = rows_query.filter(Document.legal_domain == legal_domain)

        lexical_prefilter = self._build_lexical_prefilter(tokens, preferred_terms)
        candidate_limit = None
        if lexical_prefilter is not None:
            rows_query = rows_query.filter(lexical_prefilter)
            candidate_limit = MAX_LEXICAL_PREFILTER_ROWS

        rows_query = rows_query.order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
        if candidate_limit is not None:
            rows_query = rows_query.limit(candidate_limit)
        rows = rows_query.all()
        if not rows and lexical_prefilter is not None:
            fallback_query = (
                db.query(DocumentChunk, Document, DocumentChunkVector)
                .join(Document, Document.id == DocumentChunk.document_id)
                .outerjoin(DocumentChunkVector, DocumentChunkVector.chunk_id == DocumentChunk.id)
                .filter(Document.is_active == True)
                .filter(Document.retrieval_visibility.in_(allowed_visibility))
            ) if query_vector else (
                db.query(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .filter(Document.is_active == True)
                .filter(Document.retrieval_visibility.in_(allowed_visibility))
            )
            if document_id is not None:
                fallback_query = fallback_query.filter(DocumentChunk.document_id == document_id)
            if legal_domain:
                fallback_query = fallback_query.filter(Document.legal_domain == legal_domain)
            rows = fallback_query.order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc()).all()

        candidates: list[dict[str, object]] = []
        max_lexical_score = 0
        max_semantic_score = 0.0

        for row in rows:
            chunk = row[0]
            document = row[1]
            vector_row = row[2] if query_vector and len(row) > 2 else None
            if vector_row and (
                vector_row.embedding_status != "indexed"
                or vector_row.provider != embedding_service.active_provider()
                or vector_row.embedding_model != embedding_service.active_model()
            ):
                vector_row = None
            lexical_score = callbacks.score_chunk(callbacks.build_scoring_text(chunk), tokens, preferred_terms, chunk.chunk_index)
            semantic_score = callbacks.score_semantic_similarity(query_vector, vector_row.embedding_json if vector_row else None)
            reference_bonus = callbacks.score_legal_reference_match(chunk, query_references)
            exact_citation_bonus = callbacks.score_exact_citation_phrase(chunk, query)

            if lexical_score <= 0 and semantic_score < 0.18 and reference_bonus <= 0 and exact_citation_bonus <= 0:
                continue

            max_lexical_score = max(max_lexical_score, lexical_score)
            max_semantic_score = max(max_semantic_score, semantic_score)
            candidates.append(
                {
                    "document": document,
                    "chunk": chunk,
                    "lexical_score": lexical_score,
                    "semantic_score": semantic_score,
                    "reference_bonus": reference_bonus,
                    "exact_citation_bonus": exact_citation_bonus,
                    "document_boost": callbacks.document_priority_boost(document),
                }
            )

        ranked: list[tuple[Document, DocumentChunk, int]] = []
        for candidate in candidates:
            lexical_norm = (int(candidate["lexical_score"]) / max_lexical_score) if max_lexical_score > 0 else 0.0
            semantic_norm = (float(candidate["semantic_score"]) / max_semantic_score) if max_semantic_score > 0 else 0.0
            document_norm = max(-0.12, min(0.12, int(candidate["document_boost"]) / 100))
            hybrid_score = (
                (lexical_norm * 0.46)
                + (semantic_norm * 0.36)
                + float(candidate["reference_bonus"])
                + float(candidate["exact_citation_bonus"])
                + document_norm
            )
            ranked.append(
                (
                    candidate["document"],
                    candidate["chunk"],
                    max(0, int(round(hybrid_score * 100))),
                )
            )

        ranked.sort(key=lambda item: (item[2], -item[1].char_count, -item[1].chunk_index), reverse=True)
        return ranked[:limit]

    def _build_lexical_prefilter(self, tokens: list[str], preferred_terms: list[str]):
        filter_terms = [term for term in [*tokens[:8], *preferred_terms[:4]] if len(term) >= 3]
        if not filter_terms:
            return None
        clauses = []
        for term in filter_terms:
            pattern = f"%{term}%"
            clauses.extend([
                DocumentChunk.retrieval_text.ilike(pattern),
                DocumentChunk.content.ilike(pattern),
                DocumentChunk.section_title.ilike(pattern),
            ])
        return or_(*clauses)


hybrid_chunk_ranker = HybridChunkRanker()
