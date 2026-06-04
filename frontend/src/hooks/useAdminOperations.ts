import axios from "axios";
import { useEffect, useState } from "react";

import { lawChatApi } from "../api/lawchat.api";
import type { UiText } from "../locales";
import type { AdminOperations, ContentArticleWritePayload, CorpusQualityReport, DocumentItem, GraphBackendBenchmarkPayload, GraphBackendParityPayload, KnowledgeOverview, LawyerProfileWritePayload, ReviewQueuesPayload } from "../types/lawchat";
import { hasStoredAccessToken } from "./admin/helpers";
import { useAdminDocumentOperations } from "./admin/useAdminDocumentOperations";
import { useAdminTaxonomyOperations } from "./admin/useAdminTaxonomyOperations";
import { useAdminUsersManager } from "./admin/useAdminUsersManager";

type UseAdminOperationsParams = {
  activeDocument: DocumentItem | null;
  handleUnauthorized: () => void;
  setError: (value: string | null) => void;
  setKnowledge: (value: KnowledgeOverview | null | ((current: KnowledgeOverview | null) => KnowledgeOverview | null)) => void;
  ui: UiText;
};

export function useAdminOperations({ activeDocument, handleUnauthorized, setError, setKnowledge, ui }: UseAdminOperationsParams) {
  const [adminData, setAdminData] = useState<AdminOperations | null>(null);
  const [loadingAdmin, setLoadingAdmin] = useState(false);
  const [savingAdmin, setSavingAdmin] = useState(false);
  const [graphBenchmark, setGraphBenchmark] = useState<GraphBackendBenchmarkPayload | null>(null);
  const [graphParity, setGraphParity] = useState<GraphBackendParityPayload | null>(null);
  const [graphInsightsMessage, setGraphInsightsMessage] = useState<string | null>(null);
  const [loadingGraphInsights, setLoadingGraphInsights] = useState(false);
  const [corpusQualityReport, setCorpusQualityReport] = useState<CorpusQualityReport | null>(null);
  const [reviewQueues, setReviewQueues] = useState<ReviewQueuesPayload | null>(null);

  async function loadAdminOperations() {
    if (!hasStoredAccessToken()) {
      setAdminData(null);
      return;
    }

    setLoadingAdmin(true);
    try {
      const [payload, qualityReport, reviewQueuePayload] = await Promise.all([
        lawChatApi.getAdminOperations(),
        lawChatApi.getCorpusQualityReport(true),
        lawChatApi.getReviewQueues(),
      ]);
      setAdminData(payload);
      setCorpusQualityReport(qualityReport);
      setReviewQueues(reviewQueuePayload);
    } catch (caught) {
      if (axios.isAxiosError(caught) && caught.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      throw caught;
    } finally {
      setLoadingAdmin(false);
    }
  }

  useEffect(() => {
    if (!adminData?.graph_backend_insights) {
      return;
    }
    setGraphBenchmark(adminData.graph_backend_insights.benchmark);
    setGraphParity(adminData.graph_backend_insights.parity);
  }, [adminData]);

  async function loadGraphInsights() {
    setLoadingGraphInsights(true);
    setGraphInsightsMessage("Đang chạy benchmark và parity. Tác vụ này có thể mất vài chục giây nếu graph lớn.");
    try {
      const [benchmark, parity] = await Promise.all([
        lawChatApi.getGraphBackendBenchmark(),
        lawChatApi.getGraphBackendParity(),
      ]);
      setGraphBenchmark(benchmark);
      setGraphParity(parity);
      await loadAdminOperations();
      const matched = parity.results.filter((item) => item.node_count_match && item.edge_count_match && item.edge_identity_match && item.anchor_match).length;
      setGraphInsightsMessage(`Đã chạy xong và lưu kết quả benchmark/parity. Parity khớp ${matched}/${parity.results.length} case.`);
    } catch (caught) {
      if (axios.isAxiosError(caught) && caught.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      const message = axios.isAxiosError(caught)
        ? (caught.response?.data?.message ?? caught.message)
        : "Không chạy được benchmark/parity.";
      setGraphInsightsMessage(`Chạy benchmark/parity thất bại: ${message}`);
      setError(`Chạy benchmark/parity thất bại: ${message}`);
    } finally {
      setLoadingGraphInsights(false);
    }
  }

  const taxonomyOperations = useAdminTaxonomyOperations({
    loadAdminOperations,
    savingAdmin,
    setError,
    setKnowledge,
    setSavingAdmin,
    ui,
  });

  const userOperations = useAdminUsersManager({
    loadAdminOperations,
    savingAdmin,
    setError,
    setKnowledge,
    setSavingAdmin,
    ui,
  });

  const documentOperations = useAdminDocumentOperations({
    activeDocumentId: activeDocument?.id ?? null,
    loadAdminOperations,
    savingAdmin,
    setError,
    setKnowledge,
    setSavingAdmin,
    ui,
  });

  async function handleCreateContentArticle(payload: ContentArticleWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.createContentArticle(payload);
      await loadAdminOperations();
    } catch {
      setError("Không lưu được bài viết.");
      throw new Error("create-content-article-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateContentArticle(articleId: number, payload: ContentArticleWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateContentArticle(articleId, payload);
      await loadAdminOperations();
    } catch {
      setError("Không cập nhật được bài viết.");
      throw new Error("update-content-article-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteContentArticle(articleId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteContentArticle(articleId);
      await loadAdminOperations();
    } catch {
      setError("Không xóa được bài viết.");
      throw new Error("delete-content-article-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleCreateLawyerProfile(payload: LawyerProfileWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.createLawyerProfile(payload);
      await loadAdminOperations();
    } catch {
      setError("Không lưu được hồ sơ luật sư.");
      throw new Error("create-lawyer-profile-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateLawyerProfile(lawyerId: number, payload: LawyerProfileWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateLawyerProfile(lawyerId, payload);
      await loadAdminOperations();
    } catch {
      setError("Không cập nhật được hồ sơ luật sư.");
      throw new Error("update-lawyer-profile-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteLawyerProfile(lawyerId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteLawyerProfile(lawyerId);
      await loadAdminOperations();
    } catch {
      setError("Không xóa được hồ sơ luật sư.");
      throw new Error("delete-lawyer-profile-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  return {
    adminData,
    corpusQualityReport,
    reviewQueues,
    diagnosing: documentOperations.diagnosing,
    diagnostics: documentOperations.diagnostics,
    graphBenchmark,
    graphInsightsMessage,
    graphParity,
    handleCreateAdminUser: userOperations.handleCreateAdminUser,
    handleCreateAuthorityLevel: taxonomyOperations.handleCreateAuthorityLevel,
    handleCreateCategory: taxonomyOperations.handleCreateCategory,
    handleCreateContentArticle,
    handleCreateDocument: documentOperations.handleCreateDocument,
    handleCreateDocumentType: taxonomyOperations.handleCreateDocumentType,
    handleCreateLawyerProfile,
    handleDeleteAdminUser: userOperations.handleDeleteAdminUser,
    handleDeleteAuthorityLevel: taxonomyOperations.handleDeleteAuthorityLevel,
    handleDeleteCategory: taxonomyOperations.handleDeleteCategory,
    handleDeleteContentArticle,
    handleDeleteDocument: documentOperations.handleDeleteDocument,
    handleDeleteDocumentType: taxonomyOperations.handleDeleteDocumentType,
    handleDeleteLawyerProfile,
    handleIngest: documentOperations.handleIngest,
    handleLoadDocumentChunks: documentOperations.handleLoadDocumentChunks,
    handleLoadDocumentProvisions: documentOperations.handleLoadDocumentProvisions,
    handleLoadProvisionRelations: documentOperations.handleLoadProvisionRelations,
    handleRefreshDocumentStructure: documentOperations.handleRefreshDocumentStructure,
    handleReingestAllDocuments: documentOperations.handleReingestAllDocuments,
    handleReviewDocumentMetadata: documentOperations.handleReviewDocumentMetadata,
    handleToggleCategory: taxonomyOperations.handleToggleCategory,
    handleUpdateAdminUser: userOperations.handleUpdateAdminUser,
    handleUpdateAuthorityLevel: taxonomyOperations.handleUpdateAuthorityLevel,
    handleUpdateCategory: taxonomyOperations.handleUpdateCategory,
    handleUpdateContentArticle,
    handleUpdateDocument: documentOperations.handleUpdateDocument,
    handleUpdateDocumentType: taxonomyOperations.handleUpdateDocumentType,
    handleUpdateLawyerProfile,
    handleUpdateMetadataAISettings: documentOperations.handleUpdateMetadataAISettings,
    handleUploadAndIngestDocumentFile: documentOperations.handleUploadAndIngestDocumentFile,
    handleUploadDocumentFile: documentOperations.handleUploadDocumentFile,
    ingested: documentOperations.ingested,
    ingesting: documentOperations.ingesting,
    knowledgeMessage: documentOperations.knowledgeMessage,
    loadGraphInsights,
    loadAdminOperations,
    loadDiagnostics: documentOperations.loadDiagnostics,
    loadingGraphInsights,
    loadingAdmin,
    newCategoryDescription: taxonomyOperations.newCategoryDescription,
    newCategoryName: taxonomyOperations.newCategoryName,
    newCategorySlug: taxonomyOperations.newCategorySlug,
    savingAdmin,
    setNewCategoryDescription: taxonomyOperations.setNewCategoryDescription,
    setNewCategoryName: taxonomyOperations.setNewCategoryName,
    setNewCategorySlug: taxonomyOperations.setNewCategorySlug,
  };
}
