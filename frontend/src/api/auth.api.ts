import api from "../http/axios";
import type { ApiEnvelope, AuthPayload, LoginPayload, RegisterPayload, User } from "../types/auth";

export const authApi = {
  async register(payload: RegisterPayload): Promise<AuthPayload> {
    const response = await api.post<ApiEnvelope<AuthPayload>>("/auth/register", payload);
    return response.data.data;
  },

  async login(payload: LoginPayload): Promise<AuthPayload> {
    const response = await api.post<ApiEnvelope<AuthPayload>>("/auth/login", payload);
    return response.data.data;
  },

  async me(): Promise<User> {
    const response = await api.get<ApiEnvelope<User>>("/auth/me");
    return response.data.data;
  },
};
