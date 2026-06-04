import { type ReactNode, useEffect, useState } from "react";

import type { LegalCaseItem, PlannerRunItem, ReviewQueueItem, ReviewQueuesPayload, Ticket, ValidationRunItem } from "../../types/lawchat";
import type { AdminOperations } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { translateAdminTabLabel, translateTicketStatus, translateTopic } from "../../locales/metadata";
import type { AdminTab } from "./types";
import { ArrowRightIcon, AddIcon, CloseIcon, FilterIcon, MenuIcon } from "./icons";
import { formatLegalCaseTitle, formatPlannerRunTitle, formatValidationRunTitle } from "./helpers";
import { AdminStatCard } from "./presenters";
import UserAccountMenu from "../../components/UserAccountMenu";
import { SimpleSearchSection } from "./section-shell";

type AdminNavGroup = {
  id: string;
  label: Record<Locale, string>;
  tabs: AdminTab[];
};

const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  { id: "planning", label: { vi: "Kế hoạch", en: "Planning" }, tabs: ["overview", "roadmap"] },
  { id: "content", label: { vi: "Nội dung website", en: "Website content" }, tabs: ["content-articles", "lawyer-profiles"] },
  { id: "knowledge", label: { vi: "Tri thức pháp lý", en: "Legal knowledge" }, tabs: ["documents", "annotation", "categories", "document-types", "authority-levels"] },
  { id: "runtime", label: { vi: "Runtime & AI", en: "Runtime & AI" }, tabs: ["ai-settings"] },
  { id: "operations", label: { vi: "Vận hành", en: "Operations" }, tabs: ["users", "tickets", "review-queues", "logs"] },
];

export function AdminDashboardSidebar({
  activeTab,
  isSidebarOpen,
  isDesktopSidebarCollapsed,
  locale,
  onClose,
  onHideMobileSidebar,
  onTabChange,
}: {
  activeTab: AdminTab;
  isSidebarOpen: boolean;
  isDesktopSidebarCollapsed: boolean;
  locale: Locale;
  onClose: () => void;
  onHideMobileSidebar: () => void;
  onTabChange: (tab: AdminTab) => void;
}) {
  const [openGroups, setOpenGroups] = useState<Set<string>>(
    () => new Set(ADMIN_NAV_GROUPS.filter((group) => group.tabs.includes(activeTab)).map((group) => group.id)),
  );

  useEffect(() => {
    const activeGroup = ADMIN_NAV_GROUPS.find((group) => group.tabs.includes(activeTab));
    if (!activeGroup) {
      return;
    }
    setOpenGroups((current) => {
      if (current.has(activeGroup.id)) {
        return current;
      }
      const next = new Set(current);
      next.add(activeGroup.id);
      return next;
    });
  }, [activeTab]);

  function toggleGroup(groupId: string) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }

  return (
    <aside className={`admin-sidebar admin-sidebar-modern ${isSidebarOpen ? "open" : ""} ${isDesktopSidebarCollapsed ? "collapsed" : ""}`}>
      <div className="admin-sidebar-top">
        <div className="chatgpt-sidebar-brand-row">
          <button className="chatgpt-logo-button" onClick={onClose} type="button">
            <span className="chatgpt-logo-mark">LA</span>
            <span className="chatgpt-logo-copy">
              <strong>LawChat-AI</strong>
              <small>{translateAdminTabLabel(locale, activeTab)}</small>
            </span>
          </button>

          <button className="admin-sidebar-close chatgpt-sidebar-close" onClick={onHideMobileSidebar} type="button">
            <CloseIcon />
          </button>
        </div>
      </div>

      <div className="admin-sidebar-scroll chatgpt-sidebar-scroll">
        <section className="chatgpt-sidebar-section admin-nav-section">
          <p className="section-label">{locale === "vi" ? "Quản trị" : "Admin"}</p>
          <nav className="admin-nav admin-nav-modern">
            {ADMIN_NAV_GROUPS.map((group) => {
              const isOpen = openGroups.has(group.id);
              const hasActiveChild = group.tabs.includes(activeTab);
              return (
                <div className={`admin-nav-group ${isOpen ? "open" : ""}`} key={group.id}>
                  <button className={`admin-nav-group-button ${hasActiveChild ? "active" : ""}`} onClick={() => toggleGroup(group.id)} type="button">
                    <strong>{group.label[locale]}</strong>
                    <span>{isOpen ? "−" : "+"}</span>
                  </button>
                  {isOpen ? (
                    <div className="admin-nav-subitems">
                      {group.tabs.map((tab) => (
                        <button className={`admin-nav-item ${activeTab === tab ? "active" : ""}`} key={tab} onClick={() => { onTabChange(tab); onHideMobileSidebar(); }} type="button">
                          <strong>{translateAdminTabLabel(locale, tab)}</strong>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </nav>
        </section>
      </div>
    </aside>
  );
}
export function AdminDashboardTopbar({
  activeTab,
  isDesktopSidebarCollapsed,
  isDocumentFiltersVisible,
  loadingAdmin,
  locale,
  ui,
  onLocaleChange,
  onRefresh,
  onToggleDesktopSidebar,
  onToggleDocumentFilters,
}: {
  activeTab: AdminTab;
  isDesktopSidebarCollapsed: boolean;
  isDocumentFiltersVisible: boolean;
  loadingAdmin: boolean;
  locale: Locale;
  ui: UiText;
  onLocaleChange: (locale: Locale) => void;
  onRefresh: () => void;
  onToggleDesktopSidebar: () => void;
  onToggleDocumentFilters: () => void;
}) {
  return (
    <div className="admin-content-top admin-content-top-modern">
      <div className="admin-content-heading">
        <div className="admin-content-heading-row">
          <p className="section-label">{ui.adminLabel}</p>
          {activeTab === "documents" ? (
            <button className="admin-icon-button admin-document-tools-toggle" onClick={onToggleDocumentFilters} title={isDocumentFiltersVisible ? ui.adminHideFiltersButton : ui.adminShowFiltersButton} type="button">
              <FilterIcon />
            </button>
          ) : null}
        </div>
        <h2>{translateAdminTabLabel(locale, activeTab)}</h2>
      </div>

      <div className={`admin-toolbar-actions ${activeTab === "documents" ? `admin-document-toolbar-actions ${isDocumentFiltersVisible ? "open" : "mobile-hidden"}` : ""}`}>
        <button className="admin-icon-button admin-desktop-sidebar-toggle" onClick={onToggleDesktopSidebar} title={isDesktopSidebarCollapsed ? ui.adminShowSidebarButton : ui.adminHideSidebarButton} type="button">
          <MenuIcon />
        </button>

        <div className="lang-toggle admin-toolbar-lang-toggle">
          <button className={locale === "vi" ? "active" : ""} onClick={() => onLocaleChange("vi")} type="button">VI</button>
          <button className={locale === "en" ? "active" : ""} onClick={() => onLocaleChange("en")} type="button">EN</button>
        </div>

        <button className="secondary-button admin-toolbar-button" onClick={onRefresh} type="button">
          {loadingAdmin ? ui.refreshingDashboardButton : ui.refreshButton}
        </button>
        <UserAccountMenu locale={locale} />
      </div>
    </div>
  );
}

export function AdminLoadingState({ locale }: { locale: Locale }) {
  return (
    <div className="admin-overview-shell">
      <div className="admin-hero-card admin-hero-card-modern">
        <div className="admin-hero-copy-block">
          <p className="section-label">{locale === "vi" ? "Dang tai du lieu" : "Loading data"}</p>
          <h3>{locale === "vi" ? "Dashboard dang khoi tao" : "Dashboard is initializing"}</h3>
          <p>
            {locale === "vi"
              ? "He thong dang tai overview, danh sach tai lieu va thong ke quan tri."
              : "The system is loading the overview, documents, and admin metrics."}
          </p>
        </div>
      </div>
    </div>
  );
}

export function OverviewSection({ adminData, locale, ui }: { adminData: AdminOperations; locale: Locale; ui: UiText }) {
  return (
    <div className="admin-overview-shell">
      <div className="admin-hero-card admin-hero-card-modern">
        <div className="admin-hero-copy-block">
          <p className="section-label">{ui.adminHeroEyebrow}</p>
          <h3>{ui.operationsHeroTitle}</h3>
          <p>{ui.operationsHeroDescription(adminData.overview.total_sessions, adminData.overview.total_documents, adminData.overview.total_tickets)}</p>
        </div>
        <div className="admin-hero-badges admin-hero-metrics">
          <div className="admin-hero-metric-pill">
            <span>{translateAdminTabLabel(locale, "documents")}</span>
            <strong>{adminData.overview.total_documents}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{ui.chunkCountLabel}</span>
            <strong>{adminData.overview.total_chunks}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{translateTicketStatus(locale, "in_progress")}</span>
            <strong>{adminData.overview.open_tickets}</strong>
          </div>
        </div>
      </div>

      <div className="admin-stat-grid admin-stat-grid-modern">
        <AdminStatCard label={locale === "vi" ? "Hồ sơ pháp lý" : "Legal cases"} value={adminData.overview.total_legal_cases} tone="info" />
        <AdminStatCard label={locale === "vi" ? "Hồ sơ đang mở" : "Active cases"} value={adminData.overview.active_legal_cases} tone="info" />
        <AdminStatCard label={translateAdminTabLabel(locale, "documents")} value={adminData.overview.total_documents} tone="ok" />
        <AdminStatCard label={ui.ingestedDocumentsStatLabel} value={adminData.overview.ingested_documents} tone="ok" />
        <AdminStatCard label={ui.chunkCountLabel} value={adminData.overview.total_chunks} tone="neutral" />
        <AdminStatCard label={ui.openRequestsStatLabel} value={adminData.overview.open_tickets} tone={adminData.overview.open_tickets > 0 ? "warning" : "ok"} />
        <AdminStatCard label={locale === "vi" ? "Cần review" : "Needs review"} value={adminData.overview.validation_runs_needing_review} tone={adminData.overview.validation_runs_needing_review > 0 ? "warning" : "ok"} />
        <AdminStatCard label={locale === "vi" ? "Citation đã lưu" : "Stored citations"} value={adminData.overview.total_citations} tone="neutral" />
        <AdminStatCard label={locale === "vi" ? "Quan hệ văn bản" : "Document relations"} value={adminData.overview.total_document_relations} tone="neutral" />
      </div>
    </div>
  );
}
export function TicketsSection({
  actionsColumnLabel,
  locale,
  reasonColumnLabel,
  search,
  tickets,
  titleColumnLabel,
  topicColumnLabel,
  ui,
  onClear,
  onOpenTicket,
  onSearchChange,
}: {
  actionsColumnLabel: string;
  locale: Locale;
  reasonColumnLabel: string;
  search: string;
  tickets: Ticket[];
  titleColumnLabel: string;
  topicColumnLabel: string;
  ui: UiText;
  onClear: () => void;
  onOpenTicket: (ticketId: number) => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <SimpleSearchSection
      toolbar={
        <>
          <div className="admin-table-filters"><input className="admin-filter-input" onChange={(event) => onSearchChange(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={search} /></div>
          <button className="ghost-button admin-filter-clear-button" onClick={onClear} type="button">{ui.adminClearFiltersButton}</button>
        </>
      }
    >
      <table className="admin-table admin-table-compact">
        <thead>
          <tr>
            <th>{titleColumnLabel}</th>
            <th>{topicColumnLabel}</th>
            <th>{ui.statusLabel}</th>
            <th>{reasonColumnLabel}</th>
            <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
          </tr>
        </thead>
        <tbody>
          {tickets.length === 0 ? (
            <tr><td colSpan={5}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td></tr>
          ) : tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td><div className="admin-table-title">#{ticket.id} {ticket.title}</div></td>
              <td>{translateTopic(locale, ticket.topic)}</td>
              <td>{translateTicketStatus(locale, ticket.status)}</td>
              <td>{ticket.escalation_reason}</td>
              <td className="admin-table-sticky-col admin-table-sticky-col-actions"><div className="admin-table-actions"><button className="admin-icon-button primary" onClick={() => onOpenTicket(ticket.id)} title={ui.openTicketAction} type="button"><ArrowRightIcon /></button></div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </SimpleSearchSection>
  );
}

const REVIEW_QUEUE_ORDER = ["ocr_text_quality", "metadata_review", "provision_review", "relation_review", "validation_failures", "benchmark_failures"];

function reviewQueueLabel(locale: Locale, queue: string): string {
  const labels: Record<string, Record<Locale, string>> = {
    ocr_text_quality: { vi: "OCR / text quality", en: "OCR / text quality" },
    metadata_review: { vi: "Metadata", en: "Metadata" },
    provision_review: { vi: "Điều khoản", en: "Provisions" },
    relation_review: { vi: "Quan hệ", en: "Relations" },
    validation_failures: { vi: "Validation fail", en: "Validation failures" },
    benchmark_failures: { vi: "Benchmark fail", en: "Benchmark failures" },
  };
  return labels[queue]?.[locale] ?? queue;
}

function severityLabel(locale: Locale, item: ReviewQueueItem): string {
  const severity = item.severity === "high"
    ? (locale === "vi" ? "Cao" : "High")
    : item.severity === "medium"
      ? (locale === "vi" ? "Vừa" : "Medium")
      : (locale === "vi" ? "Thấp" : "Low");
  return `${severity} · ${item.status}`;
}

export function ReviewQueuesSection({
  formatDateTime,
  locale,
  reviewQueues,
  timeColumnLabel,
  titleColumnLabel,
  ui,
}: {
  formatDateTime: (value: string) => string;
  locale: Locale;
  reviewQueues: ReviewQueuesPayload | null;
  timeColumnLabel: string;
  titleColumnLabel: string;
  ui: UiText;
}) {
  const queues = reviewQueues?.queues ?? {};
  const queueNames = REVIEW_QUEUE_ORDER.filter((queue) => queues[queue]?.length).concat(
    Object.keys(queues).filter((queue) => !REVIEW_QUEUE_ORDER.includes(queue) && queues[queue]?.length),
  );
  const totalItems = Object.values(reviewQueues?.summary ?? {}).reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="admin-overview-shell">
      <div className="admin-stat-grid admin-stat-grid-modern">
        <AdminStatCard label={locale === "vi" ? "Tổng việc" : "Total items"} value={totalItems} />
        <AdminStatCard label={reviewQueueLabel(locale, "metadata_review")} value={reviewQueues?.summary.metadata_review?.count ?? 0} />
        <AdminStatCard label={reviewQueueLabel(locale, "validation_failures")} value={reviewQueues?.summary.validation_failures?.count ?? 0} />
        <AdminStatCard label={reviewQueueLabel(locale, "benchmark_failures")} value={reviewQueues?.summary.benchmark_failures?.count ?? 0} />
      </div>

      {queueNames.length === 0 ? (
        <div className="admin-table-section">
          <div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div>
        </div>
      ) : queueNames.map((queueName) => {
        const items = queues[queueName] ?? [];
        return (
          <LogsTable key={queueName} title={reviewQueueLabel(locale, queueName)}>
            <table className="admin-table admin-table-compact">
              <thead><tr><th>{titleColumnLabel}</th><th>{ui.statusLabel}</th><th>{ui.categoryDescriptionLabel}</th><th>{timeColumnLabel}</th></tr></thead>
              <tbody>
                {items.map((item) => (
                  <tr key={`${item.source_type}-${item.source_id}`}>
                    <td className="admin-table-title-cell">{item.title}</td>
                    <td>{severityLabel(locale, item)}</td>
                    <td>{item.detail} {item.action}</td>
                    <td>{item.created_at ? formatDateTime(item.created_at) : "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </LogsTable>
        );
      })}
    </div>
  );
}

function LogsTable({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="admin-table-section">
      <div className="admin-list-row"><div className="admin-row-main"><strong>{title}</strong></div></div>
      <div className="admin-table-wrap">{children}</div>
    </div>
  );
}

function RecentEntityTable({ emptyLabel, rows, timeColumnLabel, titleColumnLabel, ui }: { emptyLabel: string; rows: ReactNode; timeColumnLabel: string; titleColumnLabel: string; ui: UiText }) {
  return (
    <table className="admin-table admin-table-compact">
      <thead><tr><th>{titleColumnLabel}</th><th>{ui.categoryDescriptionLabel}</th><th>{timeColumnLabel}</th></tr></thead>
      <tbody>{rows ?? <tr><td colSpan={3}><div className="admin-table-empty">{emptyLabel}</div></td></tr>}</tbody>
    </table>
  );
}

function parseJsonObject(value: string | null | undefined): Record<string, unknown> | null {
  if (!value) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

function parseJsonArray(value: string | null | undefined): unknown[] {
  if (!value) {
    return [];
  }
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function getPlannerAuditSummary(locale: Locale, run: PlannerRunItem): string {
  const plan = parseJsonObject(run.plan_json);
  const context = parseJsonObject(run.context_json);
  const steps = Array.isArray(plan?.steps) ? plan.steps : [];
  const stepSummary = steps
    .filter((step): step is Record<string, unknown> => Boolean(step) && typeof step === "object")
    .slice(0, 4)
    .map((step) => `${String(step.step ?? "--")}:${String(step.status ?? "--")}`)
    .join(" | ");
  const evidenceCount = context?.search_result_count ?? "--";
  const citationCoverage = context?.citation_coverage_score ?? "--";
  const semanticMatches = context?.semantic_match_count ?? "--";
  const prefix = locale === "vi" ? "Audit" : "Audit";
  return `${prefix}: evidence=${String(evidenceCount)} | citation=${String(citationCoverage)} | semantic=${String(semanticMatches)}${stepSummary ? ` | ${stepSummary}` : ""}`;
}

function getValidationAuditSummary(locale: Locale, run: ValidationRunItem): string {
  const findings = parseJsonArray(run.findings_json).map((item) => String(item)).slice(0, 2);
  const responseExcerpt = (run.response_text ?? "").replace(/\s+/g, " ").trim().slice(0, 140);
  const escalation = run.escalation_recommended ? (locale === "vi" ? "co" : "yes") : (locale === "vi" ? "khong" : "no");
  const findingText = findings.length > 0 ? ` | ${findings.join(" | ")}` : "";
  const responseText = responseExcerpt ? ` | ${responseExcerpt}` : "";
  return `Confidence: ${run.confidence_score ?? "--"} | Escalation: ${escalation}${findingText}${responseText}`;
}

export function LogsSection({
  activities,
  formatDateTime,
  legalCases,
  locale,
  plannerRuns,
  search,
  timeColumnLabel,
  titleColumnLabel,
  ui,
  validationRuns,
  onClear,
  onSearchChange,
}: {
  activities: AdminOperations["activities"];
  formatDateTime: (value: string) => string;
  legalCases: LegalCaseItem[];
  locale: Locale;
  plannerRuns: PlannerRunItem[];
  search: string;
  timeColumnLabel: string;
  titleColumnLabel: string;
  ui: UiText;
  validationRuns: ValidationRunItem[];
  onClear: () => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <div className="admin-overview-shell">
      <div className="admin-table-section">
        <div className="admin-table-toolbar">
          <div className="admin-table-filters"><input className="admin-filter-input" onChange={(event) => onSearchChange(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={search} /></div>
          <button className="ghost-button admin-filter-clear-button" onClick={onClear} type="button">{ui.adminClearFiltersButton}</button>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-compact">
            <thead><tr><th>{titleColumnLabel}</th><th>{ui.categoryDescriptionLabel}</th><th>{timeColumnLabel}</th></tr></thead>
            <tbody>
              {activities.length === 0 ? (
                <tr><td colSpan={3}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td></tr>
              ) : activities.map((activity, index) => (
                <tr key={`${activity.event_type}-${index}`}><td className="admin-table-title-cell">{activity.title}</td><td>{activity.description}</td><td>{formatDateTime(activity.occurred_at)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <LogsTable title={locale === "vi" ? "Legal cases gan day" : "Recent legal cases"}>
        <RecentEntityTable
          emptyLabel={ui.adminNoMatchingResultsLabel}
          rows={legalCases.length === 0 ? null : legalCases.map((legalCase) => (
            <tr key={legalCase.id}><td className="admin-table-title-cell">{formatLegalCaseTitle(locale, legalCase)}</td><td>{legalCase.summary || legalCase.desired_outcome || `${legalCase.status} | ${legalCase.risk_level}`}</td><td>{formatDateTime(legalCase.updated_at)}</td></tr>
          ))}
          timeColumnLabel={timeColumnLabel}
          titleColumnLabel={titleColumnLabel}
          ui={ui}
        />
      </LogsTable>

      <LogsTable title={locale === "vi" ? "Planner runs gan day" : "Recent planner runs"}>
        <RecentEntityTable
          emptyLabel={ui.adminNoMatchingResultsLabel}
          rows={plannerRuns.length === 0 ? null : plannerRuns.map((run) => (
            <tr key={run.id}><td className="admin-table-title-cell">{formatPlannerRunTitle(locale, run)}</td><td>{getPlannerAuditSummary(locale, run)}</td><td>{formatDateTime(run.updated_at)}</td></tr>
          ))}
          timeColumnLabel={timeColumnLabel}
          titleColumnLabel={titleColumnLabel}
          ui={ui}
        />
      </LogsTable>

      <LogsTable title={locale === "vi" ? "Validation runs gan day" : "Recent validation runs"}>
        <RecentEntityTable
          emptyLabel={ui.adminNoMatchingResultsLabel}
          rows={validationRuns.length === 0 ? null : validationRuns.map((run) => (
            <tr key={run.id}>
              <td className="admin-table-title-cell">{formatValidationRunTitle(run)}</td>
              <td>{getValidationAuditSummary(locale, run)}</td>
              <td>{formatDateTime(run.updated_at)}</td>
            </tr>
          ))}
          timeColumnLabel={timeColumnLabel}
          titleColumnLabel={titleColumnLabel}
          ui={ui}
        />
      </LogsTable>
    </div>
  );
}

export function FloatingAddButton({ activeTab, ui, onOpenCreateAuthorityLevel, onOpenCreateCategory, onOpenCreateContentArticle, onOpenCreateDocument, onOpenCreateDocumentType, onOpenCreateLawyerProfile }: { activeTab: AdminTab; ui: UiText; onOpenCreateAuthorityLevel: () => void; onOpenCreateCategory: () => void; onOpenCreateContentArticle: () => void; onOpenCreateDocument: () => void; onOpenCreateDocumentType: () => void; onOpenCreateLawyerProfile: () => void }) {
  const title = activeTab === "categories"
    ? ui.createCategoryButton
    : activeTab === "document-types"
      ? ui.createDocumentTypeButton
      : activeTab === "authority-levels"
        ? ui.createAuthorityLevelButton
        : activeTab === "content-articles"
          ? "Thêm bài viết"
          : activeTab === "lawyer-profiles"
            ? "Thêm luật sư"
            : ui.addDocumentButton;
  const handleClick = activeTab === "categories"
    ? onOpenCreateCategory
    : activeTab === "document-types"
      ? onOpenCreateDocumentType
      : activeTab === "authority-levels"
        ? onOpenCreateAuthorityLevel
        : activeTab === "content-articles"
          ? onOpenCreateContentArticle
          : activeTab === "lawyer-profiles"
            ? onOpenCreateLawyerProfile
            : onOpenCreateDocument;

  return (
    <button aria-label={title} className="admin-floating-add-button" onClick={handleClick} title={title} type="button">
      <AddIcon />
    </button>
  );
}

