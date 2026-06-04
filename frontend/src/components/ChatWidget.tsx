import { useEffect, useRef, type FormEvent } from "react";

import { translateTopic } from "../locales/metadata";
import type { Locale } from "../locales";
import type { ChatMessage } from "../types/lawchat";
import type { UiText } from "../locales";

interface ChatWidgetProps {
  booting: boolean;
  draft: string;
  error: string | null;
  sending: boolean;
  escalating: boolean;
  locale: Locale;
  messages: ChatMessage[];
  open: boolean;
  ui: UiText;
  onDraftChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEscalate: () => void;
  onOpenWorkspace: () => void;
  onToggleOpen: (value: boolean) => void;
}

export default function ChatWidget({
  booting,
  draft,
  error,
  sending,
  escalating,
  locale,
  messages,
  open,
  ui,
  onDraftChange,
  onSubmit,
  onEscalate,
  onOpenWorkspace,
  onToggleOpen,
}: ChatWidgetProps) {
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const previousLastMessageIdRef = useRef<number | null>(null);

  useEffect(() => {
    const element = messageListRef.current;
    const lastMessage = messages[messages.length - 1] ?? null;
    const lastMessageId = lastMessage?.id ?? null;
    const isNewLastMessage = lastMessageId !== previousLastMessageIdRef.current;

    if (!element || !open) {
      previousLastMessageIdRef.current = lastMessageId;
      return;
    }

    if (lastMessageId !== null && (isNewLastMessage || element.scrollTop === 0)) {
      const behavior = previousLastMessageIdRef.current === null ? "auto" : "smooth";
      requestAnimationFrame(() => {
        element.scrollTo({ top: element.scrollHeight, behavior });
      });
    }

    previousLastMessageIdRef.current = lastMessageId;
  }, [messages, open]);

  return (
    <div className={`chat-widget-dock ${open ? "open" : "collapsed"}`}>
      <button className="widget-side-tab" onClick={() => onToggleOpen(!open)} type="button">
        {ui.widgetSupportTabLabel}
      </button>

      <div className={`chat-widget ${open ? "open" : "collapsed"}`}>
        {open ? (
          <>
            <div className="chat-widget-topbar">
              <div className="widget-brand-row">
                <div className="widget-brand-mark">LA</div>
                <div>
                  <strong>LawChat-AI</strong>
                  <span>{ui.widgetTitle}</span>
                </div>
              </div>
              <button
                aria-label={ui.widgetCloseLabel}
                className="widget-menu-button icon-button"
                onClick={() => onToggleOpen(false)}
                title={ui.widgetCloseLabel}
                type="button"
              >
                <CloseIcon />
              </button>
            </div>

            <div className="widget-status-strip">
              <span className="widget-status-dot" />
              <span>{ui.widgetReadyStatus}</span>
            </div>

            <div className="widget-messages" ref={messageListRef}>
              {booting ? <div className="empty-state compact-empty">{ui.bootingMessage}</div> : null}
              {!booting && !messages.length ? (
                <div className="widget-welcome">
                  <strong>{ui.widgetWelcomeTitle}</strong>
                  <p>{ui.widgetWelcomeDescription}</p>
                </div>
              ) : null}
              {messages.map((message) => (
                <article className={`message-bubble ${message.role === "assistant" ? "assistant" : "user"}`} key={message.id}>
                  <div className="message-meta compact-message-meta">
                    <span>{message.role === "assistant" ? ui.messageAuthorBot : ui.messageAuthorYou}</span>
                    {message.category_slug ? <span>{translateTopic(locale, message.category_slug)}</span> : null}
                  </div>
                  <div className="message-body">{message.content}</div>
                  {message.warning_text ? <p className="warning-text">{message.warning_text}</p> : null}
                </article>
              ))}
            </div>

            {error ? <div className="error-banner widget-error-banner">{error}</div> : null}

            <form className="widget-composer" onSubmit={onSubmit}>
              <textarea
                aria-label={ui.widgetInputAriaLabel}
                onChange={(event) => onDraftChange(event.target.value)}
                placeholder={ui.widgetPlaceholder}
                rows={2}
                value={draft}
              />
              <div className="widget-toolbar">
                <button
                  aria-label={ui.widgetEscalateAriaLabel}
                  className="quick-toolbar-button icon-button"
                  disabled={escalating}
                  onClick={onEscalate}
                  title={ui.widgetConsultTitle}
                  type="button"
                >
                  <HeadsetIcon />
                </button>
                <button
                  aria-label={ui.widgetOpenWorkspaceAriaLabel}
                  className="quick-toolbar-button icon-button"
                  onClick={onOpenWorkspace}
                  title={ui.widgetExpandTitle}
                  type="button"
                >
                  <ExpandIcon />
                </button>
                <button
                  aria-label={sending ? ui.sendLoading : ui.sendButton}
                  className="widget-send-action icon-button"
                  disabled={sending || !draft.trim()}
                  title={sending ? ui.sendLoading : ui.sendButton}
                  type="submit"
                >
                  <SendIcon />
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="widget-launcher-wrap">
            <button className="widget-circle-launcher" onClick={() => onToggleOpen(true)} type="button">
              {ui.widgetLauncherLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M7 7L17 17M17 7L7 17" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

function HeadsetIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4 12a8 8 0 1116 0v5a2 2 0 01-2 2h-1v-6h1a6 6 0 10-12 0h1v6H6a2 2 0 01-2-2v-5z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M9 18h6" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

function ExpandIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M9 4H4v5M15 4h5v5M20 15v5h-5M4 15v5h5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4 11.5L20 4l-4.5 16-3.5-6-8-2.5z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M11.8 14L20 4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}
