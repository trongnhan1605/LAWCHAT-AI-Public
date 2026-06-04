from datetime import date, datetime

from pydantic import BaseModel

from src.schemas.base import BaseResponse


class CategoryItem(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class DocumentItem(BaseModel):
    id: int
    title: str
    file_name: str
    source_type: str
    legal_domain: str
    authority_level: str | None = None
    issuing_authority: str | None = None
    document_code: str | None = None
    document_type: str | None = None
    normative_level: int | None = None
    signed_date: date | None = None
    source_reference: str | None = None
    storage_path: str | None = None
    summary: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    legal_status: str | None = None
    metadata_review_status: str = "pending_review"
    metadata_review_notes: str | None = None
    metadata_last_reviewed_at: datetime | None = None
    content_sha256: str | None = None
    source_identity: str | None = None
    ingestion_quality_status: str = "pending"
    ingestion_quality_notes: str | None = None
    retrieval_visibility: str = "indexed_unreviewed"
    ocr_quality_score: float | None = None
    ocr_quality_label: str | None = None
    relation_sync_status: str = "pending"
    relation_sync_details: str | None = None
    relation_count: int = 0
    is_seed: bool
    is_active: bool
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    embedding_status: str = "not_indexed"

    model_config = {"from_attributes": True}


class DocumentChunkItem(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    section_title: str | None = None
    chunk_type: str | None = None
    citation_label: str | None = None
    hierarchy_path: str | None = None
    article_number: str | None = None
    clause_number: str | None = None
    point_number: str | None = None
    retrieval_text: str | None = None
    metadata_json: str | None = None
    content: str
    char_count: int

    model_config = {"from_attributes": True}


class LegalProvisionItem(BaseModel):
    id: int
    document_id: int
    parent_provision_id: int | None = None
    provision_level: str
    article_number: str | None = None
    clause_number: str | None = None
    point_code: str | None = None
    heading: str | None = None
    content: str
    citation_label: str | None = None
    sort_key: str
    effective_from: date | None = None
    effective_to: date | None = None
    legal_status: str | None = None
    metadata_json: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class ProvisionRelationItem(BaseModel):
    id: int
    source_document_id: int
    source_provision_id: int
    target_document_id: int
    target_provision_id: int
    relation_type: str
    relation_label: str | None = None
    source_excerpt: str | None = None
    target_excerpt: str | None = None
    confidence_score: float | None = None
    extraction_method: str | None = None
    metadata_json: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class IngestionPayload(BaseModel):
    document: DocumentItem
    extracted_characters: int
    chunk_count: int


class IngestDocumentRequest(BaseModel):
    extracted_text_override: str | None = None


class BulkIngestionFailureItem(BaseModel):
    document_id: int
    title: str
    reason: str


class BulkIngestionPayload(BaseModel):
    total_documents: int
    ingested_documents: int
    total_chunks: int
    failed_documents: list[BulkIngestionFailureItem]


class RetrievalPreviewItem(BaseModel):
    chunk_id: int
    chunk_index: int
    score: int
    section_title: str | None = None
    content_preview: str


class ExtractionDiagnosticPage(BaseModel):
    page: int
    extracted_characters: int


class ExtractionDiagnosticPayload(BaseModel):
    document_id: int
    source_type: str
    is_extractable: bool
    total_pages: int | None = None
    extracted_characters: int
    sample_pages: list[ExtractionDiagnosticPage]
    ocr_available: bool = False
    ocr_engine: str | None = None
    ocr_recommended: bool = False
    ocr_applied: bool = False
    ocr_average_confidence: float | None = None
    ocr_quality_score: float | None = None
    ocr_quality_label: str | None = None
    ocr_sample_pages: list[ExtractionDiagnosticPage] = []
    parser_article_count: int = 0
    parser_clause_count: int = 0
    parser_point_count: int = 0
    parser_provision_count: int = 0
    provision_relation_count: int = 0
    structure_quality_score: float | None = None
    structure_quality_label: str | None = None
    parser_status: str = "not_evaluated"
    parser_notes: list[str] = []
    recommendation: str


class DocumentBenchmarkDimension(BaseModel):
    name: str
    score: float
    details: str


class DocumentBenchmarkCheck(BaseModel):
    query: str
    query_type: str
    passed: bool
    top_hit_document_ids: list[int]


class DocumentBenchmarkPayload(BaseModel):
    document_id: int
    overall_score: float
    dimensions: list[DocumentBenchmarkDimension]
    retrieval_checks: list[DocumentBenchmarkCheck]


class GraphNodePayload(BaseModel):
    id: str
    document_id: int | None = None
    label: str
    title: str | None = None
    document_code: str | None = None
    document_type: str | None = None
    legal_status: str | None = None
    ocr_quality_score: float | None = None
    ocr_quality_label: str | None = None
    is_root: bool | None = None


class GraphProvisionRelationEvidencePayload(BaseModel):
    id: int
    relation_type: str
    relation_label: str | None = None
    source_provision_id: int
    target_provision_id: int
    source_excerpt: str | None = None
    target_excerpt: str | None = None
    confidence_score: float | None = None
    extraction_method: str | None = None
    metadata_json: str | None = None


class GraphEdgePayload(BaseModel):
    id: str
    source: int | str
    target: int | str
    relation_type: str
    relation_label: str | None = None
    confidence_score: float | None = None
    legal_basis: str | None = None
    metadata_json: str | None = None
    target_anchor: str | None = None
    target_excerpt: str | None = None
    provision_relation_count: int = 0
    provision_relation_types: list[str] = []
    provision_relation_samples: list[GraphProvisionRelationEvidencePayload] = []


class DocumentGraphPayload(BaseModel):
    graph_type: str
    root_document_id: int
    depth: int
    nodes: list[GraphNodePayload]
    edges: list[GraphEdgePayload]


class LegalConceptItem(BaseModel):
    id: int
    slug: str
    canonical_name: str
    concept_type: str
    legal_domain: str | None = None
    description: str | None = None
    is_seed: bool
    is_active: bool

    model_config = {"from_attributes": True}


class SemanticConceptNodePayload(BaseModel):
    id: str
    concept_id: int
    slug: str
    label: str
    concept_type: str
    legal_domain: str | None = None
    description: str | None = None
    is_root: bool | None = None


class SemanticConceptEdgePayload(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    label: str | None = None
    legal_effect: str | None = None
    confidence_score: float | None = None
    metadata_json: str | None = None


class SemanticConceptAnchorPayload(BaseModel):
    id: str
    concept_id: int
    document_id: int
    chunk_id: int | None = None
    relation_role: str
    confidence_score: float | None = None
    document_title: str | None = None
    document_code: str | None = None
    legal_status: str | None = None
    citation_label: str | None = None
    metadata_json: str | None = None
    source_excerpt: str | None = None


class SemanticConceptMatchPayload(BaseModel):
    concept_id: int
    slug: str
    canonical_name: str
    concept_type: str
    legal_domain: str | None = None
    matched_alias: str
    match_score: float


class SemanticGraphPayload(BaseModel):
    graph_type: str
    query: str | None = None
    depth: int
    root_concept_id: int | None = None
    nodes: list[SemanticConceptNodePayload]
    edges: list[SemanticConceptEdgePayload]
    anchors: list[SemanticConceptAnchorPayload]


class SemanticQueryPayload(SemanticGraphPayload):
    matched_concepts: list[SemanticConceptMatchPayload] = []


class RelationOntologyItem(BaseModel):
    relation_type: str
    label: str
    category: str
    legal_effect: str
    directional: bool
    code_match_confidence: float
    alias_match_confidence: float


class RelationOntologyResponse(BaseResponse[list[RelationOntologyItem]]):
    pass


class LegalConceptListResponse(BaseResponse[list[LegalConceptItem]]):
    pass


class ChunkListResponse(BaseResponse[list[DocumentChunkItem]]):
    pass


class ProvisionListResponse(BaseResponse[list[LegalProvisionItem]]):
    pass


class ProvisionRelationListResponse(BaseResponse[list[ProvisionRelationItem]]):
    pass


class IngestionResponse(BaseResponse[IngestionPayload]):
    pass


class BulkIngestionResponse(BaseResponse[BulkIngestionPayload]):
    pass


class RetrievalPreviewResponse(BaseResponse[list[RetrievalPreviewItem]]):
    pass


class ExtractionDiagnosticResponse(BaseResponse[ExtractionDiagnosticPayload]):
    pass


class DocumentBenchmarkResponse(BaseResponse[DocumentBenchmarkPayload]):
    pass


class DocumentGraphResponse(BaseResponse[DocumentGraphPayload]):
    pass


class SemanticGraphResponse(BaseResponse[SemanticGraphPayload]):
    pass


class SemanticQueryResponse(BaseResponse[SemanticQueryPayload]):
    pass


class KnowledgeOverviewPayload(BaseModel):
    categories: list[CategoryItem]
    documents: list[DocumentItem]


class CategoryListResponse(BaseResponse[list[CategoryItem]]):
    pass


class DocumentListResponse(BaseResponse[list[DocumentItem]]):
    pass


class KnowledgeOverviewResponse(BaseResponse[KnowledgeOverviewPayload]):
    pass
