import type {
  AdminOperations,
  ApiEnvelope,
  AutoIngestedDocumentResult,
  Category,
  ContentArticleWritePayload,
  CorpusQualityReport,
  DefinitionItem,
  DocumentChunkItem,
  DocumentGraphPayload,
  DocumentItem,
  LegalProvisionItem,
  ProvisionRelationItem,
  DocumentWritePayload,
  DuplicateDocumentAction,
  DuplicateDocumentConflictData,
  ExtractionDiagnostic,
  GraphBackendBenchmarkPayload,
  GraphBackendParityPayload,
  LawyerProfileWritePayload,
  ReviewQueuesPayload,
  Ticket,
  UploadedDocumentFile,
} from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";

export const ADMIN_TABS = ["overview", "roadmap", "users", "documents", "annotation", "content-articles", "lawyer-profiles", "categories", "document-types", "authority-levels", "ai-settings", "tickets", "review-queues", "logs"] as const;
export const DOCUMENT_SOURCE_TYPES = ["pdf", "txt", "docx"] as const;
export const LEGAL_STATUS_VALUES = ["active", "expired", "repealed", "draft", "unknown"] as const;
export const DOCUMENT_EXTRACT_DRAFT_PREFIX = "lawchat.document-extract-draft";

export type AdminTab = (typeof ADMIN_TABS)[number];
export type DefinitionKind = "document-type" | "authority-level";
export type DocumentEditorMode = "rich" | "plain";
export type DocumentSortKey = "title" | "legal_status" | "signed_date";
export type SortDirection = "asc" | "desc";
export type DocumentFormPayload = DocumentWritePayload;

export interface AdminDashboardProps {
  activeTab: AdminTab;
  adminData: AdminOperations | null;
  corpusQualityReport: CorpusQualityReport | null;
  tickets: Ticket[];
  ingesting: boolean;
  diagnosing: boolean;
  diagnostics: ExtractionDiagnostic | null;
  graphBenchmark: GraphBackendBenchmarkPayload | null;
  graphInsightsMessage: string | null;
  graphParity: GraphBackendParityPayload | null;
  loadingAdmin: boolean;
  loadingGraphInsights: boolean;
  locale: Locale;
  reviewQueues: ReviewQueuesPayload | null;
  savingAdmin: boolean;
  ui: UiText;
  onLocaleChange: (locale: Locale) => void;
  onTabChange: (tab: AdminTab) => void;
  onClose: () => void;
  onCreateAdminUser: (payload: import("../../types/lawchat").AdminUserWritePayload) => Promise<void> | void;
  onRefresh: () => void;
  onRefreshGraphInsights: () => void;
  onUpdateMetadataSettings: (metadataEnabled: boolean, metadataProvider: string, model: string, webSearchEnabled: boolean, embeddingEnabled: boolean, embeddingModel: string, chatbotEnabled: boolean, chatbotProvider: string, publicChatbotModel: string, customerChatbotModel: string, consultantChatbotModel: string, graphBackend: string) => Promise<void> | void;
  onUpdateAdminUser: (userId: number, payload: import("../../types/lawchat").AdminUserWritePayload) => Promise<void> | void;
  onIngest: (documentId: number) => void | Promise<void>;
  onReingestAllDocuments: () => void;
  onRefreshDocumentStructure: (documentId: number) => Promise<void> | void;
  onLoadDocumentChunks: (documentId: number) => Promise<DocumentChunkItem[]>;
  onLoadDocumentProvisions: (documentId: number) => Promise<LegalProvisionItem[]>;
  onLoadProvisionRelations: (documentId: number) => Promise<ProvisionRelationItem[]>;
  onCreateCategory: (name: string, slug: string, description: string) => Promise<void> | void;
  onCreateContentArticle: (payload: ContentArticleWritePayload) => Promise<void> | void;
  onCreateLawyerProfile: (payload: LawyerProfileWritePayload) => Promise<void> | void;
  onCreateDocumentType: (name: string, slug: string, description: string, priority: number) => Promise<void> | void;
  onCreateAuthorityLevel: (name: string, slug: string, description: string, priority: number) => Promise<void> | void;
  onUpdateCategory: (categoryId: number, name: string, slug: string, description: string, isActive: boolean) => Promise<void> | void;
  onUpdateContentArticle: (articleId: number, payload: ContentArticleWritePayload) => Promise<void> | void;
  onUpdateLawyerProfile: (lawyerId: number, payload: LawyerProfileWritePayload) => Promise<void> | void;
  onUpdateDocumentType: (itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => Promise<void> | void;
  onUpdateAuthorityLevel: (itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => Promise<void> | void;
  onDeleteAdminUser: (userId: number) => Promise<void> | void;
  onDeleteCategory: (categoryId: number) => Promise<void> | void;
  onDeleteContentArticle: (articleId: number) => Promise<void> | void;
  onDeleteLawyerProfile: (lawyerId: number) => Promise<void> | void;
  onDeleteDocumentType: (itemId: number) => Promise<void> | void;
  onDeleteAuthorityLevel: (itemId: number) => Promise<void> | void;
  onCreateDocument: (payload: DocumentWritePayload, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">, extractedTextOverride?: string) => Promise<void> | void;
  onUploadDocumentFile: (file: File) => Promise<UploadedDocumentFile>;
  onUploadAndIngestDocumentFile: (file: File, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">) => Promise<AutoIngestedDocumentResult>;
  onUpdateDocument: (documentId: number, payload: DocumentWritePayload) => Promise<void> | void;
  onDeleteDocument: (documentId: number) => Promise<void> | void;
  onReviewDocumentMetadata: (documentId: number, notes?: string) => Promise<void> | void;
  onOpenTicket: (ticketId: number) => void;
  onLoadDiagnostics: (documentId: number) => Promise<void> | void;
  formatDateTime: (value: string) => string;
}

export type CategoryModalState =
  | { mode: "create"; category: null }
  | { mode: "edit"; category: Category }
  | null;

export type DefinitionModalState =
  | { kind: DefinitionKind; mode: "create"; item: null }
  | { kind: DefinitionKind; mode: "edit"; item: DefinitionItem }
  | null;

export type DocumentModalState =
  | { mode: "create"; document: null }
  | { mode: "edit"; document: DocumentItem }
  | null;

export type ChunkViewerState = {
  document: DocumentItem;
  chunks: DocumentChunkItem[];
  loading: boolean;
  error: string | null;
};

export type ProvisionViewerState = {
  document: DocumentItem;
  provisions: LegalProvisionItem[];
  loading: boolean;
  error: string | null;
};

export type ProvisionRelationViewerState = {
  document: DocumentItem;
  relations: ProvisionRelationItem[];
  loading: boolean;
  error: string | null;
};

export type GraphViewerState = {
  documentId: number;
  loading: boolean;
  error: string | null;
  graph: DocumentGraphPayload | null;
};

export type GraphConnection = {
  key: string;
  sourceId: number;
  targetId: number;
  sourceNode: DocumentGraphPayload["nodes"][number] | null;
  targetNode: DocumentGraphPayload["nodes"][number] | null;
  relations: DocumentGraphPayload["edges"][number][];
};

export type DuplicateResolutionState = {
  mode: "create_document" | "upload_and_ingest";
  conflict: DuplicateDocumentConflictData;
  payload?: DocumentFormPayload;
  extractedTextOverride?: string;
  file?: File;
  resolving: boolean;
};

export type DuplicateDocumentErrorEnvelope = ApiEnvelope<DuplicateDocumentConflictData>;
