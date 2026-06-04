from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.config import settings
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.schemas.knowledge_schema import BulkIngestionPayload, BulkIngestionResponse, CategoryItem, CategoryListResponse, ChunkListResponse, DocumentBenchmarkPayload, DocumentBenchmarkResponse, DocumentChunkItem, DocumentGraphPayload, DocumentGraphResponse, DocumentItem, DocumentListResponse, ExtractionDiagnosticPayload, ExtractionDiagnosticResponse, IngestDocumentRequest, IngestionPayload, IngestionResponse, KnowledgeOverviewPayload, KnowledgeOverviewResponse, LegalConceptItem, LegalConceptListResponse, LegalProvisionItem, ProvisionListResponse, ProvisionRelationItem, ProvisionRelationListResponse, RelationOntologyItem, RelationOntologyResponse, RetrievalPreviewItem, RetrievalPreviewResponse, SemanticGraphPayload, SemanticGraphResponse, SemanticQueryPayload, SemanticQueryResponse
from src.services.document_benchmark_service import document_benchmark_service
from src.services.graph_backend_service import graph_backend_service
from src.services.knowledge_service import knowledge_service
from src.services.legal_ontology_service import legal_ontology_service
from src.services.legal_semantic_graph_service import legal_semantic_graph_service
from src.services.provision_relation_service import provision_relation_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/categories", response_model=CategoryListResponse)
def list_categories(db: Session = Depends(get_db)) -> CategoryListResponse:
    categories = [CategoryItem.model_validate(item) for item in knowledge_service.list_categories(db)]
    return CategoryListResponse(success=True, message="Categories fetched", data=categories)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    documents = [_serialize_document(db, item) for item in knowledge_service.list_documents(db)]
    return DocumentListResponse(success=True, message="Documents fetched", data=documents)


@router.get("/overview", response_model=KnowledgeOverviewResponse)
def overview(db: Session = Depends(get_db)) -> KnowledgeOverviewResponse:
    documents = knowledge_service.list_documents(db)
    document_metrics = _build_document_metrics(db, [item.id for item in documents])
    payload = KnowledgeOverviewPayload(
        categories=[CategoryItem.model_validate(item) for item in knowledge_service.list_categories(db)],
        documents=[_serialize_document(item, document_metrics.get(item.id)) for item in documents],
    )
    return KnowledgeOverviewResponse(success=True, message="Knowledge overview fetched", data=payload)


@router.get("/ontology", response_model=RelationOntologyResponse)
def relation_ontology() -> RelationOntologyResponse:
    payload = [RelationOntologyItem.model_validate(item) for item in legal_ontology_service.get_taxonomy_snapshot()]
    return RelationOntologyResponse(success=True, message="Legal ontology fetched", data=payload)


@router.get("/concepts", response_model=LegalConceptListResponse)
def list_legal_concepts(db: Session = Depends(get_db)) -> LegalConceptListResponse:
    payload = [LegalConceptItem.model_validate(item) for item in legal_semantic_graph_service.list_concepts(db)]
    return LegalConceptListResponse(success=True, message="Legal concepts fetched", data=payload)


@router.get("/concepts/{concept_id}/graph", response_model=SemanticGraphResponse)
def concept_graph(concept_id: int, depth: int = Query(default=2, ge=1, le=4), db: Session = Depends(get_db)) -> SemanticGraphResponse:
    payload = SemanticGraphPayload.model_validate(graph_backend_service.get_concept_graph(db, concept_id, depth=depth))
    return SemanticGraphResponse(success=True, message="Semantic concept graph fetched", data=payload)


@router.get("/semantic-query", response_model=SemanticQueryResponse)
def semantic_query(query: str = Query(min_length=2), depth: int = Query(default=2, ge=1, le=4), db: Session = Depends(get_db)) -> SemanticQueryResponse:
    payload = SemanticQueryPayload.model_validate(graph_backend_service.explain_query(db, query, depth=depth))
    return SemanticQueryResponse(success=True, message="Semantic query graph fetched", data=payload)


@router.post("/documents/{document_id}/ingest", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_document(document_id: int, payload: IngestDocumentRequest | None = None, db: Session = Depends(get_db)) -> IngestionResponse:
    document, extracted_characters, chunk_count = knowledge_service.ingest_document(
        db,
        document_id,
        extracted_text_override=payload.extracted_text_override if payload else None,
    )
    payload = IngestionPayload(
        document=_serialize_document(db, document),
        extracted_characters=extracted_characters,
        chunk_count=chunk_count,
    )
    return IngestionResponse(success=True, message="Document ingested", data=payload)


@router.post("/documents/reingest", response_model=BulkIngestionResponse, status_code=status.HTTP_201_CREATED)
def reingest_documents(db: Session = Depends(get_db)) -> BulkIngestionResponse:
    payload = BulkIngestionPayload.model_validate(knowledge_service.ingest_all_documents(db))
    return BulkIngestionResponse(success=True, message="Documents re-ingested", data=payload)


@router.post("/documents/{document_id}/refresh-structure", response_model=IngestionResponse)
def refresh_document_structure(document_id: int, db: Session = Depends(get_db)) -> IngestionResponse:
    document = knowledge_service.refresh_document_metadata_and_relations(db, document_id)
    metrics = _build_document_metrics(db, [document.id]).get(document.id)
    payload = IngestionPayload(
        document=_serialize_document(document, metrics),
        extracted_characters=0,
        chunk_count=int((metrics or {}).get("chunk_count", 0)),
    )
    return IngestionResponse(success=True, message="Document structure refreshed", data=payload)


@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
def list_chunks(document_id: int, db: Session = Depends(get_db)) -> ChunkListResponse:
    chunks = [DocumentChunkItem.model_validate(item) for item in knowledge_service.list_chunks(db, document_id)]
    return ChunkListResponse(success=True, message="Document chunks fetched", data=chunks)


@router.get("/documents/{document_id}/provisions", response_model=ProvisionListResponse)
def list_provisions(document_id: int, db: Session = Depends(get_db)) -> ProvisionListResponse:
    provisions = [LegalProvisionItem.model_validate(item) for item in knowledge_service.list_provisions(db, document_id)]
    return ProvisionListResponse(success=True, message="Document provisions fetched", data=provisions)


@router.get("/documents/{document_id}/provision-relations", response_model=ProvisionRelationListResponse)
def list_provision_relations(document_id: int, db: Session = Depends(get_db)) -> ProvisionRelationListResponse:
    relations = [ProvisionRelationItem.model_validate(item) for item in provision_relation_service.list_document_relations(db, document_id)]
    return ProvisionRelationListResponse(success=True, message="Document provision relations fetched", data=relations)


@router.get("/documents/{document_id}/retrieval-preview", response_model=RetrievalPreviewResponse)
def retrieval_preview(document_id: int, query: str = Query(min_length=2), db: Session = Depends(get_db)) -> RetrievalPreviewResponse:
    items = [
        RetrievalPreviewItem(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            score=score,
            section_title=chunk.section_title,
            content_preview=chunk.content[:260],
        )
        for chunk, score in knowledge_service.retrieval_preview(db, document_id, query)
    ]
    return RetrievalPreviewResponse(success=True, message="Retrieval preview fetched", data=items)


@router.get("/documents/{document_id}/diagnostics", response_model=ExtractionDiagnosticResponse)
def diagnostics(document_id: int, db: Session = Depends(get_db)) -> ExtractionDiagnosticResponse:
    payload = ExtractionDiagnosticPayload.model_validate(knowledge_service.diagnose_document(db, document_id))
    return ExtractionDiagnosticResponse(success=True, message="Document diagnostics fetched", data=payload)


@router.get("/documents/{document_id}/benchmark", response_model=DocumentBenchmarkResponse)
def benchmark(document_id: int, db: Session = Depends(get_db)) -> DocumentBenchmarkResponse:
    payload = DocumentBenchmarkPayload.model_validate(document_benchmark_service.benchmark_document(db, document_id))
    return DocumentBenchmarkResponse(success=True, message="Document benchmark fetched", data=payload)


@router.get("/documents/{document_id}/graph", response_model=DocumentGraphResponse)
def document_graph(document_id: int, depth: int = Query(default=1, ge=1, le=3), db: Session = Depends(get_db)) -> DocumentGraphResponse:
    payload = DocumentGraphPayload.model_validate(graph_backend_service.get_document_graph(db, document_id, depth=depth))
    return DocumentGraphResponse(success=True, message="Document graph fetched", data=payload)


def _build_document_metrics(db: Session, document_ids: list[int]) -> dict[int, dict[str, int | str]]:
    if not document_ids:
        return {}

    chunk_counts = {
        int(document_id): int(count or 0)
        for document_id, count in (
            db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
            .filter(DocumentChunk.document_id.in_(document_ids))
            .group_by(DocumentChunk.document_id)
            .all()
        )
    }
    relation_counts = {
        int(document_id): int(count or 0)
        for document_id, count in (
            db.query(DocumentRelation.source_document_id, func.count(DocumentRelation.id))
            .filter(DocumentRelation.source_document_id.in_(document_ids))
            .group_by(DocumentRelation.source_document_id)
            .all()
        )
    }
    vector_rows = (
        db.query(
            DocumentChunk.document_id,
            func.sum(case((DocumentChunkVector.embedding_status == "indexed", 1), else_=0)).label("indexed_count"),
            func.sum(case((DocumentChunkVector.embedding_status == "failed", 1), else_=0)).label("failed_count"),
        )
        .join(DocumentChunkVector, DocumentChunkVector.chunk_id == DocumentChunk.id)
        .filter(DocumentChunk.document_id.in_(document_ids))
        .group_by(DocumentChunk.document_id)
        .all()
    )
    vector_counts = {
        int(document_id): {
            "indexed_count": int(indexed_count or 0),
            "failed_count": int(failed_count or 0),
        }
        for document_id, indexed_count, failed_count in vector_rows
    }

    embedding_enabled = settings.ai_embedding_enabled and (settings.embedding_provider == "local" or bool(settings.openai_api_key))
    metrics: dict[int, dict[str, int | str]] = {}
    for document_id in document_ids:
        chunk_count = chunk_counts.get(document_id, 0)
        indexed_count = int(vector_counts.get(document_id, {}).get("indexed_count", 0))
        failed_count = int(vector_counts.get(document_id, {}).get("failed_count", 0))
        if chunk_count == 0:
            embedding_status = "not_indexed"
        elif indexed_count == chunk_count:
            embedding_status = "indexed"
        elif failed_count > 0 and indexed_count > 0:
            embedding_status = "partial"
        elif failed_count > 0:
            embedding_status = "failed"
        elif embedding_enabled:
            embedding_status = "pending"
        else:
            embedding_status = "disabled"

        metrics[document_id] = {
            "chunk_count": chunk_count,
            "embedded_chunk_count": indexed_count,
            "relation_count": relation_counts.get(document_id, 0),
            "embedding_status": embedding_status,
        }
    return metrics


def _serialize_document(item, metrics: dict[str, int | str] | None = None) -> DocumentItem:
    resolved_metrics = metrics or {}
    return DocumentItem.model_validate({
        "id": item.id,
        "title": item.title,
        "file_name": item.file_name,
        "source_type": item.source_type,
        "legal_domain": item.legal_domain,
        "authority_level": item.authority_level,
        "issuing_authority": item.issuing_authority,
        "document_code": item.document_code,
        "document_type": item.document_type,
        "normative_level": item.normative_level,
        "signed_date": item.signed_date,
        "source_reference": item.source_reference,
        "storage_path": item.storage_path,
        "summary": item.summary,
        "effective_date": item.effective_date,
        "expiry_date": item.expiry_date,
        "legal_status": item.legal_status,
        "metadata_review_status": item.metadata_review_status,
        "metadata_review_notes": item.metadata_review_notes,
        "metadata_last_reviewed_at": item.metadata_last_reviewed_at,
        "content_sha256": item.content_sha256,
        "source_identity": item.source_identity,
        "ingestion_quality_status": item.ingestion_quality_status,
        "ingestion_quality_notes": item.ingestion_quality_notes,
        "retrieval_visibility": item.retrieval_visibility,
        "ocr_quality_score": float(item.ocr_quality_score) if item.ocr_quality_score is not None else None,
        "ocr_quality_label": item.ocr_quality_label,
        "relation_sync_status": item.relation_sync_status,
        "relation_sync_details": item.relation_sync_details,
        "relation_count": int(resolved_metrics.get("relation_count", 0)),
        "is_seed": item.is_seed,
        "is_active": item.is_active,
        "chunk_count": int(resolved_metrics.get("chunk_count", 0)),
        "embedded_chunk_count": int(resolved_metrics.get("embedded_chunk_count", 0)),
        "embedding_status": str(resolved_metrics.get("embedding_status", "not_indexed")),
    })
