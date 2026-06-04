import { useEffect, useRef, type FormEvent } from "react";

import { translateTopic } from "../locales/metadata";
import type { Locale, UiText } from "../locales";
import type { ChatMessage, ChatSession } from "../types/lawchat";
import UserAccountMenu from "./UserAccountMenu";

interface WorkspaceChatPanelProps {
  booting: boolean;
  draft: string;
  error: string | null;
  sending: boolean;
  session: ChatSession | null;
  messages: ChatMessage[];
  locale: Locale;
  ui: UiText;
  focusedMessageId: number | null;
  onDraftChange: (value: string) => void;
  onLocaleChange: (locale: Locale) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export default function WorkspaceChatPanel({
  booting,
  draft,
  error,
  sending,
  session,
  messages,
  locale,
  ui,
  focusedMessageId,
  onDraftChange,
  onLocaleChange,
  onSubmit,
}: WorkspaceChatPanelProps) {
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const messageRefs = useRef(new Map<number, HTMLDivElement>());
  const shouldStickToBottomRef = useRef(true);
  const previousLastMessageIdRef = useRef<number | null>(null);

  function handleMessageListScroll() {
    const element = messageListRef.current;
    if (!element) {
      return;
    }

    const distanceToBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    shouldStickToBottomRef.current = distanceToBottom < 140;
  }

  useEffect(() => {
    const element = messageListRef.current;
    const lastMessage = messages[messages.length - 1] ?? null;
    const lastMessageId = lastMessage?.id ?? null;
    const isNewLastMessage = lastMessageId !== previousLastMessageIdRef.current;

    if (!element) {
      previousLastMessageIdRef.current = lastMessageId;
      return;
    }

    if (isNewLastMessage && shouldStickToBottomRef.current) {
      const behavior = previousLastMessageIdRef.current === null ? "auto" : "smooth";
      requestAnimationFrame(() => {
        element.scrollTo({ top: element.scrollHeight, behavior });
      });
    }

    previousLastMessageIdRef.current = lastMessageId;
  }, [messages]);

  useEffect(() => {
    if (focusedMessageId === null) {
      return;
    }

    const target = messageRefs.current.get(focusedMessageId);
    if (!target) {
      return;
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusedMessageId]);

  return (
    <section className="chat-panel chatgpt-chat-panel">
      <div className="chat-header chatgpt-chat-header">
        <div>
          <p className="section-label">{ui.publicChatLabel}</p>
          <h2>{ui.chatbotTitle}</h2>
        </div>

        <div className="workspace-header-actions chatgpt-chat-actions">
          <div className="lang-toggle workspace-header-lang-toggle">
            <button className={locale === "vi" ? "active" : ""} onClick={() => onLocaleChange("vi")} type="button">VI</button>
            <button className={locale === "en" ? "active" : ""} onClick={() => onLocaleChange("en")} type="button">EN</button>
          </div>
          <UserAccountMenu locale={locale} />
        </div>
      </div>

      <div className="chat-card workspace-chat-card chatgpt-message-stage">
        {booting ? <div className="empty-state">{ui.bootingMessage}</div> : null}
        {!booting && !messages.length ? (
          <div className="empty-state chatgpt-empty-state">
            <strong>{ui.emptyChatTitle}</strong>
            <p>{ui.emptyChatDescription}</p>
          </div>
        ) : null}

        <div className="message-list workspace-message-list chatgpt-message-list" onScroll={handleMessageListScroll} ref={messageListRef}>
          {messages.map((message) => (
            <div
              className={`chatgpt-message-row ${message.role === "assistant" ? "assistant" : "user"}`}
              key={message.id}
              ref={(element) => {
                if (element) {
                  messageRefs.current.set(message.id, element);
                  return;
                }

                messageRefs.current.delete(message.id);
              }}
            >
              <article className={`message-bubble ${message.role === "assistant" ? "assistant" : "user"}`}>
                <div className="message-meta">
                  <span>{message.role === "assistant" ? ui.messageAuthorBot : ui.messageAuthorUser}</span>
                  {message.category_slug ? <span>{translateTopic(locale, message.category_slug)}</span> : null}
                </div>
                <div className="message-body">{message.content}</div>
                {message.warning_text ? <p className="warning-text">{message.warning_text}</p> : null}
                {message.citation ? (
                  <div className="citation-box">
                    <strong>{message.citation.title}</strong>
                    {message.citation.source_reference ? <span>{message.citation.source_reference}</span> : null}
                  </div>
                ) : null}
              </article>
            </div>
          ))}
        </div>

        {error ? <div className="error-banner workspace-error-banner">{error}</div> : null}

        <form className="composer chatgpt-composer" onSubmit={onSubmit}>
          <div className="chatgpt-composer-input-wrap">
            <textarea
              aria-label={ui.workspaceInputAriaLabel}
              id="chat-input"
              onChange={(event) => onDraftChange(event.target.value)}
              placeholder={ui.askPlaceholder}
              rows={3}
              value={draft}
            />
            <button
              aria-label={sending ? ui.sendLoading : ui.sendButton}
              className="workspace-send-button"
              disabled={!session || sending || !draft.trim()}
              type="submit"
            >
              <SendIcon />
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function SendIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M21 3L10 14" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
      <path d="M21 3L14 21L10 14L3 10L21 3Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  );
}
