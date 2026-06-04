import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Locale } from "../locales";
import { useAuthStore } from "../store/auth.store";
import type { UserRole } from "../types/auth";

interface UserAccountMenuProps {
  locale: Locale;
}

type MenuItem = {
  key: string;
  label: string;
  path?: string;
  onSelect?: () => void;
};

export default function UserAccountMenu({ locale }: UserAccountMenuProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  const labels = useMemo(() => (
    locale === "vi"
      ? {
          home: "Trang chủ",
          workspace: "Không gian làm việc",
          consultant: "Không gian tư vấn",
          dashboard: "Bảng điều khiển",
          login: "Đăng nhập",
          register: "Đăng ký",
          logout: "Đăng xuất",
          guestName: "Khách",
          guestEmail: "Chưa đăng nhập",
        }
      : {
          home: "Home",
          workspace: "Workspace",
          consultant: "Consultant",
          dashboard: "Dashboard",
          login: "Login",
          register: "Register",
          logout: "Log out",
          guestName: "Guest",
          guestEmail: "Not signed in",
        }
  ), [locale]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  const items = buildMenuItems({
    isAuthenticated,
    labels,
    onLogout: () => {
      logout();
      navigate("/");
    },
    role: user?.role,
  });

  const initials = buildInitials(user?.full_name ?? user?.email ?? labels.guestName);

  return (
    <div className="account-menu" ref={containerRef}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        className="account-menu-trigger"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span className="account-menu-avatar">{initials}</span>
      </button>

      {open ? (
        <div className="account-menu-popover" role="menu">
          <div className="account-menu-profile">
            <strong>{user?.full_name ?? labels.guestName}</strong>
            <span>{user?.email ?? labels.guestEmail}</span>
          </div>

          <div className="account-menu-list">
            {items.map((item) => (
              <button
                className="account-menu-item"
                key={item.key}
                onClick={() => {
                  setOpen(false);
                  if (item.path) {
                    navigate(item.path);
                    return;
                  }
                  item.onSelect?.();
                }}
                role="menuitem"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function buildMenuItems({
  isAuthenticated,
  labels,
  onLogout,
  role,
}: {
  isAuthenticated: boolean;
  labels: Record<string, string>;
  onLogout: () => void;
  role?: UserRole;
}): MenuItem[] {
  if (!isAuthenticated || !role) {
    return [
      { key: "home", label: labels.home, path: "/" },
      { key: "workspace", label: labels.workspace, path: "/workspace" },
      { key: "login", label: labels.login, path: "/login" },
      { key: "register", label: labels.register, path: "/register" },
    ];
  }

  const items: MenuItem[] = [
    { key: "home", label: labels.home, path: "/" },
    { key: "workspace", label: labels.workspace, path: "/customer/workspace" },
  ];

  if (role === "consultant" || role === "admin") {
    items.push({ key: "consultant", label: labels.consultant, path: "/consultant" });
  }

  if (role === "admin") {
    items.push({ key: "dashboard", label: labels.dashboard, path: "/dashboard" });
  }

  items.push({ key: "logout", label: labels.logout, onSelect: onLogout });
  return items;
}

function buildInitials(value: string) {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return "U";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 1).toUpperCase();
  }

  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}
