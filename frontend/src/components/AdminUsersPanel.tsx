import { useEffect, useMemo, useState } from "react";

import type { Locale, UiText } from "../locales";
import type { AdminUserItem, AdminUserWritePayload } from "../types/lawchat";
import { translateAdminTabLabel } from "../locales/metadata";

const ROLE_OPTIONS: Array<AdminUserWritePayload["role"]> = ["user", "customer", "consultant", "admin"];

const ROLE_LABELS = {
  vi: {
    user: "User",
    customer: "Khách hàng",
    consultant: "Tư vấn viên",
    admin: "Quản trị viên",
  },
  en: {
    user: "User",
    customer: "Customer",
    consultant: "Consultant",
    admin: "Admin",
  },
} as const;

type UserModalState =
  | { mode: "create"; user: null }
  | { mode: "edit"; user: AdminUserItem }
  | null;

interface AdminUsersPanelProps {
  users: AdminUserItem[];
  locale: Locale;
  savingAdmin: boolean;
  ui: UiText;
  formatDateTime: (value: string) => string;
  onCreateAdminUser: (payload: AdminUserWritePayload) => Promise<void> | void;
  onUpdateAdminUser: (userId: number, payload: AdminUserWritePayload) => Promise<void> | void;
  onDeleteAdminUser: (userId: number) => Promise<void> | void;
}

function translateRole(locale: Locale, role: AdminUserItem["role"]): string {
  return ROLE_LABELS[locale][role] ?? role;
}

function getRoleChipClass(role: AdminUserItem["role"]): string {
  switch (role) {
    case "admin":
      return "user-role-chip admin-role-chip";
    case "consultant":
      return "user-role-chip consultant-role-chip";
    case "customer":
      return "user-role-chip customer-role-chip";
    default:
      return "user-role-chip user-basic-chip";
  }
}

export default function AdminUsersPanel({
  users,
  locale,
  savingAdmin,
  ui,
  formatDateTime,
  onCreateAdminUser,
  onUpdateAdminUser,
  onDeleteAdminUser,
}: AdminUsersPanelProps) {
  const actionsColumnLabel = locale === "vi" ? "Thao tac" : "Actions";
  const [search, setSearch] = useState("");
  const [modalState, setModalState] = useState<UserModalState>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AdminUserWritePayload["role"]>("customer");
  const [password, setPassword] = useState("");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!modalState) {
      setFullName("");
      setEmail("");
      setRole("customer");
      setPassword("");
      setIsActive(true);
      return;
    }

    if (modalState.mode === "edit") {
      setFullName(modalState.user.full_name);
      setEmail(modalState.user.email);
      setRole(modalState.user.role);
      setPassword("");
      setIsActive(modalState.user.is_active);
      return;
    }

    setFullName("");
    setEmail("");
    setRole("customer");
    setPassword("");
    setIsActive(true);
  }, [modalState]);

  const filteredUsers = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    if (!normalizedSearch) {
      return users;
    }

    return users.filter((user) => [user.full_name, user.email, user.role].some((value) => value.toLowerCase().includes(normalizedSearch)));
  }, [search, users]);

  const totalActiveUsers = users.filter((user) => user.is_active).length;
  const totalAdmins = users.filter((user) => user.role === "admin").length;
  const totalConsultants = users.filter((user) => user.role === "consultant").length;

  async function handleSubmit() {
    if (!fullName.trim() || !email.trim()) {
      return;
    }
    if (modalState?.mode === "create" && password.trim().length < 8) {
      return;
    }

    const payload: AdminUserWritePayload = {
      full_name: fullName.trim(),
      email: email.trim(),
      role,
      is_active: isActive,
      password: password.trim() || undefined,
    };

    try {
      if (modalState?.mode === "edit" && modalState.user) {
        await onUpdateAdminUser(modalState.user.id, payload);
      } else {
        await onCreateAdminUser(payload);
      }
      setModalState(null);
    } catch {
      // Global app error banner already shows the backend message.
    }
  }

  async function handleDelete(userId: number) {
    if (!window.confirm(ui.deleteUserConfirm)) {
      return;
    }

    try {
      await onDeleteAdminUser(userId);
    } catch {
      // Global app error banner already shows the backend message.
    }
  }

  return (
    <div className="admin-table-section admin-users-panel">
      <div className="admin-stat-grid admin-stat-grid-modern">
        <article className="admin-stat-card admin-stat-card-modern">
          <span>{translateAdminTabLabel(locale, "users")}</span>
          <strong>{users.length}</strong>
        </article>
        <article className="admin-stat-card admin-stat-card-modern">
          <span>{ui.activeUserLabel}</span>
          <strong>{totalActiveUsers}</strong>
        </article>
        <article className="admin-stat-card admin-stat-card-modern">
          <span>{translateRole(locale, "admin")}</span>
          <strong>{totalAdmins}</strong>
        </article>
        <article className="admin-stat-card admin-stat-card-modern">
          <span>{translateRole(locale, "consultant")}</span>
          <strong>{totalConsultants}</strong>
        </article>
      </div>

      <div className="admin-table-toolbar">
        <div className="admin-table-filters">
          <input className="admin-filter-input" onChange={(event) => setSearch(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={search} />
        </div>
        <div className="admin-table-toolbar-actions">
          <button className="ghost-button admin-filter-clear-button" onClick={() => setSearch("")} type="button">{ui.adminClearFiltersButton}</button>
          <button className="primary-button" onClick={() => setModalState({ mode: "create", user: null })} type="button">
            <AddIcon />
            <span>{ui.createUserButton}</span>
          </button>
        </div>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table admin-table-compact">
          <thead>
            <tr>
              <th>{ui.authFullNameLabel}</th>
              <th>{ui.authEmailLabel}</th>
              <th>{ui.userRoleLabel}</th>
              <th>{ui.statusLabel}</th>
              <th>{ui.userCreatedAtLabel}</th>
              <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div>
                </td>
              </tr>
            ) : filteredUsers.map((user) => (
              <tr key={user.id}>
                <td className="admin-table-title-cell">{user.full_name}</td>
                <td>{user.email}</td>
                <td>
                  <span className={`document-chip ${getRoleChipClass(user.role)}`}>{translateRole(locale, user.role)}</span>
                </td>
                <td>
                  <span className={`document-chip ${user.is_active ? "active-chip" : "inactive-chip"}`}>
                    {user.is_active ? ui.documentActivatedLabel : ui.documentDeactivatedLabel}
                  </span>
                </td>
                <td>{formatDateTime(user.created_at)}</td>
                <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                  <div className="admin-table-actions">
                    <button className="admin-icon-button" onClick={() => setModalState({ mode: "edit", user })} title={ui.editUserButton} type="button">
                      <EditIcon />
                    </button>
                    <button className="admin-icon-button danger" onClick={() => void handleDelete(user.id)} title={ui.deleteUserConfirm} type="button">
                      <DeleteIcon />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalState ? (
        <div className="admin-modal-backdrop" onClick={() => setModalState(null)}>
          <div className="admin-modal-sheet" onClick={(event) => event.stopPropagation()}>
            <div className="admin-modal-head">
              <div>
                <p className="section-label">{translateAdminTabLabel(locale, "users")}</p>
                <h3>{modalState.mode === "create" ? ui.createUserButton : ui.editUserButton}</h3>
              </div>
              <button className="admin-icon-button" onClick={() => setModalState(null)} type="button">
                <CloseIcon />
              </button>
            </div>

            <div className="admin-modal-form admin-modal-scrollable">
              <div className="admin-form-field">
                <label className="composer-label" htmlFor="dashboard-user-full-name">{ui.authFullNameLabel}</label>
                <input id="dashboard-user-full-name" onChange={(event) => setFullName(event.target.value)} value={fullName} />
              </div>

              <div className="admin-form-field">
                <label className="composer-label" htmlFor="dashboard-user-email">{ui.authEmailLabel}</label>
                <input id="dashboard-user-email" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
              </div>

              <div className="admin-form-field">
                <label className="composer-label" htmlFor="dashboard-user-role">{ui.userRoleLabel}</label>
                <select id="dashboard-user-role" onChange={(event) => setRole(event.target.value as AdminUserWritePayload["role"])} value={role}>
                  {ROLE_OPTIONS.map((roleOption) => (
                    <option key={roleOption} value={roleOption}>{translateRole(locale, roleOption)}</option>
                  ))}
                </select>
              </div>

              <div className="admin-form-field">
                <label className="composer-label" htmlFor="dashboard-user-password">{ui.authPasswordLabel}</label>
                <input id="dashboard-user-password" onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
                {modalState.mode === "edit" ? <small className="admin-inline-help">{ui.userPasswordEditHelp}</small> : null}
              </div>

              <label className="admin-switch-row" htmlFor="dashboard-user-active">
                <input checked={isActive} id="dashboard-user-active" onChange={(event) => setIsActive(event.target.checked)} type="checkbox" />
                <span>{ui.activeUserLabel}</span>
              </label>
            </div>

            <div className="admin-modal-actions">
              <button className="ghost-button" onClick={() => setModalState(null)} type="button">{ui.cancelButton}</button>
              <button className="primary-button" disabled={savingAdmin || !fullName.trim() || !email.trim() || (modalState.mode === "create" && password.trim().length < 8)} onClick={() => void handleSubmit()} type="button">
                {savingAdmin ? ui.savingDocumentButton : modalState.mode === "create" ? ui.createUserButton : ui.saveChangesButton}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M7 7L17 17M17 7L7 17" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4.75 19.25h3.5l9.4-9.4-3.5-3.5-9.4 9.4v3.5Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M13.65 6.35l3.5 3.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function DeleteIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M5.5 7.25h13" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M9.5 10.75v5.5M14.5 10.75v5.5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M7.25 7.25l.9 11h7.7l.9-11M9 7.25l.85-1.5h4.3L15 7.25" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function AddIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}