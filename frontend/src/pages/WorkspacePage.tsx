import { useState } from "react";
import { useNavigate } from "react-router-dom";

import WorkspaceChatPanel from "../components/WorkspaceChatPanel";
import { useLawChatApp } from "../hooks/useLawChatApp";

interface WorkspacePageProps {
  sessionMode?: "public" | "customer";
}

export default function WorkspacePage({ sessionMode = "public" }: WorkspacePageProps) {
  const navigate = useNavigate();
  const app = useLawChatApp({ sessionMode });
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [focusedMessageId, setFocusedMessageId] = useState<number | null>(null);

  const firstUserMessage = app.messages.find((message) => message.role === "user") ?? null;
  const lastMessage = app.messages[app.messages.length - 1] ?? null;
  const currentConversation = firstUserMessage
    ? {
        id: firstUserMessage.id,
        title: buildConversationTitle(firstUserMessage.content, app.ui.workspaceCurrentConversationTitle),
        preview: buildConversationPreview(lastMessage?.content ?? firstUserMessage.content, app.ui.workspaceReadyForQuestionPreview),
      }
    : null;
  const conversationLabel = app.ui.workspaceConversationLabel;
  const emptyConversationLabel = app.ui.workspaceNoConversationLabel;

  function closeSidebar() {
    setIsSidebarOpen(false);
  }

  function focusConversation(messageId: number) {
    setFocusedMessageId(messageId);
    closeSidebar();
  }

  return (
    <main className="workspace-page chatgpt-workspace-shell">
      <div
        aria-hidden={!isSidebarOpen}
        className={`chatgpt-sidebar-backdrop ${isSidebarOpen ? "open" : ""}`}
        onClick={closeSidebar}
      />

      <aside className={`chatgpt-sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="chatgpt-sidebar-top">
          <div className="chatgpt-sidebar-brand-row">
            <button className="chatgpt-logo-button" onClick={() => navigate("/")} type="button">
              <span className="chatgpt-logo-mark">LA</span>
              <span className="chatgpt-logo-copy">
                <strong>LawChat-AI</strong>
                <small>{conversationLabel}</small>
              </span>
            </button>
            <button
              aria-label={app.ui.workspaceCloseSidebarLabel}
              className="chatgpt-sidebar-close"
              onClick={closeSidebar}
              type="button"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        <div className="chatgpt-sidebar-scroll">
          <section className="chatgpt-sidebar-section chatgpt-conversation-section">
            <p className="section-label">{conversationLabel}</p>
            <div className="chatgpt-conversation-list">
              {!currentConversation ? <div className="chatgpt-sidebar-empty">{emptyConversationLabel}</div> : null}
              {currentConversation ? (
                <button
                  className={`chatgpt-conversation-item ${focusedMessageId === null || focusedMessageId === currentConversation.id ? "active" : ""}`}
                  onClick={() => focusConversation(currentConversation.id)}
                  type="button"
                >
                  <strong>{currentConversation.title}</strong>
                  <span>{currentConversation.preview}</span>
                </button>
              ) : null}
            </div>
          </section>
        </div>
      </aside>

      <section className="chatgpt-chat-stage">
        <div className="chatgpt-mobile-bar">
          <button
            aria-label={app.ui.workspaceOpenSidebarLabel}
            className="chatgpt-mobile-menu"
            onClick={() => setIsSidebarOpen(true)}
            type="button"
          >
            <MenuIcon />
          </button>

          <button className="chatgpt-logo-button" onClick={() => navigate("/")} type="button">
            <span className="chatgpt-logo-copy">
              <strong>LawChat-AI</strong>
              <small>{app.ui.workspaceEyebrow}</small>
            </span>
          </button>
        </div>

        <div className="chatgpt-chat-frame">
          <WorkspaceChatPanel
            booting={app.booting}
            draft={app.draft}
            error={app.error}
            locale={app.locale}
            messages={app.messages}
            onDraftChange={app.setDraft}
            onLocaleChange={app.setLocale}
            focusedMessageId={focusedMessageId}
            onSubmit={app.handleSubmit}
            sending={app.sending}
            session={app.session}
            ui={app.ui}
          />
        </div>
      </section>
    </main>
  );
}

function buildConversationTitle(content: string, fallbackTitle: string) {
  const normalized = content.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return fallbackTitle;
  }

  return normalized.length > 38 ? `${normalized.slice(0, 38).trim()}...` : normalized;
}

function buildConversationPreview(content: string, fallbackPreview: string) {
  const normalized = content.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return fallbackPreview;
  }

  if (normalized.length <= 72) {
    return normalized;
  }

  return `${normalized.slice(0, 72).trim()}...`;
}

function MenuIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M7 7L17 17M17 7L7 17" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}
