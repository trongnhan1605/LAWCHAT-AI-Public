import { translatePriority, translateTicketStatus, translateTopic } from "../locales/metadata";
import type { Locale, UiText } from "../locales";
import type { Ticket, TicketDetail } from "../types/lawchat";

interface ConsultantPanelProps {
  activeTicketId: number | null;
  loadingTickets: boolean;
  locale: Locale;
  savingTicket: boolean;
  ticketDetail: TicketDetail | null;
  ticketReplyDraft: string;
  ticketStatusDraft: string;
  tickets: Ticket[];
  ui: UiText;
  onLoadTickets: () => void;
  onLoadTicketDetail: (ticketId: number) => void;
  onTicketReplyDraftChange: (value: string) => void;
  onTicketStatusDraftChange: (value: string) => void;
  onTicketReply: () => void;
  onTicketStatusUpdate: () => void;
  formatConfidence: (value: number | null | undefined) => string;
}

export default function ConsultantPanel({
  activeTicketId,
  loadingTickets,
  locale,
  savingTicket,
  ticketDetail,
  ticketReplyDraft,
  ticketStatusDraft,
  tickets,
  ui,
  onLoadTickets,
  onLoadTicketDetail,
  onTicketReplyDraftChange,
  onTicketStatusDraftChange,
  onTicketReply,
  onTicketStatusUpdate,
  formatConfidence,
}: ConsultantPanelProps) {
  return (
    <div className="panel-card consultant-card">
      <div className="panel-heading-row">
        <div>
          <p className="section-label">{ui.consultantLabel}</p>
          <h2>{ui.consultantTitle}</h2>
        </div>
        <button className="secondary-button" onClick={onLoadTickets} type="button">
          {ui.refreshButton}
        </button>
      </div>

      <div className="consultant-grid">
        <div className="ticket-list">
          {loadingTickets ? <div className="empty-state compact-empty">{ui.loadingTickets}</div> : null}
          {!loadingTickets && !tickets.length ? <div className="empty-state compact-empty">{ui.noTickets}</div> : null}
          {tickets.map((item) => (
            <button className={`ticket-item ${item.id === activeTicketId ? "active" : ""}`} key={item.id} onClick={() => onLoadTicketDetail(item.id)} type="button">
              <strong>#{item.id} {item.title}</strong>
              <span>{translateTicketStatus(locale, item.status)}</span>
              <small>{translateTopic(locale, item.topic)}</small>
            </button>
          ))}
        </div>

        <div className="ticket-detail-panel">
          {!ticketDetail ? <div className="empty-state compact-empty">{ui.selectTicket}</div> : null}
          {ticketDetail ? (
            <>
              <div className="ticket-summary">
                <strong>#{ticketDetail.ticket.id} {ticketDetail.ticket.title}</strong>
                <p>{ticketDetail.ticket.escalation_reason}</p>
                <div className="diagnostic-grid">
                  <span>{ui.statusText}: {translateTicketStatus(locale, ticketDetail.ticket.status)}</span>
                  <span>{ui.priorityText}: {translatePriority(locale, ticketDetail.ticket.priority)}</span>
                  <span>{ui.confidenceLabel}: {formatConfidence(ticketDetail.ticket.confidence_score)}</span>
                </div>
              </div>

              {ticketDetail.legal_case ? (
                <div className="ticket-summary">
                  <strong>{locale === "vi" ? "Ho so phap ly" : "Legal case"}</strong>
                  <p>{ticketDetail.legal_case.title}</p>
                  <div className="diagnostic-grid">
                    <span>{locale === "vi" ? "Linh vuc" : "Domain"}: {ticketDetail.legal_case.legal_domain}</span>
                    <span>{locale === "vi" ? "Trang thai" : "Status"}: {ticketDetail.legal_case.status}</span>
                    <span>{locale === "vi" ? "Rui ro" : "Risk"}: {ticketDetail.legal_case.risk_level}</span>
                  </div>
                  {ticketDetail.legal_case.desired_outcome ? <p>{ticketDetail.legal_case.desired_outcome}</p> : null}
                </div>
              ) : null}

              {ticketDetail.case_facts.length ? (
                <div className="ticket-summary">
                  <strong>{locale === "vi" ? "Tinh tiet da trich" : "Extracted case facts"}</strong>
                  <div className="ticket-timeline">
                    {ticketDetail.case_facts.map((fact) => (
                      <article className="timeline-item" key={`fact-${fact.id}`}>
                        <span className="timeline-label">{fact.fact_type} | {fact.fact_key}</span>
                        <p>{fact.fact_value}</p>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              {ticketDetail.validation_runs.length ? (
                <div className="ticket-summary">
                  <strong>{locale === "vi" ? "Validation gan day" : "Recent validation runs"}</strong>
                  <div className="ticket-timeline">
                    {ticketDetail.validation_runs.map((run) => (
                      <article className="timeline-item" key={`validation-${run.id}`}>
                        <span className="timeline-label">{run.validation_status}</span>
                        <p>
                          {locale === "vi"
                            ? `Confidence ${formatConfidence(run.confidence_score)} | Escalation ${run.escalation_recommended ? "co" : "khong"}`
                            : `Confidence ${formatConfidence(run.confidence_score)} | Escalation ${run.escalation_recommended ? "yes" : "no"}`}
                        </p>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="ticket-timeline">
                {ticketDetail.session_messages.map((message) => (
                  <article className="timeline-item" key={`session-${message.id}`}>
                    <span className="timeline-label">
                      {ui.consultantSessionLabel} {message.role === "assistant" ? ui.messageAuthorBot : ui.messageAuthorUser}
                    </span>
                    <p>{message.content}</p>
                  </article>
                ))}
                {ticketDetail.consultant_messages.map((message) => (
                  <article className="timeline-item consultant" key={`consultant-${message.id}`}>
                    <span className="timeline-label">{message.sender_name}</span>
                    <p>{message.content}</p>
                  </article>
                ))}
              </div>

              <div className="ticket-actions-row">
                <select className="ticket-select" onChange={(event) => onTicketStatusDraftChange(event.target.value)} value={ticketStatusDraft}>
                  <option value="new">{translateTicketStatus(locale, "new")}</option>
                  <option value="assigned">{translateTicketStatus(locale, "assigned")}</option>
                  <option value="in_progress">{translateTicketStatus(locale, "in_progress")}</option>
                  <option value="waiting_user">{translateTicketStatus(locale, "waiting_user")}</option>
                  <option value="answered">{translateTicketStatus(locale, "answered")}</option>
                  <option value="closed">{translateTicketStatus(locale, "closed")}</option>
                  <option value="cancelled">{translateTicketStatus(locale, "cancelled")}</option>
                </select>
                <button className="secondary-button" disabled={savingTicket} onClick={onTicketStatusUpdate} type="button">
                  {ui.updateStatusButton}
                </button>
              </div>

              <div className="composer ticket-composer">
                <label className="composer-label" htmlFor="ticket-reply">{ui.consultantReplyLabel}</label>
                <textarea id="ticket-reply" onChange={(event) => onTicketReplyDraftChange(event.target.value)} rows={4} value={ticketReplyDraft} />
                <div className="composer-actions">
                  <span className="helper-text">{ui.consultantReplyHelp}</span>
                  <button className="primary-button" disabled={savingTicket || !ticketReplyDraft.trim()} onClick={onTicketReply} type="button">
                    {savingTicket ? ui.saveReplyLoading : ui.saveReplyButton}
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
