import api from "../http/axios";
import type {
  AdminOperations,
  AdminUserItem,
  AdminUserWritePayload,
  AnnotationDocumentPayload,
  AnnotationGroundTruthSavePayload,
  AnnotationVendorExportPayload,
  ApiEnvelope,
  AutoIngestedDocumentResult,
  Category,
  ChatbotAISettings,
  ContentArticle,
  ContentArticleWritePayload,
  CorpusQualityReport,
  DefinitionItem,
  DocumentItem,
  DocumentWritePayload,
  DuplicateDocumentAction,
  EmbeddingAISettings,
  GraphBackendBenchmarkPayload,
  GraphBackendParityPayload,
  GraphBackendSettings,
  LawyerProfile,
  LawyerProfileWritePayload,
  MetadataAISettings,
  OcrCorrectionPreviewPayload,
  ReviewQueuesPayload,
  UploadedDocumentFile,
} from "../types/lawchat";

export const adminApi = {
  async getAdminOperations(): Promise<AdminOperations> {
    const response = await api.get<ApiEnvelope<AdminOperations>>("/admin/operations");
    return response.data.data;
  },

  async getCorpusQualityReport(includeReviewed = true): Promise<CorpusQualityReport> {
    const response = await api.get<ApiEnvelope<CorpusQualityReport>>("/admin/corpus/quality-report", {
      params: { include_reviewed: includeReviewed },
    });
    return response.data.data;
  },

  async getReviewQueues(limitPerQueue = 20): Promise<ReviewQueuesPayload> {
    const response = await api.get<ApiEnvelope<ReviewQueuesPayload>>("/admin/review-queues", {
      params: { limit_per_queue: limitPerQueue },
    });
    return response.data.data;
  },

  async createAdminUser(payload: AdminUserWritePayload): Promise<AdminUserItem> {
    const response = await api.post<ApiEnvelope<AdminUserItem>>("/admin/users", payload);
    return response.data.data;
  },

  async updateAdminUser(userId: number, payload: AdminUserWritePayload): Promise<AdminUserItem> {
    const response = await api.put<ApiEnvelope<AdminUserItem>>(`/admin/users/${userId}`, payload);
    return response.data.data;
  },

  async deleteAdminUser(userId: number): Promise<void> {
    await api.delete(`/admin/users/${userId}`);
  },

  async updateMetadataAISettings(enabled: boolean, provider: string, model: string, webSearchEnabled: boolean): Promise<MetadataAISettings> {
    const response = await api.put<ApiEnvelope<MetadataAISettings>>("/admin/metadata-ai-settings", {
      enabled,
      provider,
      model,
      web_search_enabled: webSearchEnabled,
    });
    return response.data.data;
  },

  async updateEmbeddingAISettings(enabled: boolean, model: string): Promise<EmbeddingAISettings> {
    const response = await api.put<ApiEnvelope<EmbeddingAISettings>>("/admin/embedding-ai-settings", {
      enabled,
      model,
    });
    return response.data.data;
  },

  async updateChatbotAISettings(
    enabled: boolean,
    provider: string,
    publicModel: string,
    customerModel: string,
    consultantModel: string,
  ): Promise<ChatbotAISettings> {
    const response = await api.put<ApiEnvelope<ChatbotAISettings>>("/admin/chatbot-ai-settings", {
      enabled,
      provider,
      public_model: publicModel,
      customer_model: customerModel,
      consultant_model: consultantModel,
    });
    return response.data.data;
  },

  async createCategory(name: string, slug: string, description: string): Promise<Category> {
    const response = await api.post<ApiEnvelope<Category>>("/admin/categories", { name, slug, description });
    return response.data.data;
  },

  async updateCategory(categoryId: number, name: string, slug: string, description: string, isActive: boolean): Promise<Category> {
    const response = await api.put<ApiEnvelope<Category>>(`/admin/categories/${categoryId}`, {
      name,
      slug,
      description,
      is_active: isActive,
    });
    return response.data.data;
  },

  async deleteCategory(categoryId: number): Promise<void> {
    await api.delete(`/admin/categories/${categoryId}`);
  },

  async toggleCategory(categoryId: number, isActive: boolean): Promise<Category> {
    const response = await api.post<ApiEnvelope<Category>>(`/admin/categories/${categoryId}/toggle`, { is_active: isActive });
    return response.data.data;
  },

  async createContentArticle(payload: ContentArticleWritePayload): Promise<ContentArticle> {
    const response = await api.post<ApiEnvelope<ContentArticle>>("/admin/content-articles", payload);
    return response.data.data;
  },

  async updateContentArticle(articleId: number, payload: ContentArticleWritePayload): Promise<ContentArticle> {
    const response = await api.put<ApiEnvelope<ContentArticle>>(`/admin/content-articles/${articleId}`, payload);
    return response.data.data;
  },

  async deleteContentArticle(articleId: number): Promise<void> {
    await api.delete(`/admin/content-articles/${articleId}`);
  },

  async createLawyerProfile(payload: LawyerProfileWritePayload): Promise<LawyerProfile> {
    const response = await api.post<ApiEnvelope<LawyerProfile>>("/admin/lawyer-profiles", payload);
    return response.data.data;
  },

  async updateLawyerProfile(lawyerId: number, payload: LawyerProfileWritePayload): Promise<LawyerProfile> {
    const response = await api.put<ApiEnvelope<LawyerProfile>>(`/admin/lawyer-profiles/${lawyerId}`, payload);
    return response.data.data;
  },

  async deleteLawyerProfile(lawyerId: number): Promise<void> {
    await api.delete(`/admin/lawyer-profiles/${lawyerId}`);
  },

  async createDocumentType(name: string, slug: string, description: string, priority: number): Promise<DefinitionItem> {
    const response = await api.post<ApiEnvelope<DefinitionItem>>("/admin/document-types", { name, slug, description, priority });
    return response.data.data;
  },

  async updateDocumentType(
    itemId: number,
    name: string,
    slug: string,
    description: string,
    priority: number,
    isActive: boolean,
  ): Promise<DefinitionItem> {
    const response = await api.put<ApiEnvelope<DefinitionItem>>(`/admin/document-types/${itemId}`, {
      name,
      slug,
      description,
      priority,
      is_active: isActive,
    });
    return response.data.data;
  },

  async deleteDocumentType(itemId: number): Promise<void> {
    await api.delete(`/admin/document-types/${itemId}`);
  },

  async createAuthorityLevel(name: string, slug: string, description: string, priority: number): Promise<DefinitionItem> {
    const response = await api.post<ApiEnvelope<DefinitionItem>>("/admin/authority-levels", { name, slug, description, priority });
    return response.data.data;
  },

  async updateAuthorityLevel(
    itemId: number,
    name: string,
    slug: string,
    description: string,
    priority: number,
    isActive: boolean,
  ): Promise<DefinitionItem> {
    const response = await api.put<ApiEnvelope<DefinitionItem>>(`/admin/authority-levels/${itemId}`, {
      name,
      slug,
      description,
      priority,
      is_active: isActive,
    });
    return response.data.data;
  },

  async deleteAuthorityLevel(itemId: number): Promise<void> {
    await api.delete(`/admin/authority-levels/${itemId}`);
  },

  async createDocument(payload: DocumentWritePayload, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">): Promise<DocumentItem> {
    const response = await api.post<ApiEnvelope<DocumentItem>>("/admin/documents", {
      ...payload,
      duplicate_action: duplicateAction ?? null,
    });
    return response.data.data;
  },

  async uploadDocumentFile(file: File): Promise<UploadedDocumentFile> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post<ApiEnvelope<UploadedDocumentFile>>("/admin/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data.data;
  },

  async uploadAndIngestDocumentFile(file: File, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">): Promise<AutoIngestedDocumentResult> {
    const formData = new FormData();
    formData.append("file", file);
    if (duplicateAction) {
      formData.append("duplicate_action", duplicateAction);
    }
    const response = await api.post<ApiEnvelope<AutoIngestedDocumentResult>>("/admin/documents/upload-and-ingest", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data.data;
  },

  async updateDocument(documentId: number, payload: DocumentWritePayload): Promise<DocumentItem> {
    const response = await api.put<ApiEnvelope<DocumentItem>>(`/admin/documents/${documentId}`, payload);
    return response.data.data;
  },

  async reviewDocumentMetadata(documentId: number, notes?: string): Promise<DocumentItem> {
    const response = await api.post<ApiEnvelope<DocumentItem>>(`/admin/documents/${documentId}/review`, {
      notes: notes ?? null,
    });
    return response.data.data;
  },

  async deleteDocument(documentId: number): Promise<void> {
    await api.delete(`/admin/documents/${documentId}`);
  },

  async previewOcrCorrection(text: string): Promise<OcrCorrectionPreviewPayload> {
    const response = await api.post<ApiEnvelope<OcrCorrectionPreviewPayload>>("/admin/documents/ocr-correction-preview", {
      text,
    });
    return response.data.data;
  },

  async updateGraphBackendSettings(backend: string): Promise<GraphBackendSettings> {
    const response = await api.put<ApiEnvelope<GraphBackendSettings>>("/admin/graph-backend-settings", {
      backend,
    });
    return response.data.data;
  },

  async getGraphBackendBenchmark(documentIds = "10,24,51", depths = "1,2", runs = 2): Promise<GraphBackendBenchmarkPayload> {
    const response = await api.get<ApiEnvelope<GraphBackendBenchmarkPayload>>("/admin/graph-backend/benchmark", {
      params: { document_ids: documentIds, depths, runs },
      timeout: 180000,
    });
    return response.data.data;
  },

  async getGraphBackendParity(documentIds = "10,24,51", depths = "1,2"): Promise<GraphBackendParityPayload> {
    const response = await api.get<ApiEnvelope<GraphBackendParityPayload>>("/admin/graph-backend/parity", {
      params: { document_ids: documentIds, depths },
      timeout: 180000,
    });
    return response.data.data;
  },

  async getLabelStudioAnnotationPreview(documentId: number): Promise<AnnotationVendorExportPayload> {
    const response = await api.get<ApiEnvelope<AnnotationVendorExportPayload>>(`/admin/annotation/label-studio/export-preview/${documentId}`);
    return response.data.data;
  },

  async saveAnnotationGroundTruth(payload: AnnotationDocumentPayload): Promise<AnnotationGroundTruthSavePayload> {
    const response = await api.post<ApiEnvelope<AnnotationGroundTruthSavePayload>>("/admin/annotation/ground-truth/save", {
      payload,
    });
    return response.data.data;
  },

  async downloadAnnotationGroundTruth(fileName: string): Promise<Blob> {
    const response = await api.get(`/admin/annotation/ground-truth/download/${encodeURIComponent(fileName)}`, {
      responseType: "blob",
    });
    return response.data;
  },
};
