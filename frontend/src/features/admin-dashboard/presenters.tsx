import type { AIUsageByDocumentItem } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { formatUsageCurrency } from "./helpers";

export function AdminStatCard({ label, value, tone = "neutral" }: { label: string; value: number; tone?: "neutral" | "ok" | "warning" | "danger" | "info" }) {
  return (
    <article className={`admin-stat-card admin-stat-card-modern admin-stat-tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export function AIUsageByDocumentTable({ items, locale, ui }: { items: AIUsageByDocumentItem[]; locale: Locale; ui: UiText }) {
  return (
    <div className="admin-modal-scrollable">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{ui.aiUsageDocumentLabel}</th>
            <th>{ui.aiUsageModelsLabel}</th>
            <th>{ui.aiUsageMetadataRequestsLabel}</th>
            <th>{ui.aiUsageEmbeddingRequestsLabel}</th>
            <th>{ui.aiUsageInputTokensLabel}</th>
            <th>{ui.aiUsageOutputTokensLabel}</th>
            <th>{ui.aiUsageWebSearchCallsLabel}</th>
            <th>{ui.aiUsageCostLabel}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.document_id ?? "none"}-${index}`}>
              <td>
                <strong>{item.title}</strong>
                <div>{item.file_name ?? "--"}</div>
              </td>
              <td>{item.models_used.join(", ") || "--"}</td>
              <td>{item.metadata_requests}</td>
              <td>{item.embedding_requests}</td>
              <td>{item.input_tokens}</td>
              <td>{item.output_tokens}</td>
              <td>{item.web_search_calls}</td>
              <td>{formatUsageCurrency(locale, item.estimated_cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
