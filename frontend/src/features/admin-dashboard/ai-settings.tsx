import type { GraphBackendBenchmarkPayload, GraphBackendParityPayload } from "../../types/lawchat";
import type { AdminOperations } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { CHATBOT_PROVIDER_MODEL_OPTIONS, METADATA_MODEL_LABELS, METADATA_PROVIDER_MODEL_OPTIONS } from "./helpers";
import { AIUsageByDocumentTable } from "./presenters";

function formatGraphUpdatedAt(value: string, locale: Locale): string {
  const normalizedValue = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalizedValue);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(locale === "vi" ? "vi-VN" : "en-US");
}

export function AISettingsSection({
  adminData,
  chatbotEnabled,
  chatbotProvider,
  consultantChatbotModel,
  customerChatbotModel,
  embeddingEnabled,
  embeddingModel,
  graphBenchmark,
  graphInsightsMessage,
  graphBackend,
  graphParity,
  loadingGraphInsights,
  locale,
  metadataEnabled,
  metadataProvider,
  metadataModel,
  metadataWebSearchEnabled,
  publicChatbotModel,
  savingAdmin,
  ui,
  onChatbotEnabledChange,
  onChatbotProviderChange,
  onConsultantModelChange,
  onCustomerModelChange,
  onEmbeddingEnabledChange,
  onEmbeddingModelChange,
  onGraphBackendChange,
  onMetadataEnabledChange,
  onMetadataProviderChange,
  onMetadataModelChange,
  onMetadataWebSearchChange,
  onPublicModelChange,
  onRefreshGraphInsights,
  onSave,
}: {
  adminData: AdminOperations;
  chatbotEnabled: boolean;
  chatbotProvider: string;
  consultantChatbotModel: string;
  customerChatbotModel: string;
  embeddingEnabled: boolean;
  embeddingModel: string;
  graphBenchmark: GraphBackendBenchmarkPayload | null;
  graphInsightsMessage: string | null;
  graphBackend: string;
  graphParity: GraphBackendParityPayload | null;
  loadingGraphInsights: boolean;
  locale: Locale;
  metadataEnabled: boolean;
  metadataProvider: string;
  metadataModel: string;
  metadataWebSearchEnabled: boolean;
  publicChatbotModel: string;
  savingAdmin: boolean;
  ui: UiText;
  onChatbotEnabledChange: (value: boolean) => void;
  onChatbotProviderChange: (value: string) => void;
  onConsultantModelChange: (value: string) => void;
  onCustomerModelChange: (value: string) => void;
  onEmbeddingEnabledChange: (value: boolean) => void;
  onEmbeddingModelChange: (value: string) => void;
  onGraphBackendChange: (value: string) => void;
  onMetadataEnabledChange: (value: boolean) => void;
  onMetadataProviderChange: (value: string) => void;
  onMetadataModelChange: (value: string) => void;
  onMetadataWebSearchChange: (value: boolean) => void;
  onPublicModelChange: (value: string) => void;
  onRefreshGraphInsights: () => void;
  onSave: () => void;
}) {
  const providerLabel = (provider: string) => {
    if (provider === "anthropic") {
      return ui.aiProviderAnthropic;
    }
    return ui.aiProviderOpenAI;
  };
  const metadataModelOptions = METADATA_PROVIDER_MODEL_OPTIONS[metadataProvider] ?? adminData.metadata_ai_settings.available_models;
  const answerLayerModelOptions = CHATBOT_PROVIDER_MODEL_OPTIONS[chatbotProvider] ?? adminData.chatbot_ai_settings.available_models;
  const effectiveGraphBenchmark = graphBenchmark ?? adminData.graph_backend_insights?.benchmark ?? null;
  const effectiveGraphParity = graphParity ?? adminData.graph_backend_insights?.parity ?? null;
  const parityMatchedCount = effectiveGraphParity?.results.filter((item) => item.node_count_match && item.edge_count_match && item.edge_identity_match && item.anchor_match).length ?? 0;
  const relationalRuns = effectiveGraphBenchmark?.results.filter((item) => item.backend === "relational") ?? [];
  const neo4jRuns = effectiveGraphBenchmark?.results.filter((item) => item.backend === "neo4j") ?? [];
  const averageMs = (items: typeof relationalRuns) => items.length > 0 ? items.reduce((sum, item) => sum + item.avg_ms, 0) / items.length : 0;
  const relationalAvgMs = averageMs(relationalRuns);
  const neo4jAvgMs = averageMs(neo4jRuns);

  return (
    <div className="admin-overview-shell">
      <div className="admin-list-shell">
        <article className="admin-list-row"><div className="admin-row-main"><strong>{ui.metadataSettingsTitle}</strong><p>{adminData.metadata_ai_settings.enabled ? ui.metadataSettingsDescription : ui.metadataSettingsDisabledHelp}</p></div></article>
        <div className="admin-list-row">
          <div className="admin-row-main">
            <div className="admin-file-upload-row">
              <label className="admin-switch-row"><input checked={metadataEnabled} onChange={(event) => onMetadataEnabledChange(event.target.checked)} type="checkbox" /><span>{ui.metadataSettingsEnabledLabel}</span></label>
              <label className="admin-form-field"><span>{ui.aiProviderLabel}</span><select onChange={(event) => onMetadataProviderChange(event.target.value)} value={metadataProvider}>{adminData.metadata_ai_settings.available_providers.map((provider) => (<option key={`metadata-provider-${provider}`} value={provider}>{providerLabel(provider)}</option>))}</select></label>
              <label className="admin-form-field"><span>{ui.metadataSettingsModelLabel}</span><select onChange={(event) => onMetadataModelChange(event.target.value)} value={metadataModel}>{metadataModelOptions.map((model) => (<option key={model} value={model}>{METADATA_MODEL_LABELS[model] ?? model}</option>))}</select></label>
              <label className="admin-switch-row"><input checked={metadataWebSearchEnabled} onChange={(event) => onMetadataWebSearchChange(event.target.checked)} type="checkbox" /><span>{ui.metadataSettingsWebSearchLabel}</span></label>
            </div>
          </div>
        </div>
        <article className="admin-list-row"><div className="admin-row-main"><strong>{ui.embeddingSettingsTitle}</strong><p>{adminData.embedding_ai_settings.enabled ? ui.embeddingSettingsDescription : ui.embeddingSettingsDisabledHelp}</p></div></article>
        <div className="admin-list-row">
          <div className="admin-row-main">
            <div className="admin-file-upload-row">
              <label className="admin-switch-row"><input checked={embeddingEnabled} onChange={(event) => onEmbeddingEnabledChange(event.target.checked)} type="checkbox" /><span>{ui.embeddingSettingsEnabledLabel}</span></label>
              <label className="admin-form-field"><span>{ui.embeddingSettingsModelLabel}</span><select onChange={(event) => onEmbeddingModelChange(event.target.value)} value={embeddingModel}>{adminData.embedding_ai_settings.available_models.map((model) => (<option key={`embedding-${model}`} value={model}>{model}</option>))}</select></label>
            </div>
          </div>
        </div>
        <article className="admin-list-row"><div className="admin-row-main"><strong>{ui.chatbotSettingsTitle}</strong><p>{adminData.chatbot_ai_settings.enabled ? ui.chatbotSettingsDescription : ui.chatbotSettingsDisabledHelp}</p></div></article>
        <div className="admin-list-row">
          <div className="admin-row-main">
            <div className="admin-file-upload-row">
              <label className="admin-switch-row"><input checked={chatbotEnabled} onChange={(event) => onChatbotEnabledChange(event.target.checked)} type="checkbox" /><span>{ui.chatbotSettingsEnabledLabel}</span></label>
              <label className="admin-form-field"><span>{ui.aiProviderLabel}</span><select onChange={(event) => onChatbotProviderChange(event.target.value)} value={chatbotProvider}>{adminData.chatbot_ai_settings.available_providers.map((provider) => (<option key={`chatbot-provider-${provider}`} value={provider}>{providerLabel(provider)}</option>))}</select></label>
              <label className="admin-form-field"><span>{locale === "vi" ? "Mô hình trả lời public" : "Public answer model"}</span><select onChange={(event) => onPublicModelChange(event.target.value)} value={publicChatbotModel}>{answerLayerModelOptions.map((model) => (<option key={`public-${model}`} value={model}>{METADATA_MODEL_LABELS[model] ?? model}</option>))}</select></label>
              <label className="admin-form-field"><span>{locale === "vi" ? "Mô hình trả lời khách hàng" : "Customer answer model"}</span><select onChange={(event) => onCustomerModelChange(event.target.value)} value={customerChatbotModel}>{answerLayerModelOptions.map((model) => (<option key={`customer-${model}`} value={model}>{METADATA_MODEL_LABELS[model] ?? model}</option>))}</select></label>
              <label className="admin-form-field"><span>{locale === "vi" ? "Mô hình trả lời tư vấn viên" : "Consultant answer model"}</span><select onChange={(event) => onConsultantModelChange(event.target.value)} value={consultantChatbotModel}>{answerLayerModelOptions.map((model) => (<option key={`consultant-${model}`} value={model}>{METADATA_MODEL_LABELS[model] ?? model}</option>))}</select></label>
            </div>
          </div>
        </div>
        <article className="admin-list-row"><div className="admin-row-main"><strong>{ui.graphBackendSettingsTitle}</strong><p>{ui.graphBackendSettingsDescription}</p></div></article>
        <div className="admin-list-row">
          <div className="admin-row-main">
            <div className="admin-file-upload-row">
              <label className="admin-form-field"><span>{ui.graphBackendLabel}</span><select onChange={(event) => onGraphBackendChange(event.target.value)} value={graphBackend}>{adminData.graph_backend_settings.available_backends.map((backend) => (<option key={`graph-backend-${backend}`} value={backend}>{backend === "neo4j" ? ui.graphBackendNeo4j : ui.graphBackendRelational}</option>))}</select></label>
              <div className="admin-inline-help">
                <strong>{ui.graphBackendCurrentStatusLabel}</strong>
                <span>{graphBackend === "neo4j" ? (adminData.graph_backend_settings.neo4j_available ? ui.graphBackendNeo4jReady : ui.graphBackendNeo4jUnavailable) : ui.graphBackendRelationalReady}</span>
              </div>
              <button className="secondary-button" disabled={loadingGraphInsights} onClick={onRefreshGraphInsights} type="button">{loadingGraphInsights ? ui.graphBackendBenchmarkLoadingButton : ui.graphBackendBenchmarkButton}</button>
              <button className="primary-button" disabled={savingAdmin} onClick={onSave} type="button">{savingAdmin ? ui.metadataSettingsSavingButton : ui.metadataSettingsSaveButton}</button>
            </div>
            <div className="admin-inline-help">
              <strong>{locale === "vi" ? "Kết quả benchmark/parity" : "Benchmark/parity result"}</strong>
              <span>
                {graphInsightsMessage
                  ?? (adminData.graph_backend_insights?.updated_at
                    ? (locale === "vi" ? "Đang hiển thị kết quả đã lưu từ lần chạy gần nhất." : "Showing the saved result from the latest run.")
                    : (locale === "vi" ? "Chưa có kết quả đã lưu. Bấm chạy benchmark và parity để tạo baseline." : "No saved result yet. Run benchmark and parity to create a baseline."))}
              </span>
            </div>
            {effectiveGraphBenchmark || effectiveGraphParity ? (
              <div className="admin-document-detail-grid">
                {effectiveGraphParity ? (
                  <span>
                    {locale === "vi" ? "Parity" : "Parity"}: {parityMatchedCount}/{effectiveGraphParity.results.length} {locale === "vi" ? "case khớp" : "cases matched"}
                  </span>
                ) : null}
                {effectiveGraphBenchmark ? (
                  <>
                    <span>Relational avg: {relationalAvgMs.toFixed(2)} ms</span>
                    <span>Neo4j avg: {neo4jAvgMs.toFixed(2)} ms</span>
                    <span>{locale === "vi" ? "Số case benchmark" : "Benchmark cases"}: {effectiveGraphBenchmark.results.length}</span>
                  </>
                ) : null}
              </div>
            ) : null}
            {effectiveGraphParity ? (
              <div className="admin-document-detail-grid">
                {effectiveGraphParity.results.map((item) => (
                  <span key={`parity-${item.document_id}-${item.depth}`}>
                    Doc {item.document_id} d{item.depth}: {item.node_count_match && item.edge_count_match && item.edge_identity_match && item.anchor_match ? ui.graphBackendParityMatchLabel : ui.graphBackendParityMismatchLabel}
                  </span>
                ))}
              </div>
            ) : null}
            {adminData.graph_backend_insights?.updated_at ? (
              <p className="admin-row-time">
                {ui.graphBackendLastUpdatedLabel}: {formatGraphUpdatedAt(adminData.graph_backend_insights.updated_at, locale)}
              </p>
            ) : null}
            {effectiveGraphBenchmark ? (
              <div className="admin-graph-relation-list">
                {effectiveGraphBenchmark.results.map((item) => (
                  <article className="admin-graph-relation-item" key={`benchmark-${item.backend}-${item.document_id}-${item.depth}`}>
                    <div className="admin-graph-relation-item-head">
                      <span className="admin-graph-edge-badge">{item.backend} | doc {item.document_id} | d{item.depth}</span>
                      <span className="admin-graph-confidence">{item.avg_ms} ms</span>
                    </div>
                    <p className="admin-document-detail-summary">
                      {ui.graphBackendBenchmarkDetails(item.min_ms, item.max_ms, item.node_count, item.edge_count)}
                    </p>
                  </article>
                ))}
              </div>
            ) : null}
            {adminData.graph_backend_insights?.recommendation ? (
              <div className="admin-graph-relation-list">
                <article className="admin-graph-relation-item">
                  <div className="admin-graph-relation-item-head">
                    <span className="admin-graph-edge-badge">{ui.graphBackendRecommendationTitle}</span>
                    <span className="admin-graph-confidence">
                      {adminData.graph_backend_insights.recommendation.recommended_backend === "neo4j" ? ui.graphBackendNeo4j : ui.graphBackendRelational}
                    </span>
                  </div>
                  <p className="admin-document-detail-summary">
                    {adminData.graph_backend_insights.recommendation.summary}
                  </p>
                  <ul className="admin-document-detail-list">
                    {adminData.graph_backend_insights.recommendation.reasons.map((reason, index) => (
                      <li key={`graph-rec-${index}`}>{reason}</li>
                    ))}
                  </ul>
                </article>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="admin-list-shell">
        <article className="admin-list-row"><div className="admin-row-main"><strong>{ui.aiUsageByDocumentTitle}</strong></div></article>
        {adminData.ai_usage_by_document.length === 0 ? <p className="admin-row-time">{ui.aiUsageNoData}</p> : <AIUsageByDocumentTable items={adminData.ai_usage_by_document} locale={locale} ui={ui} />}
      </div>
    </div>
  );
}
