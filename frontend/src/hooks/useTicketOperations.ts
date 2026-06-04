import axios from "axios";
import { useState } from "react";

import { lawChatApi } from "../api/lawchat.api";
import type { UiText } from "../locales";
import type { Ticket, TicketDetail } from "../types/lawchat";

const ACCESS_TOKEN_KEY = "lawchat.access_token";

function hasStoredAccessToken(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return Boolean(window.localStorage.getItem(ACCESS_TOKEN_KEY));
}

type UseTicketOperationsParams = {
  handleUnauthorized: () => void;
  ui: UiText;
};

export function useTicketOperations({ handleUnauthorized, ui }: UseTicketOperationsParams) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null);
  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null);
  const [ticketReplyDraft, setTicketReplyDraft] = useState("");
  const [ticketStatusDraft, setTicketStatusDraft] = useState("in_progress");
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [savingTicket, setSavingTicket] = useState(false);
  const [ticketError, setTicketError] = useState<string | null>(null);

  async function loadTickets(preferredTicketId?: number) {
    if (!hasStoredAccessToken()) {
      setTickets([]);
      setActiveTicketId(null);
      setTicketDetail(null);
      return;
    }

    setLoadingTickets(true);
    try {
      const items = await lawChatApi.listTickets();
      setTickets(items);
      const nextTicketId = preferredTicketId ?? items[0]?.id ?? null;
      setActiveTicketId(nextTicketId);
      if (nextTicketId) {
        const detail = await lawChatApi.getTicket(nextTicketId);
        setTicketDetail(detail);
        setTicketStatusDraft(detail.ticket.status);
      } else {
        setTicketDetail(null);
      }
    } catch (caught) {
      if (axios.isAxiosError(caught) && caught.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      throw caught;
    } finally {
      setLoadingTickets(false);
    }
  }

  async function loadTicketDetail(ticketId: number) {
    setActiveTicketId(ticketId);
    try {
      const detail = await lawChatApi.getTicket(ticketId);
      setTicketDetail(detail);
      setTicketStatusDraft(detail.ticket.status);
    } catch (caught) {
      if (axios.isAxiosError(caught) && caught.response?.status === 401) {
        handleUnauthorized();
        return;
      }
      throw caught;
    }
  }

  async function handleTicketReply() {
    if (!activeTicketId || !ticketReplyDraft.trim() || savingTicket) {
      return;
    }

    setSavingTicket(true);
    try {
      await lawChatApi.replyTicket(activeTicketId, ticketReplyDraft.trim());
      setTicketReplyDraft("");
      await loadTickets(activeTicketId);
    } catch {
      setTicketError(ui.appTicketReplyError);
    } finally {
      setSavingTicket(false);
    }
  }

  async function handleTicketStatusUpdate() {
    if (!activeTicketId || savingTicket) {
      return;
    }

    setSavingTicket(true);
    try {
      await lawChatApi.updateTicketStatus(activeTicketId, ticketStatusDraft);
      await loadTickets(activeTicketId);
    } catch {
      setTicketError(ui.appTicketStatusError);
    } finally {
      setSavingTicket(false);
    }
  }

  return {
    activeTicketId,
    loadingTickets,
    savingTicket,
    setActiveTicketId,
    setTicketReplyDraft,
    setTicketStatusDraft,
    ticketDetail,
    ticketError,
    ticketReplyDraft,
    ticketStatusDraft,
    tickets,
    loadTicketDetail,
    loadTickets,
    handleTicketReply,
    handleTicketStatusUpdate,
  };
}
