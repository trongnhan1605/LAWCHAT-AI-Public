import api from "../http/axios";
import type { ApiEnvelope, AskMessagePayload, ChatSession, SessionDetail, Ticket } from "../types/lawchat";

export const chatApi = {
  async createSession(): Promise<ChatSession> {
    const response = await api.post<ApiEnvelope<ChatSession>>("/chat/sessions");
    return response.data.data;
  },

  async createCustomerSession(): Promise<ChatSession> {
    const response = await api.post<ApiEnvelope<ChatSession>>("/chat/customer/sessions");
    return response.data.data;
  },

  async getLatestCustomerSession(): Promise<SessionDetail> {
    const response = await api.get<ApiEnvelope<SessionDetail>>("/chat/customer/sessions/latest");
    return response.data.data;
  },

  async getSession(sessionToken: string): Promise<SessionDetail> {
    const response = await api.get<ApiEnvelope<SessionDetail>>(`/chat/sessions/${sessionToken}`);
    return response.data.data;
  },

  async ask(sessionToken: string, content: string): Promise<AskMessagePayload> {
    const response = await api.post<ApiEnvelope<AskMessagePayload>>(
      `/chat/sessions/${sessionToken}/messages`,
      { content },
      { timeout: 60000 },
    );
    return response.data.data;
  },

  async escalate(sessionToken: string, reason: string): Promise<Ticket> {
    const response = await api.post<ApiEnvelope<Ticket>>(`/chat/sessions/${sessionToken}/escalate`, { reason });
    return response.data.data;
  },
};
