import api from "../http/axios";
import type { ApiEnvelope, Ticket, TicketDetail } from "../types/lawchat";

export const ticketsApi = {
  async listTickets(): Promise<Ticket[]> {
    const response = await api.get<ApiEnvelope<Ticket[]>>("/tickets");
    return response.data.data;
  },

  async getTicket(ticketId: number): Promise<TicketDetail> {
    const response = await api.get<ApiEnvelope<TicketDetail>>(`/tickets/${ticketId}`);
    return response.data.data;
  },

  async replyTicket(ticketId: number, content: string, senderName = "Consultant"): Promise<Ticket> {
    const response = await api.post<ApiEnvelope<Ticket>>(`/tickets/${ticketId}/reply`, { sender_name: senderName, content });
    return response.data.data;
  },

  async updateTicketStatus(ticketId: number, status: string): Promise<Ticket> {
    const response = await api.post<ApiEnvelope<Ticket>>(`/tickets/${ticketId}/status`, { status });
    return response.data.data;
  },
};
