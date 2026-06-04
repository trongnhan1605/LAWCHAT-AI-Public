import { useNavigate } from "react-router-dom";

import ConsultantPanel from "../components/ConsultantPanel";
import UserAccountMenu from "../components/UserAccountMenu";
import { formatConfidence, useLawChatApp } from "../hooks/useLawChatApp";

export default function ConsultantPage() {
  const navigate = useNavigate();
  const app = useLawChatApp({ loadTickets: true });

  return (
    <main className="dashboard-page dashboard-page-modern app-shell">
      {app.error ? <div className="error-banner wide-banner">{app.error}</div> : null}
      <div className="panel-stack">
        <div className="workspace-header-actions chatgpt-chat-actions">
          <button className="chatgpt-logo-button consultant-logo-button" onClick={() => navigate("/")} type="button">
            <span className="chatgpt-logo-mark">LA</span>
            <span className="chatgpt-logo-copy">
              <strong>LawChat-AI</strong>
              <small>{app.ui.consultantTitle}</small>
            </span>
          </button>
          <UserAccountMenu locale={app.locale} />
        </div>
        <ConsultantPanel
          activeTicketId={app.activeTicketId}
          formatConfidence={formatConfidence}
          loadingTickets={app.loadingTickets}
          locale={app.locale}
          onLoadTicketDetail={(ticketId: number) => void app.loadTicketDetail(ticketId)}
          onLoadTickets={() => void app.loadTickets()}
          onTicketReply={() => void app.handleTicketReply()}
          onTicketReplyDraftChange={app.setTicketReplyDraft}
          onTicketStatusDraftChange={app.setTicketStatusDraft}
          onTicketStatusUpdate={() => void app.handleTicketStatusUpdate()}
          savingTicket={app.savingTicket}
          ticketDetail={app.ticketDetail}
          ticketReplyDraft={app.ticketReplyDraft}
          ticketStatusDraft={app.ticketStatusDraft}
          tickets={app.tickets}
          ui={app.ui}
        />
      </div>
    </main>
  );
}
