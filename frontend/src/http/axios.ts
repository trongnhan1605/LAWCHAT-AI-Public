import axios from "axios";

const ACCESS_TOKEN_KEY = "lawchat.access_token";
const USER_KEY = "lawchat.user";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL?.trim() || "http://localhost:8000/api",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(USER_KEY);
    }
    return Promise.reject(error);
  },
);

export default api;
