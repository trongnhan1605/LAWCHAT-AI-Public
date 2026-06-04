import type { UserRole } from "./auth";

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export type DuplicateDocumentAction = "overwrite" | "create_new" | "skip";

export interface DuplicateDocumentConflictData {
  conflict_type: "document_duplicate";
  allowed_actions: DuplicateDocumentAction[];
  matching_fields: Array<"title" | "file_name" | "content_sha256" | "source_identity">;
  existing_document: {
    id: number;
    title: string;
    file_name: string;
    source_type: string;
    legal_domain: string;
    source_reference: string | null;
    storage_path: string | null;
    content_sha256?: string | null;
    source_identity?: string | null;
  };
  suggested_title: string;
  suggested_file_name: string;
}

export interface ChatSession {
  session_token: string;
  user_id: number | null;
  session_type: string;
  status: string;
  topic_guess: string | null;
  last_confidence_score: number | null;
  escalated_ticket_id: number | null;
}

export interface Citation {
  title: string;
  source_reference: string | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  message_type: string;
  content: string;
  category_slug: string | null;
  confidence_score: number | null;
  warning_text: string | null;
  citation: Citation | null;
  needs_escalation: boolean;
  created_at: string;
}

export interface SessionDetail {
  session: ChatSession;
  messages: ChatMessage[];
}

export interface AskMessagePayload {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
}

export interface ContentArticle {
  id: number;
  title: string;
  slug: string;
  category: string;
  excerpt: string;
  source_url: string | null;
  is_featured: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ContentArticleWritePayload = Omit<ContentArticle, "id" | "created_at" | "updated_at">;

export interface LawyerProfile {
  id: number;
  full_name: string;
  slug: string;
  title: string;
  location: string;
  specialties: string;
  experience_years: number;
  rating: string | null;
  bio: string | null;
  avatar_url: string | null;
  is_featured: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type LawyerProfileWritePayload = Omit<LawyerProfile, "id" | "created_at" | "updated_at">;

export interface DefinitionItem {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  priority: number;
  is_active: boolean;
}

export interface AdminUserItem {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AdminUserWritePayload {
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  password?: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  file_name: string;
  source_type: string;
  legal_domain: string;
  authority_level: string | null;
  issuing_authority: string | null;
  document_code: string | null;
  document_type: string | null;
  normative_level: number | null;
  signed_date: string | null;
  source_reference: string | null;
  storage_path: string | null;
  summary: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  legal_status: string | null;
  metadata_review_status: string;
  metadata_review_notes: string | null;
  metadata_last_reviewed_at: string | null;
  content_sha256: string | null;
  source_identity: string | null;
  ingestion_quality_status: string;
  ingestion_quality_notes: string | null;
  retrieval_visibility: string;
  ocr_quality_score: number | null;
  ocr_quality_label: string | null;
  relation_sync_status: string;
  relation_sync_details: string | null;
  relation_count: number;
  is_seed: boolean;
  is_active: boolean;
  chunk_count: number;
  embedded_chunk_count: number;
  embedding_status: string;
}

export type DocumentWritePayload = Omit<DocumentItem, "id" | "metadata_review_status" | "metadata_review_notes" | "metadata_last_reviewed_at" | "content_sha256" | "source_identity" | "ingestion_quality_status" | "ingestion_quality_notes" | "retrieval_visibility" | "ocr_quality_score" | "ocr_quality_label" | "relation_sync_status" | "relation_sync_details" | "relation_count" | "is_seed" | "chunk_count" | "embedded_chunk_count" | "embedding_status">;

export interface UploadedDocumentFile {
  title: string;
  file_name: string;
  source_type: string;
  source_reference: string;
  storage_path: string;
  extracted_text: string | null;
  extracted_characters: number;
  ocr_applied: boolean;
  ocr_review_required: boolean;
  ocr_correction_changed_token_count: number;
  ocr_suggestions: OcrCorrectionSuggestionItem[];
  legal_domain: string | null;
  authority_level: string | null;
  issuing_authority: string | null;
  document_code: string | null;
  document_type: string | null;
  normative_level: number | null;
  signed_date: string | null;
  summary: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  legal_status: string | null;
}

export interface OcrCorrectionSuggestionItem {
  token_index: number;
  original: string;
  corrected: string;
  confidence_score?: number | null;
  reason?: string | null;
  line_number?: number | null;
  context_excerpt?: string | null;
}

export interface OcrCorrectionPreviewPayload {
  normalized_text?: string | null;
  corrected_text: string;
  changed: boolean;
  changed_token_count: number;
  suggestions: OcrCorrectionSuggestionItem[];
  review_required: boolean;
}

export interface AutoIngestedDocumentResult {
  uploaded_file: UploadedDocumentFile;
  document: DocumentItem;
  extracted_characters: number;
  chunk_count: number;
}

export interface DocumentChunkItem {
  id: number;
  document_id: number;
  chunk_index: number;
  section_title: string | null;
  chunk_type: string | null;
  citation_label: string | null;
  hierarchy_path: string | null;
  article_number: string | null;
  clause_number: string | null;
  point_number: string | null;
  retrieval_text: string | null;
  metadata_json: string | null;
  content: string;
  char_count: number;
}

export interface LegalProvisionItem {
  id: number;
  document_id: number;
  parent_provision_id: number | null;
  provision_level: string;
  article_number: string | null;
  clause_number: string | null;
  point_code: string | null;
  heading: string | null;
  content: string;
  citation_label: string | null;
  sort_key: string;
  effective_from: string | null;
  effective_to: string | null;
  legal_status: string | null;
  metadata_json: string | null;
  is_active: boolean;
}

export interface ProvisionRelationItem {
  id: number;
  source_document_id: number;
  source_provision_id: number;
  target_document_id: number;
  target_provision_id: number;
  relation_type: string;
  relation_label: string | null;
  source_excerpt: string | null;
  target_excerpt: string | null;
  confidence_score: number | null;
  extraction_method: string | null;
  metadata_json: string | null;
  is_active: boolean;
}

export interface KnowledgeOverview {
  categories: Category[];
  documents: DocumentItem[];
}

export interface Ticket {
  id: number;
  session_id: number;
  case_id: number | null;
  title: string;
  topic: string | null;
  escalation_reason: string;
  confidence_score: number | null;
  status: string;
  priority: string;
  consultant_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketMessage {
  id: number;
  ticket_id: number;
  sender_type: string;
  sender_name: string;
  content: string;
  created_at: string;
}

export interface TicketDetail {
  ticket: Ticket;
  legal_case: LegalCaseItem | null;
  case_facts: CaseFactItem[];
  validation_runs: ValidationRunItem[];
  session_messages: ChatMessage[];
  consultant_messages: TicketMessage[];
}

export interface ExtractionDiagnosticPage {
  page: number;
  extracted_characters: number;
}

export interface ExtractionDiagnostic {
  document_id: number;
  source_type: string;
  is_extractable: boolean;
  total_pages: number | null;
  extracted_characters: number;
  sample_pages: ExtractionDiagnosticPage[];
  ocr_available: boolean;
  ocr_engine: string | null;
  ocr_recommended: boolean;
  ocr_applied: boolean;
  ocr_average_confidence: number | null;
  ocr_quality_score: number | null;
  ocr_quality_label: string | null;
  ocr_sample_pages: ExtractionDiagnosticPage[];
  parser_article_count: number;
  parser_clause_count: number;
  parser_point_count: number;
  parser_provision_count: number;
  provision_relation_count: number;
  structure_quality_score: number | null;
  structure_quality_label: string | null;
  parser_status: string;
  parser_notes: string[];
  recommendation: string;
}

export interface IngestionPayload {
  document: DocumentItem;
  extracted_characters: number;
  chunk_count: number;
}

export interface BulkIngestionFailureItem {
  document_id: number;
  title: string;
  reason: string;
}

export interface BulkIngestionPayload {
  total_documents: number;
  ingested_documents: number;
  total_chunks: number;
  failed_documents: BulkIngestionFailureItem[];
}

export interface DocumentBenchmarkDimension {
  name: string;
  score: number;
  details: string;
}

export interface DocumentBenchmarkCheck {
  query: string;
  query_type: string;
  passed: boolean;
  top_hit_document_ids: number[];
}

export interface DocumentBenchmarkPayload {
  document_id: number;
  overall_score: number;
  dimensions: DocumentBenchmarkDimension[];
  retrieval_checks: DocumentBenchmarkCheck[];
}

export interface GraphNodeItem {
  id: string;
  document_id: number | null;
  label: string;
  title: string | null;
  document_code: string | null;
  document_type: string | null;
  legal_status: string | null;
  ocr_quality_score: number | null;
  ocr_quality_label: string | null;
  is_root: boolean | null;
}

export interface GraphEdgeItem {
  id: string;
  source: number | string;
  target: number | string;
  relation_type: string;
  relation_label: string | null;
  confidence_score: number | null;
  legal_basis: string | null;
  metadata_json: string | null;
  target_anchor: string | null;
  target_excerpt: string | null;
  provision_relation_count: number;
  provision_relation_types: string[];
  provision_relation_samples: ProvisionRelationItem[];
}

export interface DocumentGraphPayload {
  graph_type: string;
  root_document_id: number;
  depth: number;
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
}

export interface AdminOverview {
  total_sessions: number;
  total_messages: number;
  total_legal_cases: number;
  active_legal_cases: number;
  high_risk_legal_cases: number;
  total_case_facts: number;
  total_documents: number;
  ingested_documents: number;
  total_chunks: number;
  total_document_relations: number;
  total_citations: number;
  total_categories: number;
  active_categories: number;
  total_tickets: number;
  open_tickets: number;
  answered_tickets: number;
  total_planner_runs: number;
  total_reasoning_runs: number;
  total_validation_runs: number;
  validation_runs_needing_review: number;
  escalations_recommended: number;
}

export interface AdminActivityItem {
  event_type: string;
  title: string;
  description: string;
  occurred_at: string;
}

export interface AIUsageOverview {
  total_requests: number;
  metadata_requests: number;
  embedding_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_input_tokens: number;
  total_web_search_calls: number;
  total_estimated_cost_usd: number;
}

export interface AIUsageByDayItem {
  day: string;
  request_count: number;
  metadata_requests: number;
  embedding_requests: number;
  web_search_calls: number;
  estimated_cost_usd: number;
}

export interface AIUsageByDocumentItem {
  document_id: number | null;
  title: string;
  file_name: string | null;
  models_used: string[];
  request_count: number;
  metadata_requests: number;
  embedding_requests: number;
  input_tokens: number;
  output_tokens: number;
  web_search_calls: number;
  estimated_cost_usd: number;
}

export interface AIUsageRequestItem {
  id: number;
  created_at: string;
  request_type: string;
  endpoint: string;
  provider: string;
  model: string;
  request_identifier: string | null;
  document_id: number | null;
  document_title: string | null;
  file_name: string | null;
  chunk_count: number | null;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  total_tokens: number;
  web_search_calls: number;
  estimated_cost_usd: number;
  status: string;
  error_message: string | null;
}

export interface PlannerRunItem {
  id: number;
  case_id?: number | null;
  session_id: number | null;
  user_id: number | null;
  query_text: string;
  detected_intent: string | null;
  detected_domain: string | null;
  complexity_level: string | null;
  status: string;
  plan_json: string | null;
  context_json: string | null;
  result_json: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ValidationRunItem {
  id: number;
  case_id?: number | null;
  planner_run_id: number | null;
  reasoning_run_id: number | null;
  response_text: string | null;
  validation_status: string;
  confidence_score: number | null;
  escalation_recommended: boolean;
  findings_json: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface MetadataAISettings {
  enabled: boolean;
  provider: string;
  model: string;
  web_search_enabled: boolean;
  available_providers: string[];
  available_models: string[];
}

export interface EmbeddingAISettings {
  enabled: boolean;
  model: string;
  available_models: string[];
}

export interface ChatbotAISettings {
  enabled: boolean;
  provider: string;
  model: string;
  public_model: string;
  customer_model: string;
  consultant_model: string;
  available_providers: string[];
  available_models: string[];
}

export interface GraphBackendSettings {
  backend: string;
  available_backends: string[];
  neo4j_configured: boolean;
  neo4j_available: boolean;
  neo4j_database: string | null;
  neo4j_sync_enabled: boolean;
}

export interface GraphBackendBenchmarkItem {
  backend: string;
  document_id: number;
  depth: number;
  runs: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  node_count: number;
  edge_count: number;
}

export interface GraphBackendBenchmarkPayload {
  document_ids: number[];
  depths: number[];
  runs_per_case: number;
  results: GraphBackendBenchmarkItem[];
}

export interface GraphBackendParityItem {
  document_id: number;
  depth: number;
  node_count_relational: number;
  node_count_neo4j: number;
  edge_count_relational: number;
  edge_count_neo4j: number;
  node_count_match: boolean;
  edge_count_match: boolean;
  edge_identity_match: boolean;
  anchor_match: boolean;
}

export interface GraphBackendParityPayload {
  document_ids: number[];
  depths: number[];
  results: GraphBackendParityItem[];
}

export interface GraphBackendRecommendation {
  recommended_backend: string;
  summary: string;
  reasons: string[];
}

export interface GraphBackendInsights {
  benchmark: GraphBackendBenchmarkPayload | null;
  parity: GraphBackendParityPayload | null;
  recommendation: GraphBackendRecommendation | null;
  updated_at: string | null;
}

export interface CorpusQualitySummary {
  total_documents: number;
  pending_review_documents: number;
  reviewed_documents: number;
  high_risk_documents: number;
  medium_risk_documents: number;
  low_risk_documents: number;
  total_chunks: number;
  total_provisions: number;
  total_document_relations: number;
  total_provision_relations: number;
  relations_missing_evidence: number;
  issue_counts: Record<string, number>;
}

export interface CorpusQualityDocumentItem {
  document_id: number;
  title: string;
  file_name: string;
  source_reference: string | null;
  storage_path: string;
  document_code: string | null;
  document_type: string | null;
  legal_domain: string;
  authority_level: string | null;
  issuing_authority: string | null;
  signed_date: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  legal_status: string | null;
  metadata_review_status: string;
  content_sha256: string | null;
  source_identity: string | null;
  ingestion_quality_status: string;
  ingestion_quality_notes: string | null;
  retrieval_visibility: string;
  ocr_quality_label: string | null;
  ocr_quality_score: number | null;
  chunk_count: number;
  provision_count: number;
  indexed_chunk_count: number;
  document_relation_count: number;
  provision_relation_count: number;
  missing_relation_evidence_count: number;
  risk_level: "high" | "medium" | "low" | string;
  issue_codes: string[];
  recommendations: string[];
}

export interface CorpusQualityReport {
  summary: CorpusQualitySummary;
  items: CorpusQualityDocumentItem[];
}

export interface ReviewQueueSummaryItem {
  count: number;
  high: number;
  medium: number;
  low: number;
}

export interface ReviewQueueItem {
  queue: string;
  source_type: string;
  source_id: string;
  title: string;
  status: string;
  severity: string;
  detail: string;
  action: string;
  created_at: string | null;
  document_id?: number | null;
  case_id?: number | null;
  source_path?: string | null;
}

export interface ReviewQueuesPayload {
  summary: Record<string, ReviewQueueSummaryItem>;
  queues: Record<string, ReviewQueueItem[]>;
}

export interface AnnotationEntityPayload {
  id: string;
  label: string;
  text: string;
  start: number | null;
  end: number | null;
  normalized_value: string | null;
  attributes: Record<string, string | number | boolean | null>;
}

export interface AnnotationRelationPayload {
  id: string;
  relation_type: string;
  source_entity_id: string;
  target_entity_id: string;
  confidence_score: number | null;
  attributes: Record<string, string | number | boolean | null>;
}

export interface AnnotationDocumentPayload {
  document_id: number | null;
  vendor: string;
  source_file_name: string | null;
  source_text: string | null;
  language: string;
  review_status: string;
  entities: AnnotationEntityPayload[];
  relations: AnnotationRelationPayload[];
}

export interface AnnotationImportSummaryPayload {
  vendor: string;
  document_id: number | null;
  source_file_name: string | null;
  entity_count: number;
  relation_count: number;
  metadata_fields: Record<string, string>;
  provision_count: number;
  provision_relation_count: number;
  semantic_entity_count: number;
  warnings: string[];
}

export interface AnnotationVendorExportPayload {
  vendor: string;
  document_id: number;
  task: Record<string, unknown>;
  internal_payload: AnnotationDocumentPayload;
  import_summary: AnnotationImportSummaryPayload;
}

export interface AnnotationGroundTruthSavePayload {
  file_name: string;
  download_url: string;
  saved_at: string;
  import_summary: AnnotationImportSummaryPayload;
  bundle_counts: Record<string, number>;
}

export interface LegalCaseItem {
  id: number;
  session_id: number | null;
  user_id: number | null;
  title: string;
  legal_domain: string;
  status: string;
  risk_level: string;
  summary: string | null;
  desired_outcome: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseFactItem {
  id: number;
  case_id: number;
  source_message_id: number | null;
  fact_type: string;
  fact_key: string;
  fact_value: string;
  happened_on: string | null;
  is_disputed: boolean;
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface LegalCaseDetail {
  legal_case: LegalCaseItem;
  case_facts: CaseFactItem[];
  planner_runs: PlannerRunItem[];
  validation_runs: ValidationRunItem[];
  tickets: Ticket[];
}

export interface AdminOperations {
  overview: AdminOverview;
  users: AdminUserItem[];
  documents: DocumentItem[];
  categories: Category[];
  content_articles: ContentArticle[];
  lawyer_profiles: LawyerProfile[];
  document_types: DefinitionItem[];
  authority_levels: DefinitionItem[];
  activities: AdminActivityItem[];
  metadata_ai_settings: MetadataAISettings;
  embedding_ai_settings: EmbeddingAISettings;
  chatbot_ai_settings: ChatbotAISettings;
  graph_backend_settings: GraphBackendSettings;
  graph_backend_insights: GraphBackendInsights | null;
  ai_usage_overview: AIUsageOverview;
  ai_usage_by_day: AIUsageByDayItem[];
  ai_usage_by_document: AIUsageByDocumentItem[];
  recent_ai_requests: AIUsageRequestItem[];
  recent_legal_cases: LegalCaseItem[];
  recent_planner_runs: PlannerRunItem[];
  recent_validation_runs: ValidationRunItem[];
}
