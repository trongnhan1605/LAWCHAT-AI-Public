export type UserRole = "user" | "customer" | "consultant" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface AuthPayload {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
}

export function resolveUserHomePath(role: UserRole): string {
  if (role === "admin") {
    return "/dashboard";
  }
  if (role === "consultant") {
    return "/consultant";
  }
  return "/customer/workspace";
}
