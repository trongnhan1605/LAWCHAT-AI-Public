import type { DefinitionItem, LegalCaseItem, PlannerRunItem, ValidationRunItem } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { DOCUMENT_EXTRACT_DRAFT_PREFIX } from "./types";

export const EMPTY_DEFINITION_ITEMS: DefinitionItem[] = [];

export const STATIC_DOCUMENT_TYPE_LABELS = {
  vi: {
    "bo-luat": "1 - Bộ luật",
    luat: "2 - Luật",
    "nghi-quyet": "3 - Nghị quyết",
    "nghi-dinh": "4 - Nghị định",
    "thong-tu": "5 - Thông tư",
    "quyet-dinh": "6 - Quyết định",
    "chi-thi": "7 - Chỉ thị",
    "an-le": "8 - Án lệ",
    khac: "9 - Khác",
  },
  en: {
    "bo-luat": "1 - Code",
    luat: "2 - Law",
    "nghi-quyet": "3 - Resolution",
    "nghi-dinh": "4 - Decree",
    "thong-tu": "5 - Circular",
    "quyet-dinh": "6 - Decision",
    "chi-thi": "7 - Directive",
    "an-le": "8 - Case law",
    khac: "9 - Other",
  },
} as const;

export const LEGAL_STATUS_LABELS = {
  vi: { active: "Còn hiệu lực", expired: "Hết hiệu lực", repealed: "Bị thay thế/bãi bỏ", draft: "Dự thảo", unknown: "Chưa rõ" },
  en: { active: "Active", expired: "Expired", repealed: "Repealed", draft: "Draft", unknown: "Unknown" },
} as const;

export const METADATA_MODEL_LABELS: Record<string, string> = {
  "cx/gpt-5.5": "9router gpt-5.5",
  "cx/gpt-5.4": "9router gpt-5.4",
  "cx/gpt-5.2": "9router gpt-5.2",
  "cx/gpt-5.3-codex-high": "9router gpt-5.3 codex high",
  "cx/gpt-5.3-codex-low": "9router gpt-5.3 codex low",
  "gpt-5.4-nano": "gpt-5.4 nano",
  "gpt-5.4-mini": "gpt-5.4 mini",
  "gpt-5.4": "gpt-5.4",
  "gpt-4.1": "gpt-4.1",
  "gpt-4.1-mini": "gpt-4.1 mini",
  "claude-3-5-haiku-latest": "Claude 3.5 Haiku",
  "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
};

export const METADATA_PROVIDER_MODEL_OPTIONS: Record<string, string[]> = {
  openai: ["cx/gpt-5.5", "cx/gpt-5.4", "cx/gpt-5.2", "cx/gpt-5.3-codex-high", "cx/gpt-5.3-codex-low", "gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4", "gpt-4.1", "gpt-4.1-mini"],
  anthropic: ["claude-3-5-haiku-latest", "claude-3-7-sonnet-latest"],
};

export const CHATBOT_PROVIDER_MODEL_OPTIONS: Record<string, string[]> = {
  openai: ["cx/gpt-5.5", "cx/gpt-5.4", "cx/gpt-5.2", "cx/gpt-5.3-codex-high", "cx/gpt-5.3-codex-low", "gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4", "gpt-4.1", "gpt-4.1-mini"],
  anthropic: ["claude-3-5-haiku-latest", "claude-3-7-sonnet-latest"],
};

export const RELATION_TAXONOMY = {
  repeals: {
    color: "#b91c1c",
    borderColor: "#fecaca",
    background: "#fef2f2",
    lineStyle: "solid",
    weight: "strong",
    vi: { label: "Bãi bỏ", effect: "Văn bản nguồn chấm dứt hiệu lực toàn bộ hoặc một phần văn bản đích." },
    en: { label: "Repeals", effect: "The source document removes legal effect of the target document or provisions." },
  },
  replaces: {
    color: "#c2410c",
    borderColor: "#fed7aa",
    background: "#fff7ed",
    lineStyle: "solid",
    weight: "strong",
    vi: { label: "Thay thế", effect: "Văn bản nguồn thay thế trực tiếp văn bản hoặc quy định đích." },
    en: { label: "Replaces", effect: "The source document directly replaces the target document or provisions." },
  },
  amends: {
    color: "#a16207",
    borderColor: "#fde68a",
    background: "#fffbeb",
    lineStyle: "solid",
    weight: "strong",
    vi: { label: "Sửa đổi", effect: "Văn bản nguồn sửa đổi nội dung của văn bản đích." },
    en: { label: "Amends", effect: "The source document amends the content of the target document." },
  },
  supplements: {
    color: "#ea580c",
    borderColor: "#fdba74",
    background: "#fff7ed",
    lineStyle: "solid",
    weight: "strong",
    vi: { label: "Bổ sung", effect: "Văn bản nguồn bổ sung quy định cho văn bản đích." },
    en: { label: "Supplements", effect: "The source document supplements the target document with additional rules." },
  },
  consolidates: {
    color: "#0f766e",
    borderColor: "#99f6e4",
    background: "#f0fdfa",
    lineStyle: "solid",
    weight: "medium",
    vi: { label: "Hợp nhất", effect: "VBHN hợp nhất nội dung văn bản gốc và các lần sửa đổi, bổ sung." },
    en: { label: "Consolidates", effect: "A consolidated text combines the original document and later amendments." },
  },
  guides_implementation: {
    color: "#2563eb",
    borderColor: "#bfdbfe",
    background: "#eff6ff",
    lineStyle: "solid",
    weight: "medium",
    vi: { label: "Hướng dẫn thi hành", effect: "Văn bản nguồn quy định chi tiết hoặc hướng dẫn thực hiện văn bản đích." },
    en: { label: "Guides implementation", effect: "The source document details or guides implementation of the target document." },
  },
  legal_basis: {
    color: "#1d4ed8",
    borderColor: "#93c5fd",
    background: "#eff6ff",
    lineStyle: "solid",
    weight: "medium",
    vi: { label: "Căn cứ pháp lý", effect: "Văn bản đích được viện dẫn làm căn cứ ban hành hoặc lập luận pháp lý." },
    en: { label: "Legal basis", effect: "The target document is cited as legal basis for promulgation or legal reasoning." },
  },
  general_reference: {
    color: "#475569",
    borderColor: "#cbd5e1",
    background: "#f8fafc",
    lineStyle: "dashed",
    weight: "light",
    vi: { label: "Dẫn chiếu chung", effect: "Văn bản nguồn chỉ dẫn chiếu hoặc tham chiếu tới văn bản đích." },
    en: { label: "General reference", effect: "The source document only references the target document without direct modifying effect." },
  },
} as const;

export function normalizeSearchValue(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

export function formatPlannerRunTitle(locale: Locale, run: PlannerRunItem): string {
  const intent = run.detected_intent ?? (locale === "vi" ? "chua-ro" : "unknown");
  const domain = run.detected_domain ?? (locale === "vi" ? "chua-ro" : "unknown");
  return `Planner #${run.id} | ${intent} | ${domain}`;
}

export function formatLegalCaseTitle(locale: Locale, legalCase: LegalCaseItem): string {
  const domain = legalCase.legal_domain ?? (locale === "vi" ? "chua-ro" : "unknown");
  return `Case #${legalCase.id} | ${domain} | ${legalCase.risk_level}`;
}

export function formatValidationRunTitle(run: ValidationRunItem): string {
  return `Validation #${run.id} | ${run.validation_status}`;
}

export function getDefinitionLabel(items: DefinitionItem[] | undefined, value: string | null | undefined, fallbackLabels: Record<Locale, Record<string, string>>, locale: Locale): string {
  if (!value) {
    return "--";
  }
  const match = items?.find((item) => item.slug === value);
  if (match) {
    return `${match.priority} - ${match.name}`;
  }
  return fallbackLabels[locale][value as keyof typeof fallbackLabels[typeof locale]] ?? value;
}

export function getDocumentTypeLabel(locale: Locale, value: string | null | undefined, items?: DefinitionItem[]): string {
  return getDefinitionLabel(items, value, STATIC_DOCUMENT_TYPE_LABELS, locale);
}

export function getDocumentTypeName(locale: Locale, value: string | null | undefined, items?: DefinitionItem[]): string {
  if (!value) {
    return "--";
  }
  const match = items?.find((item) => item.slug === value) ?? { name: value };
  if (match) {
    return match.name;
  }
  const fallback = STATIC_DOCUMENT_TYPE_LABELS[locale][value as keyof typeof STATIC_DOCUMENT_TYPE_LABELS[typeof locale]] ?? value;
  return fallback.includes(" - ") ? fallback.split(" - ").slice(1).join(" - ") : fallback;
}

export function getLegalStatusLabel(locale: Locale, value: string | null | undefined): string {
  if (!value) {
    return "--";
  }
  return LEGAL_STATUS_LABELS[locale][value as keyof typeof LEGAL_STATUS_LABELS[typeof locale]] ?? value;
}

export function getLegalStatusTone(value: string | null | undefined): string {
  switch (value) {
    case "active":
      return "legal-status-active";
    case "expired":
      return "legal-status-expired";
    case "repealed":
      return "legal-status-repealed";
    case "draft":
      return "legal-status-draft";
    default:
      return "legal-status-unknown";
  }
}

export function getMetadataReviewLabel(locale: Locale, value: string | null | undefined, ui: UiText): string {
  if (value === "reviewed") {
    return ui.documentMetadataReviewedLabel;
  }
  if (value === "pending_review") {
    return ui.documentMetadataPendingReviewLabel;
  }
  return value ?? (locale === "vi" ? "Chua ro" : "Unknown");
}

export function getMetadataReviewTone(value: string | null | undefined): string {
  return value === "reviewed" ? "review-status-reviewed" : "review-status-pending";
}

export function getRelationSyncLabel(locale: Locale, value: string | null | undefined, ui: UiText): string {
  if (value === "synced") {
    return ui.documentRelationSyncedLabel;
  }
  if (value === "no_matches") {
    return ui.documentRelationNoMatchLabel;
  }
  if (value === "failed") {
    return ui.documentRelationFailedLabel;
  }
  return locale === "vi" ? "Cho dong bo" : "Pending";
}

export function getQualityLabel(locale: Locale, value: string | null | undefined): string {
  switch (value) {
    case "direct_text_high":
      return locale === "vi" ? "Nguon text truc tiep - cao" : "Direct text - high";
    case "direct_text_medium":
      return locale === "vi" ? "Nguon text truc tiep - trung binh" : "Direct text - medium";
    case "direct_text_low":
      return locale === "vi" ? "Nguon text truc tiep - thap" : "Direct text - low";
    case "ocr_high":
      return locale === "vi" ? "OCR - cao" : "OCR - high";
    case "ocr_medium":
      return locale === "vi" ? "OCR - trung binh" : "OCR - medium";
    case "ocr_low":
      return locale === "vi" ? "OCR - thap" : "OCR - low";
    default:
      return value ?? "--";
  }
}

export function getQualityPrefix(locale: Locale, label: string | null | undefined): string {
  if ((label ?? "").startsWith("ocr_")) {
    return locale === "vi" ? "OCR" : "OCR";
  }
  return locale === "vi" ? "Text" : "Text";
}

export function getRelationDefinition(locale: Locale, relationType: string | null | undefined) {
  const definition = relationType ? RELATION_TAXONOMY[relationType as keyof typeof RELATION_TAXONOMY] : undefined;
  if (definition) {
    return {
      label: definition[locale].label,
      effect: definition[locale].effect,
      color: definition.color,
      borderColor: definition.borderColor,
      background: definition.background,
      lineStyle: definition.lineStyle,
      weight: definition.weight,
    };
  }
  return {
    label: relationType ?? "--",
    effect: relationType ?? "--",
    color: "#475569",
    borderColor: "#cbd5e1",
    background: "#f8fafc",
    lineStyle: "dashed",
    weight: "light",
  };
}

export function normalizeDefinitionValue(value: string | null | undefined, items: DefinitionItem[], fallback: string): string {
  if (value && items.some((item) => item.slug === value)) {
    return value;
  }
  return fallback;
}

export function buildDocumentExtractDraftKey(storagePath: string): string {
  return `${DOCUMENT_EXTRACT_DRAFT_PREFIX}:${storagePath.trim()}`;
}

export function loadDocumentExtractDraft(storagePath: string): string | null {
  if (typeof window === "undefined" || !storagePath.trim()) {
    return null;
  }
  return window.localStorage.getItem(buildDocumentExtractDraftKey(storagePath));
}

export function saveDocumentExtractDraft(storagePath: string, value: string): void {
  if (typeof window === "undefined" || !storagePath.trim()) {
    return;
  }
  window.localStorage.setItem(buildDocumentExtractDraftKey(storagePath), value);
}

export function clearDocumentExtractDraft(storagePath: string): void {
  if (typeof window === "undefined" || !storagePath.trim()) {
    return;
  }
  window.localStorage.removeItem(buildDocumentExtractDraftKey(storagePath));
}

export function formatUsageCurrency(locale: Locale, value: number): string {
  return new Intl.NumberFormat(locale === "vi" ? "vi-VN" : "en-US", { style: "currency", currency: "USD", maximumFractionDigits: 4 }).format(value);
}
