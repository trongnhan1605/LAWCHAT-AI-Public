from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_relation import DocumentRelation
from src.tools.search_law import SearchLawResult


@dataclass(frozen=True)
class RelatedArticleResult:
    document_id: int
    chunk_id: int
    document_title: str
    citation_label: str | None
    relation_type: str
    source_reference: str | None
    excerpt: str

    def to_dict(self) -> dict:
        return asdict(self)


def get_related_articles(db: Session, search_results: list[SearchLawResult], *, limit: int = 4) -> list[RelatedArticleResult]:
    if not search_results:
        return []

    source_results = search_results[:2]
    source_chunk_ids = {item.chunk_id for item in source_results}
    source_document_ids = {item.document_id for item in source_results}

    source_chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(source_chunk_ids)).all()
    source_chunk_map = {chunk.id: chunk for chunk in source_chunks}
    documents = db.query(Document).filter(Document.id.in_(source_document_ids)).all()
    document_map = {document.id: document for document in documents}

    related_results: list[RelatedArticleResult] = []
    seen_pairs: set[tuple[int, int]] = set()

    for result in source_results:
        source_chunk = source_chunk_map.get(result.chunk_id)
        if source_chunk is None:
            continue

        candidate_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == result.document_id)
            .filter(DocumentChunk.id != result.chunk_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

        for chunk in candidate_chunks:
            same_article = bool(source_chunk.article_number and chunk.article_number == source_chunk.article_number)
            nearby_chunk = abs(chunk.chunk_index - source_chunk.chunk_index) <= 1
            if not same_article and not nearby_chunk:
                continue
            pair = (chunk.document_id, chunk.id)
            if pair in seen_pairs:
                continue
            document = document_map.get(chunk.document_id) or db.query(Document).filter(Document.id == chunk.document_id).first()
            if document is None:
                continue
            seen_pairs.add(pair)
            related_results.append(
                RelatedArticleResult(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    document_title=document.title,
                    citation_label=chunk.citation_label,
                    relation_type="same_document_context",
                    source_reference=document.source_reference,
                    excerpt=(" ".join(chunk.content.split())[:320]).rstrip() + ("..." if len(" ".join(chunk.content.split())) > 320 else ""),
                )
            )
            if len(related_results) >= limit:
                return related_results

    relations = (
        db.query(DocumentRelation)
        .filter(DocumentRelation.source_document_id.in_(source_document_ids))
        .filter(DocumentRelation.is_active == True)
        .order_by(DocumentRelation.updated_at.desc(), DocumentRelation.id.desc())
        .all()
    )
    for relation in relations:
        target_document = db.query(Document).filter(Document.id == relation.target_document_id).first()
        target_chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == relation.target_document_id)
            .order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
            .first()
        )
        if target_document is None or target_chunk is None:
            continue
        pair = (target_document.id, target_chunk.id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        compact_excerpt = " ".join(target_chunk.content.split())
        related_results.append(
            RelatedArticleResult(
                document_id=target_document.id,
                chunk_id=target_chunk.id,
                document_title=target_document.title,
                citation_label=target_chunk.citation_label,
                relation_type=relation.relation_type,
                source_reference=target_document.source_reference,
                excerpt=compact_excerpt[:320].rstrip() + ("..." if len(compact_excerpt) > 320 else ""),
            )
        )
        if len(related_results) >= limit:
            break

    return related_results