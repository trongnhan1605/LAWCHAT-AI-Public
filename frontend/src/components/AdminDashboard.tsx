import { useMemo, useState } from "react";

import { translateTicketStatus, translateTopic } from "../locales/metadata";
import AdminUsersPanel from "./AdminUsersPanel";
import {
  EMPTY_DEFINITION_ITEMS,
  normalizeSearchValue,
} from "../features/admin-dashboard/helpers";
import { MenuIcon } from "../features/admin-dashboard/icons";
import {
  DocumentsSection,
} from "../features/admin-dashboard/documents";
import {
  ChunkViewerModal,
  DocumentModal,
  DuplicateResolutionModal,
  ProvisionRelationViewerModal,
  ProvisionViewerModal,
} from "../features/admin-dashboard/document-modals";
import {
  AdminDashboardSidebar,
  AdminDashboardTopbar,
  AdminLoadingState,
  FloatingAddButton,
  LogsSection,
  OverviewSection,
  ReviewQueuesSection,
  TicketsSection,
} from "../features/admin-dashboard/sections";
import { AISettingsSection } from "../features/admin-dashboard/ai-settings";
import { AnnotationSection } from "../features/admin-dashboard/annotation";
import { ContentArticlesSection, ContentManagementModal, LawyerProfilesSection, type ContentModalState } from "../features/admin-dashboard/content-management";
import { RoadmapSection } from "../features/admin-dashboard/roadmap";
import { CategoriesSection, CategoryModal, DefinitionModal, DefinitionsSection } from "../features/admin-dashboard/taxonomy";
import type { AdminDashboardProps } from "../features/admin-dashboard/types";
import type { ContentArticleWritePayload, LawyerProfileWritePayload } from "../types/lawchat";
import { useAdminTaxonomyManager } from "../features/admin-dashboard/useAdminTaxonomyManager";
import { useAdminDocumentsController } from "../features/admin-dashboard/useAdminDocumentsController";
import { useAdminAiSettings } from "../features/admin-dashboard/useAdminAiSettings";
import { useAnnotationGroundTruth } from "../features/admin-dashboard/useAnnotationGroundTruth";

export type { AdminTab } from "../features/admin-dashboard/types";

export default function AdminDashboard({
  activeTab,
  adminData,
  corpusQualityReport,
  tickets,
  ingesting,
  diagnosing,
  diagnostics,
  graphBenchmark,
  graphInsightsMessage,
  graphParity,
  loadingAdmin,
  loadingGraphInsights,
  locale,
  reviewQueues,
  savingAdmin,
  ui,
  onLocaleChange,
  onTabChange,
  onClose,
  onCreateAdminUser,
  onCreateContentArticle,
  onCreateLawyerProfile,
  onRefresh,
  onRefreshGraphInsights,
  onUpdateMetadataSettings,
  onUpdateAdminUser,
  onUpdateContentArticle,
  onUpdateLawyerProfile,
  onIngest,
  onReingestAllDocuments,
  onRefreshDocumentStructure,
  onLoadDocumentChunks,
  onLoadDocumentProvisions,
  onLoadProvisionRelations,
  onCreateCategory,
  onCreateDocumentType,
  onCreateAuthorityLevel,
  onUpdateCategory,
  onUpdateDocumentType,
  onUpdateAuthorityLevel,
  onDeleteAdminUser,
  onDeleteContentArticle,
  onDeleteLawyerProfile,
  onDeleteCategory,
  onDeleteDocumentType,
  onDeleteAuthorityLevel,
  onCreateDocument,
  onUploadDocumentFile,
  onUploadAndIngestDocumentFile,
  onUpdateDocument,
  onDeleteDocument,
  onReviewDocumentMetadata,
  onOpenTicket,
  onLoadDiagnostics,
  formatDateTime,
}: AdminDashboardProps) {
  const showsFloatingAddButton = activeTab === "categories" || activeTab === "document-types" || activeTab === "authority-levels" || activeTab === "documents" || activeTab === "content-articles" || activeTab === "lawyer-profiles";
  const actionsColumnLabel = locale === "vi" ? "Thao tac" : "Actions";
  const topicColumnLabel = locale === "vi" ? "Chu de" : "Topic";
  const reasonColumnLabel = locale === "vi" ? "Ly do" : "Reason";
  const titleColumnLabel = locale === "vi" ? "Tieu de" : "Title";
  const timeColumnLabel = locale === "vi" ? "Thoi gian" : "Time";

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktopSidebarCollapsed, setIsDesktopSidebarCollapsed] = useState(false);

  const [categorySearch, setCategorySearch] = useState("");
  const [articleSearch, setArticleSearch] = useState("");
  const [lawyerSearch, setLawyerSearch] = useState("");
  const [documentTypeSearch, setDocumentTypeSearch] = useState("");
  const [authorityLevelSearch, setAuthorityLevelSearch] = useState("");
  const [ticketSearch, setTicketSearch] = useState("");
  const [logSearch, setLogSearch] = useState("");
  const [contentModalState, setContentModalState] = useState<ContentModalState>(null);
  const [articleDraft, setArticleDraft] = useState<ContentArticleWritePayload>({
    title: "",
    slug: "",
    category: "",
    excerpt: "",
    source_url: null,
    is_featured: true,
    is_active: true,
  });
  const [lawyerDraft, setLawyerDraft] = useState<LawyerProfileWritePayload>({
    full_name: "",
    slug: "",
    title: "",
    location: "",
    specialties: "",
    experience_years: 0,
    rating: null,
    bio: null,
    avatar_url: null,
    is_featured: true,
    is_active: true,
  });

  const documentTypeDefinitions = adminData?.document_types ?? EMPTY_DEFINITION_ITEMS;
  const authorityLevelDefinitions = adminData?.authority_levels ?? EMPTY_DEFINITION_ITEMS;

  const documentsController = useAdminDocumentsController({
    adminData,
    locale,
    onCreateDocument,
    onDeleteDocument,
    onIngest,
    onLoadDocumentChunks,
    onLoadDocumentProvisions,
    onLoadProvisionRelations,
    onRefreshDocumentStructure,
    onReingestAllDocuments,
    onReviewDocumentMetadata,
    onUpdateDocument,
    onUploadAndIngestDocumentFile,
    onUploadDocumentFile,
    ui,
  });

  const {
    categoryModalState,
    categoryName,
    categorySlug,
    categoryDescription,
    categoryIsActive,
    definitionModalState,
    definitionName,
    definitionSlug,
    definitionDescription,
    definitionPriority,
    definitionIsActive,
    setCategoryName,
    setCategorySlug,
    setCategoryDescription,
    setCategoryIsActive,
    setDefinitionName,
    setDefinitionSlug,
    setDefinitionDescription,
    setDefinitionPriority,
    setDefinitionIsActive,
    openCreateCategoryModal,
    openEditCategoryModal,
    closeCategoryModal,
    openCreateDefinitionModal,
    openEditDefinitionModal,
    closeDefinitionModal,
    handleCategorySubmit,
    handleCategoryDelete,
    handleDefinitionSubmit,
    handleDefinitionDelete,
  } = useAdminTaxonomyManager({
    ui,
    onCreateCategory,
    onCreateDocumentType,
    onCreateAuthorityLevel,
    onUpdateCategory,
    onUpdateDocumentType,
    onUpdateAuthorityLevel,
    onDeleteCategory,
    onDeleteDocumentType,
    onDeleteAuthorityLevel,
  });

  const aiSettings = useAdminAiSettings({
    adminData,
    savingAdmin,
    onUpdateMetadataSettings,
  });

  const annotationGroundTruth = useAnnotationGroundTruth();
  const {
    chatbotEnabled,
    chatbotProvider,
    consultantChatbotModel,
    customerChatbotModel,
    embeddingEnabled,
    embeddingModel,
    graphBackend,
    metadataEnabled,
    metadataModel,
    metadataProvider,
    metadataWebSearchEnabled,
    publicChatbotModel,
    setChatbotEnabled,
    setChatbotProvider,
    setConsultantChatbotModel,
    setCustomerChatbotModel,
    setEmbeddingEnabled,
    setEmbeddingModel,
    setGraphBackend,
    setMetadataEnabled,
    setMetadataModel,
    setMetadataProvider,
    setMetadataWebSearchEnabled,
    setPublicChatbotModel,
    handleMetadataSettingsSubmit,
  } = aiSettings;
  const {
    annotationGroundTruthSave,
    annotationPreview,
    annotationPreviewDocumentId,
    annotationPreviewLoading,
    annotationSaveLoading,
    handleDownloadAnnotationGroundTruth,
    handleLoadAnnotationPreview,
    handleSaveAnnotationGroundTruth,
  } = annotationGroundTruth;

  const filteredCategories = useMemo(() => (adminData?.categories ?? []).filter((category) => {
    const normalizedSearch = normalizeSearchValue(categorySearch);
    return !normalizedSearch || [category.name, category.slug, category.description].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.categories, categorySearch]);
  const filteredArticles = useMemo(() => (adminData?.content_articles ?? []).filter((article) => {
    const normalizedSearch = normalizeSearchValue(articleSearch);
    return !normalizedSearch || [article.title, article.slug, article.category, article.excerpt].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.content_articles, articleSearch]);
  const filteredLawyers = useMemo(() => (adminData?.lawyer_profiles ?? []).filter((lawyer) => {
    const normalizedSearch = normalizeSearchValue(lawyerSearch);
    return !normalizedSearch || [lawyer.full_name, lawyer.slug, lawyer.title, lawyer.location, lawyer.specialties, lawyer.bio].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.lawyer_profiles, lawyerSearch]);

  const documentTypeStats = useMemo(() => documentTypeDefinitions.map((item) => ({
    ...item,
    count: (adminData?.documents ?? []).filter((document) => (document.document_type ?? "") === item.slug).length,
  })), [adminData?.documents, documentTypeDefinitions]);
  const authorityLevelStats = useMemo(() => authorityLevelDefinitions.map((item) => ({
    ...item,
    count: (adminData?.documents ?? []).filter((document) => (document.authority_level ?? "") === item.slug).length,
  })), [adminData?.documents, authorityLevelDefinitions]);
  const filteredDocumentTypeStats = useMemo(() => documentTypeStats.filter((item) => {
    const normalizedSearch = normalizeSearchValue(documentTypeSearch);
    return !normalizedSearch || [item.name, item.slug, item.description].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [documentTypeSearch, documentTypeStats]);
  const filteredAuthorityLevelStats = useMemo(() => authorityLevelStats.filter((item) => {
    const normalizedSearch = normalizeSearchValue(authorityLevelSearch);
    return !normalizedSearch || [item.name, item.slug, item.description].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [authorityLevelSearch, authorityLevelStats]);

  const filteredTickets = useMemo(() => tickets.filter((ticket) => {
    const normalizedSearch = normalizeSearchValue(ticketSearch);
    return !normalizedSearch || [
      ticket.title,
      ticket.escalation_reason,
      translateTopic(locale, ticket.topic),
      translateTicketStatus(locale, ticket.status),
    ].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [locale, ticketSearch, tickets]);

  const filteredActivities = useMemo(() => (adminData?.activities ?? []).filter((activity) => {
    const normalizedSearch = normalizeSearchValue(logSearch);
    return !normalizedSearch || [activity.title, activity.description, activity.event_type].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.activities, logSearch]);
  const filteredLegalCases = useMemo(() => (adminData?.recent_legal_cases ?? []).filter((legalCase) => {
    const normalizedSearch = normalizeSearchValue(logSearch);
    return !normalizedSearch || [
      legalCase.title,
      legalCase.legal_domain,
      legalCase.status,
      legalCase.risk_level,
      legalCase.summary,
      legalCase.desired_outcome,
    ].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.recent_legal_cases, logSearch]);
  const filteredPlannerRuns = useMemo(() => (adminData?.recent_planner_runs ?? []).filter((run) => {
    const normalizedSearch = normalizeSearchValue(logSearch);
    return !normalizedSearch || [
      run.query_text,
      run.detected_domain,
      run.detected_intent,
      run.complexity_level,
      run.status,
    ].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.recent_planner_runs, logSearch]);
  const filteredValidationRuns = useMemo(() => (adminData?.recent_validation_runs ?? []).filter((run) => {
    const normalizedSearch = normalizeSearchValue(logSearch);
    return !normalizedSearch || [
      run.validation_status,
      run.confidence_score?.toString(),
      run.planner_run_id?.toString(),
      run.reasoning_run_id?.toString(),
      run.escalation_recommended ? "escalation" : "no-escalation",
    ].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
  }), [adminData?.recent_validation_runs, logSearch]);

  function openCreateArticleModal() {
    setArticleDraft({ title: "", slug: "", category: "", excerpt: "", source_url: null, is_featured: true, is_active: true });
    setContentModalState({ kind: "article", mode: "create", item: null });
  }

  function openEditArticleModal(item: NonNullable<typeof adminData>["content_articles"][number]) {
    setArticleDraft({
      title: item.title,
      slug: item.slug,
      category: item.category,
      excerpt: item.excerpt,
      source_url: item.source_url,
      is_featured: item.is_featured,
      is_active: item.is_active,
    });
    setContentModalState({ kind: "article", mode: "edit", item });
  }

  function openCreateLawyerModal() {
    setLawyerDraft({ full_name: "", slug: "", title: "", location: "", specialties: "", experience_years: 0, rating: null, bio: null, avatar_url: null, is_featured: true, is_active: true });
    setContentModalState({ kind: "lawyer", mode: "create", item: null });
  }

  function openEditLawyerModal(item: NonNullable<typeof adminData>["lawyer_profiles"][number]) {
    setLawyerDraft({
      full_name: item.full_name,
      slug: item.slug,
      title: item.title,
      location: item.location,
      specialties: item.specialties,
      experience_years: item.experience_years,
      rating: item.rating,
      bio: item.bio,
      avatar_url: item.avatar_url,
      is_featured: item.is_featured,
      is_active: item.is_active,
    });
    setContentModalState({ kind: "lawyer", mode: "edit", item });
  }

  async function handleContentSubmit() {
    if (!contentModalState) {
      return;
    }
    if (contentModalState.kind === "article") {
      if (contentModalState.mode === "edit") {
        await onUpdateContentArticle(contentModalState.item.id, articleDraft);
      } else {
        await onCreateContentArticle(articleDraft);
      }
    } else if (contentModalState.mode === "edit") {
      await onUpdateLawyerProfile(contentModalState.item.id, lawyerDraft);
    } else {
      await onCreateLawyerProfile(lawyerDraft);
    }
    setContentModalState(null);
  }

  return (
    <section className="admin-screen-wrap">
      <div className={`admin-sidebar-backdrop ${isSidebarOpen ? "open" : ""}`} onClick={() => setIsSidebarOpen(false)} />

      <div className="admin-mobile-bar">
        <button className="admin-mobile-menu" onClick={() => setIsSidebarOpen(true)} type="button">
          <MenuIcon />
        </button>
        <div className="admin-mobile-copy">
          <strong>LawChat-AI</strong>
          <span>{ui.adminPageTitle}</span>
        </div>
      </div>

      <div className={`admin-dashboard-shell admin-dashboard-shell-modern ${isDesktopSidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <AdminDashboardSidebar
          activeTab={activeTab}
          isDesktopSidebarCollapsed={isDesktopSidebarCollapsed}
          isSidebarOpen={isSidebarOpen}
          locale={locale}
          onClose={onClose}
          onHideMobileSidebar={() => setIsSidebarOpen(false)}
          onTabChange={onTabChange}
        />

        <section className={`admin-content admin-content-modern ${showsFloatingAddButton ? "admin-content-with-floating-add" : ""}`}>
          <AdminDashboardTopbar
            activeTab={activeTab}
            isDesktopSidebarCollapsed={isDesktopSidebarCollapsed}
            isDocumentFiltersVisible={documentsController.isDocumentFiltersVisible}
            loadingAdmin={loadingAdmin}
            locale={locale}
            ui={ui}
            onLocaleChange={onLocaleChange}
            onRefresh={onRefresh}
            onToggleDesktopSidebar={() => setIsDesktopSidebarCollapsed((current) => !current)}
            onToggleDocumentFilters={() => documentsController.setIsDocumentFiltersVisible((current: boolean) => !current)}
          />

          {loadingAdmin && !adminData ? <AdminLoadingState locale={locale} /> : null}
          {activeTab === "overview" && adminData ? <OverviewSection adminData={adminData} locale={locale} ui={ui} /> : null}
          {activeTab === "roadmap" ? <RoadmapSection locale={locale} onTabChange={onTabChange} /> : null}

          {activeTab === "users" && adminData ? (
            <AdminUsersPanel
              formatDateTime={formatDateTime}
              locale={locale}
              onCreateAdminUser={onCreateAdminUser}
              onDeleteAdminUser={onDeleteAdminUser}
              onUpdateAdminUser={onUpdateAdminUser}
              savingAdmin={savingAdmin}
              ui={ui}
              users={adminData.users}
            />
          ) : null}

          {activeTab === "documents" && adminData ? (
            <DocumentsSection
              actionsColumnLabel={actionsColumnLabel}
              adminData={adminData}
              corpusQualityReport={corpusQualityReport}
              currentDocumentPage={documentsController.currentDocumentPage}
              diagnosing={diagnosing}
              diagnostics={diagnostics}
              documentDomainFilter={documentsController.documentDomainFilter}
              documentFormatDateTime={formatDateTime}
              documentPageSize={documentsController.documentPageSize}
              documentSearch={documentsController.documentSearch}
              documentSortDirection={documentsController.documentSortDirection}
              documentSortKey={documentsController.documentSortKey}
              documentStatusFilter={documentsController.documentStatusFilter}
              expandedDocumentIds={documentsController.expandedDocumentIds}
              graphConnections={documentsController.graphConnections}
              graphViewerState={documentsController.graphViewerState}
              ingesting={ingesting}
              isDocumentFiltersVisible={documentsController.isDocumentFiltersVisible}
              locale={locale}
              paginatedDocuments={documentsController.paginatedDocuments}
              paginationEnd={documentsController.paginationEnd}
              paginationStart={documentsController.paginationStart}
              selectedGraphConnection={documentsController.selectedGraphConnection}
              sortedDocumentsLength={documentsController.sortedDocuments.length}
              statusFilterOptions={documentsController.statusFilterOptions}
              totalDocumentPages={documentsController.totalDocumentPages}
              ui={ui}
              onClearFilters={() => { documentsController.setDocumentSearch(""); documentsController.setDocumentStatusFilter("all"); documentsController.setDocumentDomainFilter("all"); }}
              onDeleteDocument={(documentId) => void documentsController.handleDocumentDelete(documentId)}
              onDocumentDomainFilterChange={documentsController.setDocumentDomainFilter}
              onDocumentPageChange={documentsController.setDocumentPage}
              onDocumentPageSizeChange={documentsController.setDocumentPageSize}
              onDocumentSearchChange={documentsController.setDocumentSearch}
              onDocumentSort={documentsController.handleDocumentSort}
              onDocumentStatusFilterChange={documentsController.setDocumentStatusFilter}
              onDownloadSource={documentsController.handleDownloadSource}
              onEditDocument={documentsController.openEditDocumentModal}
              onLoadDiagnostics={(documentId) => void onLoadDiagnostics(documentId)}
              onLoadDocumentChunks={(document) => void documentsController.loadDocumentChunks(document)}
              onLoadDocumentProvisions={(document) => void documentsController.loadDocumentProvisions(document)}
              onLoadProvisionRelations={(document) => void documentsController.loadProvisionRelations(document)}
              onLoadDocumentGraph={(document) => void documentsController.loadDocumentGraph(document)}
              onMarkDocumentReviewed={(document) => void documentsController.handleMarkDocumentReviewed(document)}
              onSelectGraphConnection={documentsController.setSelectedGraphConnectionKey}
              onToggleDocumentExpanded={documentsController.toggleDocumentExpanded}
              onReingestAll={documentsController.handleReingestAll}
            />
          ) : null}

          {activeTab === "annotation" && adminData ? (
            <AnnotationSection
              adminData={adminData}
              annotationGroundTruthSave={annotationGroundTruthSave}
              annotationPreview={annotationPreview}
              annotationPreviewDocumentId={annotationPreviewDocumentId}
              annotationPreviewLoading={annotationPreviewLoading}
              annotationSaveLoading={annotationSaveLoading}
              locale={locale}
              onDownloadAnnotationGroundTruth={(fileName) => void handleDownloadAnnotationGroundTruth(fileName)}
              onLoadAnnotationPreview={(documentId) => void handleLoadAnnotationPreview(documentId)}
              onSaveAnnotationGroundTruth={(payload) => void handleSaveAnnotationGroundTruth(payload)}
            />
          ) : null}

          {activeTab === "content-articles" && adminData ? (
            <ContentArticlesSection
              actionsColumnLabel={actionsColumnLabel}
              articles={filteredArticles}
              locale={locale}
              search={articleSearch}
              ui={ui}
              onClear={() => setArticleSearch("")}
              onDelete={(articleId) => void onDeleteContentArticle(articleId)}
              onEdit={openEditArticleModal}
              onSearchChange={setArticleSearch}
            />
          ) : null}

          {activeTab === "lawyer-profiles" && adminData ? (
            <LawyerProfilesSection
              actionsColumnLabel={actionsColumnLabel}
              lawyers={filteredLawyers}
              locale={locale}
              search={lawyerSearch}
              ui={ui}
              onClear={() => setLawyerSearch("")}
              onDelete={(lawyerId) => void onDeleteLawyerProfile(lawyerId)}
              onEdit={openEditLawyerModal}
              onSearchChange={setLawyerSearch}
            />
          ) : null}

          {activeTab === "categories" && adminData ? (
            <CategoriesSection
              actionsColumnLabel={actionsColumnLabel}
              filteredCategories={filteredCategories}
              locale={locale}
              search={categorySearch}
              ui={ui}
              onClear={() => setCategorySearch("")}
              onDelete={(categoryId) => void handleCategoryDelete(categoryId)}
              onEdit={openEditCategoryModal}
              onSearchChange={setCategorySearch}
            />
          ) : null}

          {activeTab === "document-types" && adminData ? (
            <DefinitionsSection
              actionsColumnLabel={actionsColumnLabel}
              items={filteredDocumentTypeStats}
              kind="document-type"
              locale={locale}
              search={documentTypeSearch}
              ui={ui}
              onClear={() => setDocumentTypeSearch("")}
              onDelete={(itemId) => void handleDefinitionDelete("document-type", itemId)}
              onEdit={(item) => openEditDefinitionModal("document-type", item)}
              onSearchChange={setDocumentTypeSearch}
            />
          ) : null}

          {activeTab === "authority-levels" && adminData ? (
            <DefinitionsSection
              actionsColumnLabel={actionsColumnLabel}
              items={filteredAuthorityLevelStats}
              kind="authority-level"
              locale={locale}
              search={authorityLevelSearch}
              ui={ui}
              onClear={() => setAuthorityLevelSearch("")}
              onDelete={(itemId) => void handleDefinitionDelete("authority-level", itemId)}
              onEdit={(item) => openEditDefinitionModal("authority-level", item)}
              onSearchChange={setAuthorityLevelSearch}
            />
          ) : null}

          {activeTab === "ai-settings" && adminData ? (
            <AISettingsSection
              adminData={adminData}
              chatbotEnabled={chatbotEnabled}
              chatbotProvider={chatbotProvider}
              consultantChatbotModel={consultantChatbotModel}
              graphBenchmark={graphBenchmark}
              graphInsightsMessage={graphInsightsMessage}
              graphBackend={graphBackend}
              graphParity={graphParity}
              customerChatbotModel={customerChatbotModel}
              embeddingEnabled={embeddingEnabled}
              embeddingModel={embeddingModel}
              loadingGraphInsights={loadingGraphInsights}
              locale={locale}
              metadataEnabled={metadataEnabled}
              metadataProvider={metadataProvider}
              metadataModel={metadataModel}
              metadataWebSearchEnabled={metadataWebSearchEnabled}
              publicChatbotModel={publicChatbotModel}
              savingAdmin={savingAdmin}
              ui={ui}
              onChatbotEnabledChange={setChatbotEnabled}
              onChatbotProviderChange={setChatbotProvider}
              onConsultantModelChange={setConsultantChatbotModel}
              onCustomerModelChange={setCustomerChatbotModel}
              onGraphBackendChange={setGraphBackend}
              onEmbeddingEnabledChange={setEmbeddingEnabled}
              onEmbeddingModelChange={setEmbeddingModel}
              onMetadataEnabledChange={setMetadataEnabled}
              onMetadataProviderChange={setMetadataProvider}
              onMetadataModelChange={setMetadataModel}
              onMetadataWebSearchChange={setMetadataWebSearchEnabled}
              onPublicModelChange={setPublicChatbotModel}
              onRefreshGraphInsights={() => void onRefreshGraphInsights()}
              onSave={() => void handleMetadataSettingsSubmit()}
            />
          ) : null}

          {activeTab === "tickets" ? (
            <TicketsSection
              actionsColumnLabel={actionsColumnLabel}
              locale={locale}
              reasonColumnLabel={reasonColumnLabel}
              search={ticketSearch}
              tickets={filteredTickets}
              titleColumnLabel={titleColumnLabel}
              topicColumnLabel={topicColumnLabel}
              ui={ui}
              onClear={() => setTicketSearch("")}
              onOpenTicket={onOpenTicket}
              onSearchChange={setTicketSearch}
            />
          ) : null}

          {activeTab === "review-queues" ? (
            <ReviewQueuesSection
              formatDateTime={formatDateTime}
              locale={locale}
              reviewQueues={reviewQueues}
              timeColumnLabel={timeColumnLabel}
              titleColumnLabel={titleColumnLabel}
              ui={ui}
            />
          ) : null}

          {activeTab === "logs" && adminData ? (
            <LogsSection
              activities={filteredActivities}
              formatDateTime={formatDateTime}
              legalCases={filteredLegalCases}
              locale={locale}
              plannerRuns={filteredPlannerRuns}
              search={logSearch}
              timeColumnLabel={timeColumnLabel}
              titleColumnLabel={titleColumnLabel}
              ui={ui}
              validationRuns={filteredValidationRuns}
              onClear={() => setLogSearch("")}
              onSearchChange={setLogSearch}
            />
          ) : null}
        </section>
      </div>

      {showsFloatingAddButton ? (
        <FloatingAddButton
          activeTab={activeTab}
          ui={ui}
          onOpenCreateAuthorityLevel={() => openCreateDefinitionModal("authority-level")}
          onOpenCreateCategory={openCreateCategoryModal}
          onOpenCreateContentArticle={openCreateArticleModal}
          onOpenCreateDocument={documentsController.openCreateDocumentModal}
          onOpenCreateDocumentType={() => openCreateDefinitionModal("document-type")}
          onOpenCreateLawyerProfile={openCreateLawyerModal}
        />
      ) : null}

      <ContentManagementModal
        article={articleDraft}
        lawyer={lawyerDraft}
        locale={locale}
        modalState={contentModalState}
        savingAdmin={savingAdmin}
        onArticleChange={setArticleDraft}
        onClose={() => setContentModalState(null)}
        onLawyerChange={setLawyerDraft}
        onSubmit={() => void handleContentSubmit()}
      />

      <CategoryModal
        categoryDescription={categoryDescription}
        categoryIsActive={categoryIsActive}
        categoryModalState={categoryModalState}
        categoryName={categoryName}
        categorySlug={categorySlug}
        locale={locale}
        savingAdmin={savingAdmin}
        ui={ui}
        onCategoryDescriptionChange={setCategoryDescription}
        onCategoryIsActiveChange={setCategoryIsActive}
        onCategoryNameChange={setCategoryName}
        onCategorySlugChange={setCategorySlug}
        onClose={closeCategoryModal}
        onSubmit={() => void handleCategorySubmit()}
      />

      <DefinitionModal
        definitionDescription={definitionDescription}
        definitionIsActive={definitionIsActive}
        definitionModalState={definitionModalState}
        definitionName={definitionName}
        definitionPriority={definitionPriority}
        definitionSlug={definitionSlug}
        locale={locale}
        savingAdmin={savingAdmin}
        ui={ui}
        onClose={closeDefinitionModal}
        onDefinitionDescriptionChange={setDefinitionDescription}
        onDefinitionIsActiveChange={setDefinitionIsActive}
        onDefinitionNameChange={setDefinitionName}
        onDefinitionPriorityChange={setDefinitionPriority}
        onDefinitionSlugChange={setDefinitionSlug}
        onSubmit={() => void handleDefinitionSubmit()}
      />

      <DocumentModal
        applyingOcrCorrection={documentsController.applyingOcrCorrection}
        authorityLevel={documentsController.documentAuthorityLevel}
        authorityLevelOptions={documentsController.authorityLevelOptions}
        canRestoreExtractedText={documentsController.canRestoreExtractedText}
        documentCode={documentsController.documentCode}
        documentEditorMode={documentsController.documentEditorMode}
        documentEditorNotice={documentsController.documentEditorNotice}
        documentEditorRef={documentsController.documentEditorRef}
        documentEditorReplace={documentsController.documentEditorReplace}
        documentEditorSearch={documentsController.documentEditorSearch}
        documentEffectiveDate={documentsController.documentEffectiveDate}
        documentExpiryDate={documentsController.documentExpiryDate}
        documentExtractedCharacters={documentsController.documentExtractedCharacters}
        documentExtractedText={documentsController.documentExtractedText}
        documentFileName={documentsController.documentFileName}
        documentIsActive={documentsController.documentIsActive}
        documentIssuingAuthority={documentsController.documentIssuingAuthority}
        documentLegalDomain={documentsController.documentLegalDomain}
        documentLegalStatus={documentsController.documentLegalStatus}
        documentModalState={documentsController.documentModalState}
        documentOcrSuggestions={documentsController.documentOcrSuggestions}
        documentSearchMatchCount={documentsController.documentSearchMatchCount}
        documentSignedDate={documentsController.documentSignedDate}
        documentSourceReference={documentsController.documentSourceReference}
        documentStoragePath={documentsController.documentStoragePath}
        documentSummary={documentsController.documentSummary}
        documentTitle={documentsController.documentTitle}
        documentType={documentsController.documentType}
        documentTypeOptions={documentsController.documentTypeOptions}
        documentUploadHelpText={documentsController.documentUploadHelpText}
        fileInputRef={documentsController.fileInputRef}
        hasDocumentExtractDraft={documentsController.hasDocumentExtractDraft}
        legalDomainOptions={documentsController.legalDomainOptions}
        legalStatusOptions={documentsController.legalStatusOptions}
        locale={locale}
        savingAdmin={savingAdmin}
        ui={ui}
        uploadingDocumentFile={documentsController.uploadingDocumentFile}
        onApplyOcrCorrection={() => void documentsController.handleApplyOcrCorrection()}
        onAuthorityLevelChange={documentsController.setDocumentAuthorityLevel}
        onClearExtractedTextDraft={documentsController.handleClearExtractedTextDraft}
        onClose={documentsController.closeDocumentModal}
        onDocumentCodeChange={documentsController.setDocumentCode}
        onDocumentEffectiveDateChange={documentsController.setDocumentEffectiveDate}
        onDocumentEditorModeChange={documentsController.setDocumentEditorMode}
        onDocumentEditorReplaceChange={documentsController.setDocumentEditorReplace}
        onDocumentEditorSearchChange={documentsController.setDocumentEditorSearch}
        onDocumentExpiryDateChange={documentsController.setDocumentExpiryDate}
        onDocumentExtractedTextChange={documentsController.setDocumentExtractedText}
        onDocumentFileNameChange={documentsController.setDocumentFileName}
        onDocumentFindNext={documentsController.handleFindNextInDocument}
        onDocumentIsActiveChange={documentsController.setDocumentIsActive}
        onDocumentIssuingAuthorityChange={documentsController.setDocumentIssuingAuthority}
        onDocumentLegalDomainChange={documentsController.setDocumentLegalDomain}
        onDocumentLegalStatusChange={(value) => documentsController.setDocumentLegalStatus(value as "active" | "expired" | "repealed" | "draft" | "unknown")}
        onDocumentSignedDateChange={documentsController.setDocumentSignedDate}
        onDocumentSourceReferenceChange={documentsController.setDocumentSourceReference}
        onDocumentSummaryChange={documentsController.setDocumentSummary}
        onDocumentTitleChange={documentsController.setDocumentTitle}
        onDocumentTypeChange={documentsController.setDocumentType}
        onFileSelection={(event) => void documentsController.handleDocumentFileSelection(event)}
        onJoinBrokenLines={documentsController.handleJoinBrokenLines}
        onNormalizeWhitespace={documentsController.handleNormalizeWhitespace}
        onRemoveBlankLines={documentsController.handleRemoveBlankLines}
        onReplaceAll={documentsController.handleReplaceAllInDocument}
        onRestoreExtractedText={documentsController.handleRestoreExtractedText}
        onSplitLegalHeadings={documentsController.handleSplitLegalHeadings}
        onSubmit={() => void documentsController.handleDocumentSubmit()}
      />

      <ChunkViewerModal
        chunkViewerState={documentsController.chunkViewerState}
        ingesting={ingesting}
        ui={ui}
        onClose={documentsController.closeChunkViewer}
        onRefresh={(document) => void documentsController.loadDocumentChunks(document)}
        onReingest={(document) => void documentsController.handleChunkReingest(document)}
      />

      <ProvisionViewerModal
        provisionViewerState={documentsController.provisionViewerState}
        ui={ui}
        onClose={documentsController.closeProvisionViewer}
        onRefresh={(document) => void documentsController.loadDocumentProvisions(document)}
        onSync={(document) => void documentsController.handleSyncDocumentStructure(document, "provisions")}
      />
      <ProvisionRelationViewerModal
        provisionRelationViewerState={documentsController.provisionRelationViewerState}
        ui={ui}
        onClose={documentsController.closeProvisionRelationViewer}
        onRefresh={(document) => void documentsController.loadProvisionRelations(document)}
        onSync={(document) => void documentsController.handleSyncDocumentStructure(document, "relations")}
      />

      <DuplicateResolutionModal
        duplicateResolutionState={documentsController.duplicateResolutionState}
        ui={ui}
        onClose={documentsController.closeDuplicateResolution}
        onResolve={(action) => void documentsController.handleDuplicateResolution(action)}
      />
    </section>
  );
}
