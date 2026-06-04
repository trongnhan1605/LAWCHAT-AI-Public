from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.services.knowledge_service import knowledge_service


@dataclass(slots=True)
class BenchmarkDimension:
    name: str
    score: float
    details: str


class DocumentBenchmarkService:
    def benchmark_document(self, db: Session, document_id: int) -> dict:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError("Document not found for benchmark")

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        metadata_score = self._score_metadata(document)
        chunk_score = self._score_chunk_structure(chunks)
        retrieval_score, retrieval_checks = self._score_retrieval(db, document, chunks)
        review_score = self._score_review_readiness(document)
        overall_score = round(((metadata_score.score * 0.3) + (chunk_score.score * 0.2) + (retrieval_score.score * 0.35) + (review_score.score * 0.15)), 3)

        return {
            "document_id": document_id,
            "overall_score": overall_score,
            "dimensions": [
                {"name": metadata_score.name, "score": metadata_score.score, "details": metadata_score.details},
                {"name": chunk_score.name, "score": chunk_score.score, "details": chunk_score.details},
                {"name": retrieval_score.name, "score": retrieval_score.score, "details": retrieval_score.details},
                {"name": review_score.name, "score": review_score.score, "details": review_score.details},
            ],
            "retrieval_checks": retrieval_checks,
        }

    def _score_metadata(self, document: Document) -> BenchmarkDimension:
        important_fields = [
            document.title,
            document.legal_domain,
            document.document_type,
            document.document_code,
            document.issuing_authority,
            document.authority_level,
            document.signed_date,
            document.effective_date,
            document.legal_status,
            document.summary,
        ]
        completed = sum(1 for item in important_fields if item not in (None, ""))
        score = round(completed / len(important_fields), 3)
        return BenchmarkDimension("metadata_completeness", score, f"{completed}/{len(important_fields)} key metadata fields are populated.")

    def _score_chunk_structure(self, chunks: list[DocumentChunk]) -> BenchmarkDimension:
        if not chunks:
            return BenchmarkDimension("chunk_structure", 0.0, "No chunks available for this document.")
        legal_chunks = sum(1 for chunk in chunks if chunk.chunk_type in {"article", "clause", "point"})
        avg_chars = sum(chunk.char_count or 0 for chunk in chunks) / max(len(chunks), 1)
        structure_ratio = legal_chunks / len(chunks)
        avg_chars_score = min(avg_chars / 420, 1.0)
        score = round((structure_ratio * 0.7) + (avg_chars_score * 0.3), 3)
        return BenchmarkDimension("chunk_structure", score, f"{legal_chunks}/{len(chunks)} chunks preserve legal structure; average chunk length is {round(avg_chars, 1)} chars.")

    def _score_retrieval(self, db: Session, document: Document, chunks: list[DocumentChunk]) -> tuple[BenchmarkDimension, list[dict]]:
        checks: list[dict] = []
        passed = 0
        queries: list[tuple[str, str]] = []
        if document.document_code:
            queries.append((document.document_code, "document_code"))
        if document.title:
            queries.append((document.title, "title"))
        for chunk in chunks:
            if chunk.citation_label:
                queries.append((chunk.citation_label, "citation_label"))
            if len(queries) >= 5:
                break

        for query, query_type in queries:
            results = knowledge_service.search_chunks(db, query, limit=5, preferred_terms=[document.document_code] if document.document_code else None)
            matched = any(found_document.id == document.id for found_document, _, _ in results)
            if matched:
                passed += 1
            checks.append({"query": query, "query_type": query_type, "passed": matched, "top_hit_document_ids": [found_document.id for found_document, _, _ in results]})

        score = round(passed / len(checks), 3) if checks else 0.0
        return BenchmarkDimension("retrieval_accuracy", score, f"{passed}/{len(checks)} synthetic retrieval checks returned the target document.") , checks

    def _score_review_readiness(self, document: Document) -> BenchmarkDimension:
        metadata_score = 1.0 if document.metadata_review_status == "reviewed" else 0.45
        relation_score = 1.0 if document.relation_sync_status in {"synced", "no_matches"} else (0.4 if document.relation_sync_status == "pending" else 0.1)
        score = round((metadata_score * 0.65) + (relation_score * 0.35), 3)
        return BenchmarkDimension(
            "review_readiness",
            score,
            f"Metadata review is '{document.metadata_review_status}' and relation sync is '{document.relation_sync_status}'.",
        )


document_benchmark_service = DocumentBenchmarkService()