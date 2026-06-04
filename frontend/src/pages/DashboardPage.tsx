import { useState } from "react";
import { useNavigate } from "react-router-dom";

import AdminDashboard, { type AdminTab } from "../components/AdminDashboard";
import { formatDateTime, useLawChatApp } from "../hooks/useLawChatApp";
import type { AdminUserWritePayload, ContentArticleWritePayload, DocumentWritePayload, LawyerProfileWritePayload } from "../types/lawchat";

type DocumentFormPayload = DocumentWritePayload;
type AdminUserFormPayload = AdminUserWritePayload;
type ContentArticleFormPayload = ContentArticleWritePayload;
type LawyerProfileFormPayload = LawyerProfileWritePayload;

export default function DashboardPage() {
  const navigate = useNavigate();
  const app = useLawChatApp({ loadAdmin: true, loadTickets: true });
  const [adminTab, setAdminTab] = useState<AdminTab>("overview");

  return (
    <main className="dashboard-page dashboard-page-modern app-shell">
      {app.error ? <div className="error-banner wide-banner">{app.error}</div> : null}

      <AdminDashboard
        activeTab={adminTab}
        adminData={app.adminData}
        corpusQualityReport={app.corpusQualityReport}
        diagnosing={app.diagnosing}
        diagnostics={app.diagnostics}
        graphBenchmark={app.graphBenchmark}
        graphInsightsMessage={app.graphInsightsMessage}
        graphParity={app.graphParity}
        formatDateTime={(value: string) => formatDateTime(value, app.locale)}
        ingesting={app.ingesting}
        loadingAdmin={app.loadingAdmin}
        loadingGraphInsights={app.loadingGraphInsights}
        locale={app.locale}
        onLocaleChange={app.setLocale}
        onClose={() => navigate("/")}
        onCreateAdminUser={(payload: AdminUserFormPayload) => app.handleCreateAdminUser(payload)}
        onCreateCategory={(name: string, slug: string, description: string) => app.handleCreateCategory(name, slug, description)}
        onCreateContentArticle={(payload: ContentArticleFormPayload) => app.handleCreateContentArticle(payload)}
        onCreateDocumentType={(name: string, slug: string, description: string, priority: number) => app.handleCreateDocumentType(name, slug, description, priority)}
        onCreateLawyerProfile={(payload: LawyerProfileFormPayload) => app.handleCreateLawyerProfile(payload)}
        onCreateAuthorityLevel={(name: string, slug: string, description: string, priority: number) => app.handleCreateAuthorityLevel(name, slug, description, priority)}
        onCreateDocument={(payload: DocumentFormPayload, duplicateAction, extractedTextOverride) => app.handleCreateDocument(payload, duplicateAction, extractedTextOverride)}
        onDeleteAuthorityLevel={(itemId: number) => app.handleDeleteAuthorityLevel(itemId)}
        onDeleteAdminUser={(userId: number) => app.handleDeleteAdminUser(userId)}
        onDeleteCategory={(categoryId: number) => app.handleDeleteCategory(categoryId)}
        onDeleteContentArticle={(articleId: number) => app.handleDeleteContentArticle(articleId)}
        onDeleteDocumentType={(itemId: number) => app.handleDeleteDocumentType(itemId)}
        onDeleteLawyerProfile={(lawyerId: number) => app.handleDeleteLawyerProfile(lawyerId)}
        onDeleteDocument={(documentId: number) => app.handleDeleteDocument(documentId)}
        onReviewDocumentMetadata={(documentId: number, notes?: string) => app.handleReviewDocumentMetadata(documentId, notes)}
        onIngest={(documentId: number) => void app.handleIngest(documentId)}
        onReingestAllDocuments={() => void app.handleReingestAllDocuments()}
        onRefreshDocumentStructure={(documentId: number) => app.handleRefreshDocumentStructure(documentId)}
        onLoadDocumentChunks={(documentId: number) => app.handleLoadDocumentChunks(documentId)}
        onLoadDocumentProvisions={(documentId: number) => app.handleLoadDocumentProvisions(documentId)}
        onLoadProvisionRelations={(documentId: number) => app.handleLoadProvisionRelations(documentId)}
        onLoadDiagnostics={(documentId: number) => app.loadDiagnostics(documentId)}
        onOpenTicket={(ticketId: number) => void app.loadTicketDetail(ticketId).then(() => navigate("/consultant"))}
        onRefresh={() => void app.loadAdminOperations()}
        onRefreshGraphInsights={() => void app.loadGraphInsights()}
        onTabChange={setAdminTab}
        onUpdateMetadataSettings={(metadataEnabled: boolean, metadataProvider: string, model: string, webSearchEnabled: boolean, embeddingEnabled: boolean, embeddingModel: string, chatbotEnabled: boolean, chatbotProvider: string, publicChatbotModel: string, customerChatbotModel: string, consultantChatbotModel: string, graphBackend: string) => app.handleUpdateMetadataAISettings(metadataEnabled, metadataProvider, model, webSearchEnabled, embeddingEnabled, embeddingModel, chatbotEnabled, chatbotProvider, publicChatbotModel, customerChatbotModel, consultantChatbotModel, graphBackend)}
        onUpdateAdminUser={(userId: number, payload: AdminUserFormPayload) => app.handleUpdateAdminUser(userId, payload)}
        onUpdateContentArticle={(articleId: number, payload: ContentArticleFormPayload) => app.handleUpdateContentArticle(articleId, payload)}
        onUploadDocumentFile={(file: File) => app.handleUploadDocumentFile(file)}
        onUploadAndIngestDocumentFile={(file: File, duplicateAction) => app.handleUploadAndIngestDocumentFile(file, duplicateAction)}
        onUpdateAuthorityLevel={(itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => app.handleUpdateAuthorityLevel(itemId, name, slug, description, priority, isActive)}
        onUpdateCategory={(categoryId: number, name: string, slug: string, description: string, isActive: boolean) => app.handleUpdateCategory(categoryId, name, slug, description, isActive)}
        onUpdateDocumentType={(itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => app.handleUpdateDocumentType(itemId, name, slug, description, priority, isActive)}
        onUpdateDocument={(documentId: number, payload: DocumentFormPayload) => app.handleUpdateDocument(documentId, payload)}
        onUpdateLawyerProfile={(lawyerId: number, payload: LawyerProfileFormPayload) => app.handleUpdateLawyerProfile(lawyerId, payload)}
        reviewQueues={app.reviewQueues}
        savingAdmin={app.savingAdmin}
        tickets={app.tickets}
        ui={app.ui}
      />
    </main>
  );
}
