import axios from "axios";
import { useState } from "react";

import { lawChatApi } from "../../api/lawchat.api";
import type {
  AutoIngestedDocumentResult,
  BulkIngestionPayload,
  DocumentChunkItem,
  DocumentWritePayload,
  DuplicateDocumentAction,
  ExtractionDiagnostic,
  IngestionPayload,
  LegalProvisionItem,
  ProvisionRelationItem,
} from "../../types/lawchat";
import { isDocumentDuplicateError } from "./helpers";
import type { SharedDocumentOperationParams } from "./types";

export function useAdminDocumentOperations({
  activeDocumentId,
  loadAdminOperations,
  savingAdmin,
  setError,
  setKnowledge,
  setSavingAdmin,
  ui,
}: SharedDocumentOperationParams) {
  const [diagnosing, setDiagnosing] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [diagnostics, setDiagnostics] = useState<ExtractionDiagnostic | null>(null);
  const [ingestionResult, setIngestionResult] = useState<IngestionPayload | null>(null);
  const [knowledgeMessage, setKnowledgeMessage] = useState<string | null>(null);

  async function refreshKnowledgeOverview() {
    const overview = await lawChatApi.getKnowledgeOverview();
    setKnowledge(overview);
  }

  async function loadDiagnostics(documentId: number) {
    setDiagnosing(true);
    setKnowledgeMessage(null);

    try {
      const payload = await lawChatApi.getDocumentDiagnostics(documentId);
      setDiagnostics(payload);
    } catch {
      setKnowledgeMessage(ui.appDiagnosticsError);
    } finally {
      setDiagnosing(false);
    }
  }

  async function handleIngest(documentId?: number) {
    const targetDocumentId = documentId ?? activeDocumentId;
    if (!targetDocumentId || ingesting) {
      return;
    }

    setIngesting(true);
    setKnowledgeMessage(null);

    try {
      const payload = await lawChatApi.ingestDocument(targetDocumentId);
      setIngestionResult(payload);
      setKnowledge((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          documents: current.documents.map((document) => (document.id === payload.document.id ? payload.document : document)),
        };
      });
      await loadAdminOperations();
      await loadDiagnostics(targetDocumentId);
      setKnowledgeMessage(ui.appIngestSuccess(payload.chunk_count));
    } catch (caught) {
      if (axios.isAxiosError(caught)) {
        setKnowledgeMessage(caught.response?.data?.message ?? ui.appIngestError);
      } else {
        setKnowledgeMessage(ui.appIngestError);
      }
    } finally {
      setIngesting(false);
    }
  }

  async function handleCreateDocument(payload: DocumentWritePayload, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">, extractedTextOverride?: string) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    setIngesting(true);
    setKnowledgeMessage(null);
    try {
      const createdDocument = await lawChatApi.createDocument(payload, duplicateAction);
      try {
        const ingestionPayload = await lawChatApi.ingestDocument(createdDocument.id, extractedTextOverride);
        setIngestionResult(ingestionPayload);
        setKnowledgeMessage(ui.appIngestSuccess(ingestionPayload.chunk_count));
        await loadDiagnostics(createdDocument.id);
      } catch (caught) {
        if (axios.isAxiosError(caught)) {
          setKnowledgeMessage(caught.response?.data?.message ?? ui.appIngestError);
        } else {
          setKnowledgeMessage(ui.appIngestError);
        }
      }
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch (caught) {
      if (isDocumentDuplicateError(caught)) {
        throw caught;
      }
      setError(ui.appCreateDocumentError);
      throw caught;
    } finally {
      setSavingAdmin(false);
      setIngesting(false);
    }
  }

  async function handleUpdateDocument(documentId: number, payload: DocumentWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateDocument(documentId, payload);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateDocumentError);
      throw new Error("update-document-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteDocument(documentId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteDocument(documentId);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appDeleteDocumentError);
      throw new Error("delete-document-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleReviewDocumentMetadata(documentId: number, notes?: string) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.reviewDocumentMetadata(documentId, notes);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appReviewDocumentError);
      throw new Error("review-document-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUploadDocumentFile(file: File) {
    return await lawChatApi.uploadDocumentFile(file);
  }

  async function handleUpdateMetadataAISettings(
    metadataEnabled: boolean,
    metadataProvider: string,
    model: string,
    webSearchEnabled: boolean,
    embeddingEnabled: boolean,
    embeddingModel: string,
    chatbotEnabled: boolean,
    chatbotProvider: string,
    publicChatbotModel: string,
    customerChatbotModel: string,
    consultantChatbotModel: string,
    graphBackend: string,
  ) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateMetadataAISettings(metadataEnabled, metadataProvider, model, webSearchEnabled);
      await lawChatApi.updateEmbeddingAISettings(embeddingEnabled, embeddingModel);
      await lawChatApi.updateChatbotAISettings(chatbotEnabled, chatbotProvider, publicChatbotModel, customerChatbotModel, consultantChatbotModel);
      await lawChatApi.updateGraphBackendSettings(graphBackend);
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateMetadataSettingsError);
      throw new Error("update-metadata-settings-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUploadAndIngestDocumentFile(file: File, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">): Promise<AutoIngestedDocumentResult> {
    if (savingAdmin || ingesting) {
      throw new Error("document-upload-in-progress");
    }
    setSavingAdmin(true);
    setIngesting(true);
    setError(null);
    try {
      const result = await lawChatApi.uploadAndIngestDocumentFile(file, duplicateAction);
      setIngestionResult({
        chunk_count: result.chunk_count,
        document: result.document,
        extracted_characters: result.extracted_characters,
      });
      await refreshKnowledgeOverview();
      await loadAdminOperations();
      await loadDiagnostics(result.document.id);
      setKnowledgeMessage(ui.appAutoIngestDocumentSuccess(result.document.title, result.chunk_count));
      return result;
    } catch (caught) {
      if (isDocumentDuplicateError(caught)) {
        throw caught;
      }
      setError(ui.appAutoIngestDocumentError);
      throw caught;
    } finally {
      setSavingAdmin(false);
      setIngesting(false);
    }
  }

  async function handleReingestAllDocuments(): Promise<BulkIngestionPayload> {
    if (savingAdmin || ingesting) {
      throw new Error("document-reingest-in-progress");
    }
    setSavingAdmin(true);
    setIngesting(true);
    setKnowledgeMessage(null);
    setError(null);
    try {
      const payload = await lawChatApi.reingestDocuments();
      await refreshKnowledgeOverview();
      await loadAdminOperations();
      setKnowledgeMessage(ui.reingestAllResult(payload.ingested_documents, payload.total_documents, payload.total_chunks, payload.failed_documents.length));
      return payload;
    } catch (caught) {
      if (axios.isAxiosError(caught)) {
        setKnowledgeMessage(caught.response?.data?.message ?? ui.appIngestError);
      } else {
        setKnowledgeMessage(ui.appIngestError);
      }
      throw caught;
    } finally {
      setSavingAdmin(false);
      setIngesting(false);
    }
  }

  async function handleLoadDocumentChunks(documentId: number): Promise<DocumentChunkItem[]> {
    return await lawChatApi.listDocumentChunks(documentId);
  }

  async function handleLoadDocumentProvisions(documentId: number): Promise<LegalProvisionItem[]> {
    return await lawChatApi.listDocumentProvisions(documentId);
  }

  async function handleLoadProvisionRelations(documentId: number): Promise<ProvisionRelationItem[]> {
    return await lawChatApi.listProvisionRelations(documentId);
  }

  async function handleRefreshDocumentStructure(documentId: number): Promise<void> {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.refreshDocumentStructure(documentId);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appIngestError);
      throw new Error("refresh-document-structure-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  return {
    diagnosing,
    diagnostics,
    handleCreateDocument,
    handleDeleteDocument,
    handleIngest,
    handleLoadDocumentChunks,
    handleLoadDocumentProvisions,
    handleLoadProvisionRelations,
    handleRefreshDocumentStructure,
    handleReingestAllDocuments,
    handleReviewDocumentMetadata,
    handleUpdateDocument,
    handleUpdateMetadataAISettings,
    handleUploadAndIngestDocumentFile,
    handleUploadDocumentFile,
    ingested: ingestionResult,
    ingesting,
    knowledgeMessage,
    loadDiagnostics,
  };
}
