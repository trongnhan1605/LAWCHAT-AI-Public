import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { lawChatApi } from "../api/lawchat.api";
import { UI_TEXT, type Locale } from "../locales";
import { useAuthStore } from "../store/auth.store";
import { useAdminOperations } from "./useAdminOperations";
import { useTicketOperations } from "./useTicketOperations";
import type {
  ChatMessage,
  ChatSession,
  DocumentItem,
  KnowledgeOverview,
  Ticket,
} from "../types/lawchat";

const SESSION_STORAGE_KEY = "lawchat.chat.session_token";
const CUSTOMER_SESSION_STORAGE_KEY = "lawchat.customer_chat.session_token";
const LOCALE_STORAGE_KEY = "lawchat.ui.locale";

type SessionMode = "public" | "customer";

interface UseLawChatAppOptions {
  sessionMode?: SessionMode;
  loadTickets?: boolean;
  loadAdmin?: boolean;
}

const QUICK_PROMPTS: Record<Locale, readonly string[]> = {
  vi: [
    "Con nuôi có được hưởng quyền và nghĩa vụ như con đẻ không?",
    "Mang thai hộ vì mục đích nhân đạo cần đáp ứng những điều kiện nào?",
    "Văn bản hộ tịch cũ này còn hiệu lực hay đã bị thay thế?",
  ],
  en: [
    "Do adopted children have the same rights and obligations as biological children?",
    "What conditions apply to altruistic surrogacy?",
    "Is this older civil-status document still valid or has it been replaced?",
  ],
};

function buildOptimisticMessage(overrides: Partial<ChatMessage> & Pick<ChatMessage, "id" | "role" | "message_type" | "content">): ChatMessage {
  return {
    id: overrides.id,
    role: overrides.role,
    message_type: overrides.message_type,
    content: overrides.content,
    category_slug: overrides.category_slug ?? null,
    confidence_score: overrides.confidence_score ?? null,
    warning_text: overrides.warning_text ?? null,
    citation: overrides.citation ?? null,
    needs_escalation: overrides.needs_escalation ?? false,
    created_at: overrides.created_at ?? new Date().toISOString(),
  };
}

const ACCESS_TOKEN_KEY = "lawchat.access_token";

function hasStoredAccessToken(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return Boolean(window.localStorage.getItem(ACCESS_TOKEN_KEY));
}

export function useLawChatApp(options: UseLawChatAppOptions = {}) {
  const sessionMode = options.sessionMode ?? "public";
  const shouldLoadTickets = options.loadTickets ?? false;
  const shouldLoadAdmin = options.loadAdmin ?? false;
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeOverview | null>(null);
  const [draft, setDraft] = useState("");
  const [booting, setBooting] = useState(true);
  const [sending, setSending] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [widgetOpen, setWidgetOpen] = useState(true);
  const [locale, setLocale] = useState<Locale>(() => {
    if (typeof window === "undefined") {
      return "vi";
    }

    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return stored === "en" ? "en" : "vi";
  });
  const ui = UI_TEXT[locale];
  const quickPrompts = QUICK_PROMPTS[locale];
  const activeDocument = useMemo<DocumentItem | null>(() => knowledge?.documents[0] ?? null, [knowledge]);
  const widgetMessages = useMemo(() => messages.slice(-6), [messages]);
  const handleUnauthorized = useCallback(() => {
    useAuthStore.getState().logout();
    setError(locale === "vi" ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại." : "Your session has expired. Please sign in again.");
  }, [locale]);

  const ticketOperations = useTicketOperations({
    handleUnauthorized,
    ui,
  });

  const adminOperations = useAdminOperations({
    activeDocument,
    handleUnauthorized,
    setError,
    setKnowledge,
    ui,
  });

  useEffect(() => {
    async function initializeApp() {
      setBooting(true);
      setError(null);

      try {
        const [resolvedSession, overview] = await Promise.all([restoreOrCreateSession(sessionMode), lawChatApi.getKnowledgeOverview()]);
        setSession(resolvedSession.session);
        setMessages(resolvedSession.messages);
        setKnowledge(overview);
        const canLoadProtectedData = hasStoredAccessToken();
        await Promise.all([
          shouldLoadTickets && canLoadProtectedData ? ticketOperations.loadTickets() : Promise.resolve(),
          shouldLoadAdmin && canLoadProtectedData ? adminOperations.loadAdminOperations() : Promise.resolve(),
        ]);
        if (overview.documents[0]) {
          void adminOperations.loadDiagnostics(overview.documents[0].id);
        }
      } catch {
        setError(UI_TEXT[locale].appInitializeError);
      } finally {
        setBooting(false);
      }
    }

    void initializeApp();
  }, [locale, sessionMode, shouldLoadAdmin, shouldLoadTickets]);

  useEffect(() => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  }, [locale]);

  async function restoreOrCreateSession(mode: SessionMode) {
    if (mode === "customer") {
      const existing = window.localStorage.getItem(CUSTOMER_SESSION_STORAGE_KEY);
      if (existing) {
        try {
          return await lawChatApi.getSession(existing);
        } catch {
          window.localStorage.removeItem(CUSTOMER_SESSION_STORAGE_KEY);
        }
      }

      const latest = await lawChatApi.getLatestCustomerSession();
      window.localStorage.setItem(CUSTOMER_SESSION_STORAGE_KEY, latest.session.session_token);
      return latest;
    }

    const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) {
      try {
        return await lawChatApi.getSession(existing);
      } catch {
        window.localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    }

    const created = await lawChatApi.createSession();
    window.localStorage.setItem(SESSION_STORAGE_KEY, created.session_token);
    return { session: created, messages: [] };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !draft.trim() || sending) {
      return;
    }

    const question = draft.trim();
    const optimisticUserId = -Date.now();
    const optimisticAssistantId = optimisticUserId - 1;
    const optimisticUserMessage = buildOptimisticMessage({
      id: optimisticUserId,
      role: "user",
      message_type: "question",
      content: question,
      category_slug: session.topic_guess,
    });
    const optimisticAssistantMessage = buildOptimisticMessage({
      id: optimisticAssistantId,
      role: "assistant",
      message_type: "status",
      content: ui.assistantThinking,
    });

    setSending(true);
    setError(null);
    setDraft("");
    setWidgetOpen(true);
    setMessages((current) => [...current, optimisticUserMessage, optimisticAssistantMessage]);

    try {
      const payload = await lawChatApi.ask(session.session_token, question);
      setSession(payload.session);
      const sessionStorageKey = payload.session.session_type === "customer" ? CUSTOMER_SESSION_STORAGE_KEY : SESSION_STORAGE_KEY;
      window.localStorage.setItem(sessionStorageKey, payload.session.session_token);
      setMessages((current) => current.map((message) => {
        if (message.id === optimisticUserId) {
          return payload.user_message;
        }
        if (message.id === optimisticAssistantId) {
          return payload.assistant_message;
        }
        return message;
      }));
    } catch {
      setMessages((current) => current.map((message) => {
        if (message.id === optimisticAssistantId) {
          return {
            ...message,
            message_type: "error",
            content: ui.appAskError,
            warning_text: ui.appAskError,
          };
        }
        return message;
      }));
      setError(ui.appAskError);
    } finally {
      setSending(false);
    }
  }

  async function handleEscalate() {
    if (!session || escalating) {
      return;
    }

    setEscalating(true);
    setError(null);

    try {
      const created = await lawChatApi.escalate(
        session.session_token,
        ui.appEscalateReason,
      );
      setTicket(created);
      await ticketOperations.loadTickets(created.id);
      setSession((current) => (current ? { ...current, status: "escalated", escalated_ticket_id: created.id } : current));
    } catch {
      setError(ui.appEscalateError);
    } finally {
      setEscalating(false);
    }
  }

  return {
    activeDocument,
    activeTicketId: ticketOperations.activeTicketId,
    adminData: adminOperations.adminData,
    booting,
    corpusQualityReport: adminOperations.corpusQualityReport,
    diagnosing: adminOperations.diagnosing,
    diagnostics: adminOperations.diagnostics,
    draft,
    error: error ?? ticketOperations.ticketError,
    escalating,
    graphBenchmark: adminOperations.graphBenchmark,
    graphInsightsMessage: adminOperations.graphInsightsMessage,
    graphParity: adminOperations.graphParity,
    ingested: adminOperations.ingested,
    ingesting: adminOperations.ingesting,
    knowledge,
    knowledgeMessage: adminOperations.knowledgeMessage,
    loadingAdmin: adminOperations.loadingAdmin,
    loadingTickets: ticketOperations.loadingTickets,
    locale,
    messages,
    newCategoryDescription: adminOperations.newCategoryDescription,
    newCategoryName: adminOperations.newCategoryName,
    newCategorySlug: adminOperations.newCategorySlug,
    quickPrompts,
    reviewQueues: adminOperations.reviewQueues,
    savingAdmin: adminOperations.savingAdmin,
    savingTicket: ticketOperations.savingTicket,
    sending,
    session,
    setDraft,
    setLocale,
    setNewCategoryDescription: adminOperations.setNewCategoryDescription,
    setNewCategoryName: adminOperations.setNewCategoryName,
    setNewCategorySlug: adminOperations.setNewCategorySlug,
    setTicketReplyDraft: ticketOperations.setTicketReplyDraft,
    setTicketStatusDraft: ticketOperations.setTicketStatusDraft,
    setWidgetOpen,
    ticket,
    ticketDetail: ticketOperations.ticketDetail,
    ticketReplyDraft: ticketOperations.ticketReplyDraft,
    ticketStatusDraft: ticketOperations.ticketStatusDraft,
    tickets: ticketOperations.tickets,
    ui,
    widgetMessages,
    widgetOpen,
    handleCreateCategory: adminOperations.handleCreateCategory,
    handleCreateContentArticle: adminOperations.handleCreateContentArticle,
    handleCreateAdminUser: adminOperations.handleCreateAdminUser,
    handleCreateDocumentType: adminOperations.handleCreateDocumentType,
    handleCreateAuthorityLevel: adminOperations.handleCreateAuthorityLevel,
    handleCreateDocument: adminOperations.handleCreateDocument,
    handleCreateLawyerProfile: adminOperations.handleCreateLawyerProfile,
    handleDeleteAdminUser: adminOperations.handleDeleteAdminUser,
    handleDeleteAuthorityLevel: adminOperations.handleDeleteAuthorityLevel,
    handleDeleteContentArticle: adminOperations.handleDeleteContentArticle,
    handleDeleteDocumentType: adminOperations.handleDeleteDocumentType,
    handleDeleteLawyerProfile: adminOperations.handleDeleteLawyerProfile,
    handleUpdateMetadataAISettings: adminOperations.handleUpdateMetadataAISettings,
    handleEscalate,
    handleDeleteDocument: adminOperations.handleDeleteDocument,
    handleReviewDocumentMetadata: adminOperations.handleReviewDocumentMetadata,
    handleIngest: adminOperations.handleIngest,
    handleLoadDocumentChunks: adminOperations.handleLoadDocumentChunks,
    handleLoadDocumentProvisions: adminOperations.handleLoadDocumentProvisions,
    handleLoadProvisionRelations: adminOperations.handleLoadProvisionRelations,
    handleRefreshDocumentStructure: adminOperations.handleRefreshDocumentStructure,
    handleReingestAllDocuments: adminOperations.handleReingestAllDocuments,
    handleSubmit,
    handleTicketReply: ticketOperations.handleTicketReply,
    handleTicketStatusUpdate: ticketOperations.handleTicketStatusUpdate,
    handleUploadDocumentFile: adminOperations.handleUploadDocumentFile,
    handleUploadAndIngestDocumentFile: adminOperations.handleUploadAndIngestDocumentFile,
    handleUpdateAdminUser: adminOperations.handleUpdateAdminUser,
    handleUpdateCategory: adminOperations.handleUpdateCategory,
    handleUpdateContentArticle: adminOperations.handleUpdateContentArticle,
    handleUpdateAuthorityLevel: adminOperations.handleUpdateAuthorityLevel,
    handleUpdateDocumentType: adminOperations.handleUpdateDocumentType,
    handleUpdateDocument: adminOperations.handleUpdateDocument,
    handleUpdateLawyerProfile: adminOperations.handleUpdateLawyerProfile,
    handleDeleteCategory: adminOperations.handleDeleteCategory,
    handleToggleCategory: adminOperations.handleToggleCategory,
    loadAdminOperations: adminOperations.loadAdminOperations,
    loadDiagnostics: adminOperations.loadDiagnostics,
    loadGraphInsights: adminOperations.loadGraphInsights,
    loadTicketDetail: ticketOperations.loadTicketDetail,
    loadTickets: ticketOperations.loadTickets,
    loadingGraphInsights: adminOperations.loadingGraphInsights,
  };
}

export function formatConfidence(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "--";
  }

  return `${Math.round(value * 100)}%`;
}

export function formatDateTime(value: string, locale: Locale): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(locale === "vi" ? "vi-VN" : "en-US");
}
