import axios from "axios";

const ACCESS_TOKEN_KEY = "lawchat.access_token";

export function hasStoredAccessToken(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return Boolean(window.localStorage.getItem(ACCESS_TOKEN_KEY));
}

export function isDocumentDuplicateError(caught: unknown): boolean {
  return axios.isAxiosError(caught)
    && caught.response?.status === 409
    && caught.response?.data?.data?.conflict_type === "document_duplicate";
}
