import { create } from "zustand";

import { authApi } from "../api/auth.api";
import { UI_TEXT, resolveStoredLocale } from "../locales";
import type { LoginPayload, RegisterPayload, User } from "../types/auth";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  isLoading: boolean;
  error: string | null;
  hydrate: () => Promise<void>;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const ACCESS_TOKEN_KEY = "lawchat.access_token";
const USER_KEY = "lawchat.user";

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isHydrated: false,
  isLoading: false,
  error: null,

  hydrate: async () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    const rawUser = localStorage.getItem(USER_KEY);

    if (!token || !rawUser) {
      set({ isHydrated: true });
      return;
    }

    try {
      const user = JSON.parse(rawUser) as User;
      set({ token, user, isAuthenticated: true, isHydrated: true, error: null });
    } catch {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({ user: null, token: null, isAuthenticated: false, isHydrated: true });
    }
  },

  login: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const auth = await authApi.login(payload);
      localStorage.setItem(ACCESS_TOKEN_KEY, auth.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
      set({
        user: auth.user,
        token: auth.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : UI_TEXT[resolveStoredLocale()].authLoginFailed;
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  register: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const auth = await authApi.register(payload);
      localStorage.setItem(ACCESS_TOKEN_KEY, auth.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
      set({
        user: auth.user,
        token: auth.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : UI_TEXT[resolveStoredLocale()].authRegisterFailed;
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    set({ user: null, token: null, isAuthenticated: false, error: null });
  },

  clearError: () => set({ error: null }),
}));
