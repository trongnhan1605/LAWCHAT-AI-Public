import api from "../http/axios";
import type {
  ApiEnvelope,
  BulkIngestionPayload,
  DocumentBenchmarkPayload,
  DocumentChunkItem,
  DocumentGraphPayload,
  ExtractionDiagnostic,
  IngestionPayload,
  KnowledgeOverview,
  LegalProvisionItem,
  ProvisionRelationItem,
} from "../types/lawchat";

export const knowledgeApi = {
  async getKnowledgeOverview(): Promise<KnowledgeOverview> {
    const response = await api.get<ApiEnvelope<KnowledgeOverview>>("/knowledge/overview");
    return response.data.data;
  },

  async getDocumentDiagnostics(documentId: number): Promise<ExtractionDiagnostic> {
    const response = await api.get<ApiEnvelope<ExtractionDiagnostic>>(`/knowledge/documents/${documentId}/diagnostics`);
    return response.data.data;
  },

  async ingestDocument(documentId: number, extractedTextOverride?: string): Promise<IngestionPayload> {
    const response = await api.post<ApiEnvelope<IngestionPayload>>(`/knowledge/documents/${documentId}/ingest`, {
      extracted_text_override: extractedTextOverride?.trim() ? extractedTextOverride : null,
    });
    return response.data.data;
  },

  async reingestDocuments(): Promise<BulkIngestionPayload> {
    const response = await api.post<ApiEnvelope<BulkIngestionPayload>>("/knowledge/documents/reingest");
    return response.data.data;
  },

  async refreshDocumentStructure(documentId: number): Promise<IngestionPayload> {
    const response = await api.post<ApiEnvelope<IngestionPayload>>(`/knowledge/documents/${documentId}/refresh-structure`);
    return response.data.data;
  },

  async listDocumentChunks(documentId: number): Promise<DocumentChunkItem[]> {
    const response = await api.get<ApiEnvelope<DocumentChunkItem[]>>(`/knowledge/documents/${documentId}/chunks`);
    return response.data.data;
  },

  async listDocumentProvisions(documentId: number): Promise<LegalProvisionItem[]> {
    const response = await api.get<ApiEnvelope<LegalProvisionItem[]>>(`/knowledge/documents/${documentId}/provisions`);
    return response.data.data;
  },

  async listProvisionRelations(documentId: number): Promise<ProvisionRelationItem[]> {
    const response = await api.get<ApiEnvelope<ProvisionRelationItem[]>>(`/knowledge/documents/${documentId}/provision-relations`);
    return response.data.data;
  },

  async getDocumentBenchmark(documentId: number): Promise<DocumentBenchmarkPayload> {
    const response = await api.get<ApiEnvelope<DocumentBenchmarkPayload>>(`/knowledge/documents/${documentId}/benchmark`);
    return response.data.data;
  },

  async getDocumentGraph(documentId: number, depth = 1): Promise<DocumentGraphPayload> {
    const response = await api.get<ApiEnvelope<DocumentGraphPayload>>(`/knowledge/documents/${documentId}/graph`, {
      params: { depth },
    });
    return response.data.data;
  },
};
