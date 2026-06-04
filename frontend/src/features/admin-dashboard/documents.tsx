import { type CSSProperties } from "react";

import type {
  AdminOperations,
  CorpusQualityDocumentItem,
  CorpusQualityReport,
  DocumentItem,
  ExtractionDiagnostic,
} from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { translateBooleanState } from "../../locales/metadata";
import {
  getDocumentTypeLabel,
  getDocumentTypeName,
  getLegalStatusLabel,
  getLegalStatusTone,
  getMetadataReviewLabel,
  getMetadataReviewTone,
  getQualityLabel,
  getQualityPrefix,
  getRelationDefinition,
  getRelationSyncLabel,
  RELATION_TAXONOMY,
} from "./helpers";
import {
  ChunkIcon,
  DeleteIcon,
  DownloadIcon,
  EditIcon,
  ExpandIcon,
  RelationIcon,
  StructureIcon,
} from "./icons";
import type {
  DocumentSortKey,
  GraphConnection,
  GraphViewerState,
} from "./types";

function getStableDocumentTitle(document: DocumentItem, locale: Locale, adminData: AdminOperations): string {
  const documentCode = document.document_code?.trim();
  if (documentCode) {
    return `${documentCode} · ${getDocumentTypeName(locale, document.document_type, adminData.document_types)}`;
  }
  return document.file_name?.trim() || document.title;
}

function getQualityIssueLabel(locale: Locale, issueCode: string): string {
  const labels: Record<string, Record<Locale, string>> = {
    document_code_year_mismatch_filename: {
      vi: "Mã văn bản lệch năm so với tên file",
      en: "Document code year differs from file name",
    },
    legal_status_not_authoritative: {
      vi: "Trạng thái pháp lý chưa đủ tin cậy",
      en: "Legal status is not authoritative",
    },
    low_ocr_quality: {
      vi: "Chất lượng text/OCR thấp",
      en: "Low text/OCR quality",
    },
    metadata_pending_review: {
      vi: "Metadata đang chờ người kiểm",
      en: "Metadata is pending review",
    },
    ingestion_blocked: {
      vi: "Ingest bị chặn",
      en: "Ingestion blocked",
    },
    ingestion_review_required: {
      vi: "Ingest cần review",
      en: "Ingestion needs review",
    },
    no_chunks: {
      vi: "Chưa có chunk truy xuất",
      en: "No retrieval chunks",
    },
    no_structured_provisions: {
      vi: "Chưa tách được điều/khoản",
      en: "No structured provisions",
    },
    relation_missing_evidence: {
      vi: "Quan hệ thiếu đoạn chứng cứ",
      en: "Relation is missing evidence",
    },
    retrieval_blocked: {
      vi: "Retrieval đang bị chặn",
      en: "Retrieval is blocked",
    },
    retrieval_unreviewed: {
      vi: "Retrieval chưa được xác thực",
      en: "Retrieval is unreviewed",
    },
  };
  return labels[issueCode]?.[locale] ?? issueCode;
}

function getRiskLabel(locale: Locale, riskLevel: string): string {
  if (riskLevel === "high") {
    return locale === "vi" ? "Rủi ro cao" : "High risk";
  }
  if (riskLevel === "medium") {
    return locale === "vi" ? "Cần kiểm" : "Needs review";
  }
  return locale === "vi" ? "Ổn định" : "Low risk";
}

function getRiskTone(riskLevel: string): string {
  if (riskLevel === "high") {
    return "risk-high";
  }
  if (riskLevel === "medium") {
    return "risk-medium";
  }
  return "risk-low";
}

export function DocumentsSection({
  actionsColumnLabel,
  adminData,
  corpusQualityReport,
  currentDocumentPage,
  diagnosing,
  diagnostics,
  documentDomainFilter,
  documentFormatDateTime,
  documentPageSize,
  documentSearch,
  documentSortDirection,
  documentSortKey,
  documentStatusFilter,
  expandedDocumentIds,
  graphConnections,
  graphViewerState,
  ingesting,
  isDocumentFiltersVisible,
  locale,
  paginatedDocuments,
  paginationEnd,
  paginationStart,
  selectedGraphConnection,
  sortedDocumentsLength,
  statusFilterOptions,
  totalDocumentPages,
  ui,
  onClearFilters,
  onDeleteDocument,
  onDocumentDomainFilterChange,
  onDocumentPageChange,
  onDocumentPageSizeChange,
  onDocumentSearchChange,
  onDocumentSort,
  onDocumentStatusFilterChange,
  onDownloadSource,
  onEditDocument,
  onLoadDiagnostics,
  onLoadDocumentChunks,
  onLoadDocumentProvisions,
  onLoadProvisionRelations,
  onLoadDocumentGraph,
  onMarkDocumentReviewed,
  onSelectGraphConnection,
  onToggleDocumentExpanded,
  onReingestAll,
}: {
  actionsColumnLabel: string;
  adminData: AdminOperations;
  corpusQualityReport: CorpusQualityReport | null;
  currentDocumentPage: number;
  diagnosing: boolean;
  diagnostics: ExtractionDiagnostic | null;
  documentDomainFilter: string;
  documentFormatDateTime: (value: string) => string;
  documentPageSize: number;
  documentSearch: string;
  documentSortDirection: "asc" | "desc";
  documentSortKey: DocumentSortKey;
  documentStatusFilter: string;
  expandedDocumentIds: number[];
  graphConnections: GraphConnection[];
  graphViewerState: GraphViewerState | null;
  ingesting: boolean;
  isDocumentFiltersVisible: boolean;
  locale: Locale;
  paginatedDocuments: DocumentItem[];
  paginationEnd: number;
  paginationStart: number;
  selectedGraphConnection: GraphConnection | null;
  sortedDocumentsLength: number;
  statusFilterOptions: { value: string; label: string }[];
  totalDocumentPages: number;
  ui: UiText;
  onClearFilters: () => void;
  onDeleteDocument: (documentId: number) => void;
  onDocumentDomainFilterChange: (value: string) => void;
  onDocumentPageChange: (updater: (current: number) => number) => void;
  onDocumentPageSizeChange: (value: number) => void;
  onDocumentSearchChange: (value: string) => void;
  onDocumentSort: (key: DocumentSortKey) => void;
  onDocumentStatusFilterChange: (value: string) => void;
  onDownloadSource: (documentId: number) => void;
  onEditDocument: (document: DocumentItem) => void;
  onLoadDiagnostics: (documentId: number) => void;
  onLoadDocumentChunks: (document: DocumentItem) => void;
  onLoadDocumentProvisions: (document: DocumentItem) => void;
  onLoadProvisionRelations: (document: DocumentItem) => void;
  onLoadDocumentGraph: (document: DocumentItem) => void;
  onMarkDocumentReviewed: (document: DocumentItem) => void;
  onSelectGraphConnection: (key: string) => void;
  onToggleDocumentExpanded: (documentId: number) => void;
  onReingestAll: () => void;
}) {
  function renderSortButton(label: string, key: DocumentSortKey) {
    const isActive = documentSortKey === key;
    const directionMark = !isActive ? "" : documentSortDirection === "asc" ? " ^" : " v";
    return (
      <button
        className={`admin-sort-button ${isActive ? "active" : ""}`}
        onClick={() => onDocumentSort(key)}
        title={isActive && documentSortDirection === "asc" ? ui.adminSortDescendingLabel : ui.adminSortAscendingLabel}
        type="button"
      >
        <span>{label}{directionMark}</span>
      </button>
    );
  }

  const qualityItemsByDocumentId = new Map((corpusQualityReport?.items ?? []).map((item) => [item.document_id, item]));
  const reviewQueue = (corpusQualityReport?.items ?? [])
    .filter((item) => item.metadata_review_status !== "reviewed" || item.risk_level === "high" || item.issue_codes.length > 0)
    .slice(0, 8);

  return (
    <div className="admin-table-section">
      {corpusQualityReport ? (
        <CorpusQualityReviewPanel
          documents={adminData.documents}
          items={reviewQueue}
          locale={locale}
          report={corpusQualityReport}
          onEditDocument={onEditDocument}
          onMarkDocumentReviewed={onMarkDocumentReviewed}
          onToggleDocumentExpanded={onToggleDocumentExpanded}
        />
      ) : null}
      <div className="admin-table-toolbar admin-document-toolbar">
        <div className={`admin-table-filters admin-document-filters ${isDocumentFiltersVisible ? "open" : "mobile-hidden"}`}>
          <input className="admin-filter-input" onChange={(event) => onDocumentSearchChange(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={documentSearch} />
          <select className="admin-filter-select" onChange={(event) => onDocumentStatusFilterChange(event.target.value)} value={documentStatusFilter}>
            {statusFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>{`${ui.documentActivationColumnLabel}: ${option.label}`}</option>
            ))}
          </select>
          <select className="admin-filter-select" onChange={(event) => onDocumentDomainFilterChange(event.target.value)} value={documentDomainFilter}>
            <option value="all">{`${ui.documentLegalDomainLabel}: ${ui.adminFilterAllLabel}`}</option>
            {adminData.categories.map((category) => (
              <option key={category.id} value={category.slug}>{`${ui.documentLegalDomainLabel}: ${category.name}`}</option>
            ))}
          </select>
        </div>
        <div className="admin-table-toolbar-actions">
          <button className="secondary-button" disabled={ingesting} onClick={onReingestAll} type="button">
            {ingesting ? ui.reingestAllLoading : ui.reingestAllButton}
          </button>
          <button className="ghost-button admin-filter-clear-button" onClick={onClearFilters} type="button">{ui.adminClearFiltersButton}</button>
        </div>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table admin-documents-table">
          <thead>
            <tr>
              <th>{renderSortButton(ui.documentTitleLabel, "title")}</th>
              <th>{renderSortButton(ui.documentLegalStatusLabel, "legal_status")}</th>
              <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
            </tr>
          </thead>
          <tbody>
            {paginatedDocuments.length === 0 ? (
              <tr>
                <td colSpan={3}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td>
              </tr>
            ) : paginatedDocuments.flatMap((document) => {
              const expanded = expandedDocumentIds.includes(document.id);
              const legalDomainLabel = adminData.categories.find((category) => category.slug === document.legal_domain)?.name ?? document.legal_domain;
              const stableTitle = getStableDocumentTitle(document, locale, adminData);
              const qualityItem = qualityItemsByDocumentId.get(document.id);
              const metaItems = [
                `${ui.documentIdLabel}: ${document.id}`,
                document.document_code?.trim() || "--",
                getDocumentTypeName(locale, document.document_type, adminData.document_types),
                document.issuing_authority?.trim() || "--",
                document.signed_date?.trim() || null,
              ].filter((item): item is string => Boolean(item));

              return [
                <tr key={`row-${document.id}`}>
                  <td className="admin-document-primary-cell">
                    <div className="admin-table-title admin-document-table-title" title={document.title}>
                      {stableTitle}
                    </div>
                    {document.title !== stableTitle ? (
                      <div className="admin-table-subtext admin-document-title-subtext" title={document.title}>
                        {locale === "vi" ? "Tieu de OCR/parse" : "OCR/parsed title"}: {document.title}
                      </div>
                    ) : null}
                    <div className="admin-table-subtext admin-document-meta-line">{metaItems.join(" | ")}</div>
                    <div className="admin-document-chip-row">
                      <span className={`document-chip ${getMetadataReviewTone(document.metadata_review_status)}`}>
                        {getMetadataReviewLabel(locale, document.metadata_review_status, ui)}
                      </span>
                      {document.ocr_quality_score !== null ? (
                        <span className="document-chip relation-status-chip">
                          {getQualityPrefix(locale, document.ocr_quality_label)}: {document.ocr_quality_score}%
                        </span>
                      ) : null}
                      <span className="document-chip relation-status-chip">
                        {ui.documentRelationCountLabel}: {document.relation_count}
                      </span>
                      {qualityItem ? (
                        <span className={`document-chip corpus-risk-chip ${getRiskTone(qualityItem.risk_level)}`}>
                          {getRiskLabel(locale, qualityItem.risk_level)}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td>
                    <span className={`document-chip admin-legal-status-chip ${getLegalStatusTone(document.legal_status)}`}>
                      {getLegalStatusLabel(locale, document.legal_status)}
                    </span>
                  </td>
                  <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                    <div className="admin-table-actions admin-document-table-actions">
                      <button className="admin-icon-button" onClick={() => onToggleDocumentExpanded(document.id)} title={expanded ? ui.readLessButton : ui.readMoreButton} type="button"><ExpandIcon expanded={expanded} /></button>
                      <button className="admin-icon-button" onClick={() => onDownloadSource(document.id)} title={ui.downloadSourceButton} type="button"><DownloadIcon /></button>
                      <button className="admin-icon-button" onClick={() => onEditDocument(document)} title={ui.editDocumentAction} type="button"><EditIcon /></button>
                      <button className="admin-icon-button danger" onClick={() => onDeleteDocument(document.id)} title={ui.deleteDocumentAction} type="button"><DeleteIcon /></button>
                      <button className="admin-icon-button" onClick={() => onLoadDocumentChunks(document)} title={ui.viewChunksAction} type="button"><ChunkIcon /></button>
                      <button className="admin-icon-button" onClick={() => onLoadDocumentProvisions(document)} title={ui.viewProvisionsAction} type="button"><StructureIcon /></button>
                      <button className="admin-icon-button" onClick={() => onLoadProvisionRelations(document)} title={ui.viewProvisionRelationsAction} type="button"><RelationIcon /></button>
                    </div>
                  </td>
                </tr>,
                ...(expanded ? [
                  <tr className="admin-document-detail-row" key={`detail-${document.id}`}>
                    <td colSpan={3}>
                      <DocumentDetailPanel
                        adminData={adminData}
                        diagnosing={diagnosing}
                        diagnostics={diagnostics}
                        document={document}
                        formatDateTime={documentFormatDateTime}
                        graphConnections={graphConnections}
                        graphViewerState={graphViewerState}
                        legalDomainLabel={legalDomainLabel}
                        locale={locale}
                        selectedGraphConnection={selectedGraphConnection}
                        ui={ui}
                        qualityItem={qualityItem ?? null}
                        onLoadDiagnostics={onLoadDiagnostics}
                        onLoadDocumentGraph={onLoadDocumentGraph}
                        onMarkDocumentReviewed={onMarkDocumentReviewed}
                        onSelectGraphConnection={onSelectGraphConnection}
                      />
                    </td>
                  </tr>,
                ] : []),
              ];
            })}
          </tbody>
        </table>
      </div>
      <div className="admin-pagination-bar">
        <div className="admin-pagination-summary">{ui.adminPaginationSummary(paginationStart, paginationEnd, sortedDocumentsLength)}</div>
        <div className="admin-pagination-controls">
          <label className="admin-pagination-page-size">
            <span>{ui.adminRowsPerPageLabel}</span>
            <select className="admin-filter-select" onChange={(event) => onDocumentPageSizeChange(Number(event.target.value))} value={documentPageSize}>
              {[10, 20, 50].map((size) => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
          </label>
          <button className="ghost-button admin-pagination-button" disabled={currentDocumentPage <= 1} onClick={() => onDocumentPageChange((current) => Math.max(1, current - 1))} type="button">{ui.adminPaginationPreviousLabel}</button>
          <span className="admin-pagination-page-indicator">{currentDocumentPage}/{totalDocumentPages}</span>
          <button className="ghost-button admin-pagination-button" disabled={currentDocumentPage >= totalDocumentPages} onClick={() => onDocumentPageChange((current) => Math.min(totalDocumentPages, current + 1))} type="button">{ui.adminPaginationNextLabel}</button>
        </div>
      </div>
    </div>
  );
}

function CorpusQualityReviewPanel({
  documents,
  items,
  locale,
  report,
  onEditDocument,
  onMarkDocumentReviewed,
  onToggleDocumentExpanded,
}: {
  documents: DocumentItem[];
  items: CorpusQualityDocumentItem[];
  locale: Locale;
  report: CorpusQualityReport;
  onEditDocument: (document: DocumentItem) => void;
  onMarkDocumentReviewed: (document: DocumentItem) => void;
  onToggleDocumentExpanded: (documentId: number) => void;
}) {
  const summary = report.summary;
  const documentsById = new Map(documents.map((document) => [document.id, document]));
  return (
    <section className="corpus-quality-panel">
      <div className="corpus-quality-summary">
        <div>
          <p className="section-label">{locale === "vi" ? "Hàng đợi review dữ liệu" : "Data review queue"}</p>
          <h3>{locale === "vi" ? "AI chỉ là pre-label, chưa phải ground truth" : "AI output is pre-label, not ground truth"}</h3>
        </div>
        <div className="corpus-quality-metrics">
          <span><strong>{summary.pending_review_documents}</strong>{locale === "vi" ? " chờ review" : " pending"}</span>
          <span><strong>{summary.high_risk_documents}</strong>{locale === "vi" ? " rủi ro cao" : " high risk"}</span>
          <span><strong>{summary.relations_missing_evidence}</strong>{locale === "vi" ? " relation thiếu chứng cứ" : " relation evidence gaps"}</span>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="admin-document-detail-summary">{locale === "vi" ? "Không có tài liệu nào đang bị cảnh báo trong report hiện tại." : "No documents are flagged by the current report."}</p>
      ) : (
        <div className="corpus-quality-list">
          {items.map((item) => {
            const document = documentsById.get(item.document_id);
            return (
              <article className="corpus-quality-item" key={item.document_id}>
                <div className="corpus-quality-item-main">
                  <div className="corpus-quality-item-head">
                    <span className={`document-chip corpus-risk-chip ${getRiskTone(item.risk_level)}`}>{getRiskLabel(locale, item.risk_level)}</span>
                    <strong>{item.document_code || item.file_name}</strong>
                  </div>
                  <p>{item.title}</p>
                  <div className="corpus-quality-issue-row">
                    {item.issue_codes.slice(0, 4).map((issueCode) => (
                      <span className="document-chip corpus-issue-chip" key={issueCode}>{getQualityIssueLabel(locale, issueCode)}</span>
                    ))}
                    {item.issue_codes.length > 4 ? <span className="document-chip corpus-issue-chip">+{item.issue_codes.length - 4}</span> : null}
                  </div>
                  <div className="admin-document-detail-grid">
                    <span>Chunks: {item.chunk_count}</span>
                    <span>Provisions: {item.provision_count}</span>
                    <span>Relations: {item.document_relation_count}/{item.provision_relation_count}</span>
                    <span>{locale === "vi" ? "Legal status" : "Legal status"}: {item.legal_status ?? "--"}</span>
                    <span>Retrieval: {item.retrieval_visibility}</span>
                  </div>
                </div>
                <div className="corpus-quality-actions">
                  <button className="admin-inline-button" onClick={() => onToggleDocumentExpanded(item.document_id)} type="button">
                    {locale === "vi" ? "Mở chi tiết" : "Open details"}
                  </button>
                  {document ? (
                    <>
                      <button className="admin-inline-button" onClick={() => onEditDocument(document)} type="button">
                        {locale === "vi" ? "Sửa metadata" : "Edit metadata"}
                      </button>
                      <button className="admin-inline-button" disabled={document.metadata_review_status === "reviewed"} onClick={() => onMarkDocumentReviewed(document)} type="button">
                        {document.metadata_review_status === "reviewed" ? (locale === "vi" ? "Đã review" : "Reviewed") : (locale === "vi" ? "Đánh dấu review" : "Mark reviewed")}
                      </button>
                    </>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function DocumentDetailPanel({
  adminData,
  diagnosing,
  diagnostics,
  document,
  formatDateTime,
  graphConnections,
  graphViewerState,
  legalDomainLabel,
  locale,
  selectedGraphConnection,
  ui,
  qualityItem,
  onLoadDiagnostics,
  onLoadDocumentGraph,
  onMarkDocumentReviewed,
  onSelectGraphConnection,
}: {
  adminData: AdminOperations;
  diagnosing: boolean;
  diagnostics: ExtractionDiagnostic | null;
  document: DocumentItem;
  formatDateTime: (value: string) => string;
  graphConnections: GraphConnection[];
  graphViewerState: GraphViewerState | null;
  legalDomainLabel: string;
  locale: Locale;
  selectedGraphConnection: GraphConnection | null;
  ui: UiText;
  qualityItem: CorpusQualityDocumentItem | null;
  onLoadDiagnostics: (documentId: number) => void;
  onLoadDocumentGraph: (document: DocumentItem) => void;
  onMarkDocumentReviewed: (document: DocumentItem) => void;
  onSelectGraphConnection: (key: string) => void;
}) {
  return (
    <div className="admin-document-detail-panel">
      <strong>{ui.documentDetailsSummaryLabel}</strong>
      <div className="admin-document-detail-sections">
        <section className="admin-document-detail-section">
          <h4>{ui.documentLegalInfoSectionLabel}</h4>
          <div className="admin-document-detail-grid">
            {document.document_code ? <span>{ui.documentCodeLabel}: {document.document_code}</span> : null}
            <span>{ui.documentTypeLabel}: {getDocumentTypeLabel(locale, document.document_type, adminData.document_types)}</span>
            <span>{ui.documentAuthorityLabel}: {document.issuing_authority ?? "--"}</span>
            <span>{ui.documentLegalDomainLabel}: {legalDomainLabel}</span>
            {document.signed_date ? <span>{ui.documentSignedDateLabel}: {document.signed_date}</span> : null}
            <span>{ui.documentLegalStatusLabel}: {getLegalStatusLabel(locale, document.legal_status)}</span>
            <span>{ui.documentMetadataReviewStatusLabel}: {getMetadataReviewLabel(locale, document.metadata_review_status, ui)}</span>
            {document.ocr_quality_score !== null ? <span>{locale === "vi" ? "Chat luong text" : "Text quality"}: {document.ocr_quality_score}% ({getQualityLabel(locale, document.ocr_quality_label)})</span> : null}
            <span>{ui.documentRelationStatusLabel}: {getRelationSyncLabel(locale, document.relation_sync_status, ui)}</span>
            <span>{ui.documentRelationCountLabel}: {document.relation_count}</span>
            {document.effective_date ? <span>{ui.documentEffectiveDateLabel}: {document.effective_date}</span> : null}
            {document.expiry_date ? <span>{ui.documentExpiryDateLabel}: {document.expiry_date}</span> : null}
            <span>{ui.documentActivationDescriptionLabel}: {document.is_active ? ui.documentActivatedLabel : ui.documentDeactivatedLabel}</span>
            {document.metadata_last_reviewed_at ? <span>{ui.documentReviewedAtLabel}: {formatDateTime(document.metadata_last_reviewed_at)}</span> : null}
          </div>
        </section>
        {qualityItem ? (
          <section className="admin-document-detail-section">
            <h4>{locale === "vi" ? "Kiểm soát chất lượng corpus" : "Corpus quality control"}</h4>
            <div className="admin-document-chip-row">
              <span className={`document-chip corpus-risk-chip ${getRiskTone(qualityItem.risk_level)}`}>
                {getRiskLabel(locale, qualityItem.risk_level)}
              </span>
              {qualityItem.issue_codes.map((issueCode) => (
                <span className="document-chip corpus-issue-chip" key={issueCode}>{getQualityIssueLabel(locale, issueCode)}</span>
              ))}
            </div>
            <div className="admin-document-detail-grid">
              <span>Chunks: {qualityItem.chunk_count}</span>
              <span>Indexed: {qualityItem.indexed_chunk_count}</span>
              <span>Provisions: {qualityItem.provision_count}</span>
              <span>Document relations: {qualityItem.document_relation_count}</span>
              <span>Provision relations: {qualityItem.provision_relation_count}</span>
              <span>Missing evidence: {qualityItem.missing_relation_evidence_count}</span>
              <span>Ingestion: {qualityItem.ingestion_quality_status}</span>
              <span>Retrieval: {qualityItem.retrieval_visibility}</span>
            </div>
            {qualityItem.recommendations.length > 0 ? (
              <div className="corpus-quality-recommendations">
                {qualityItem.recommendations.map((recommendation) => (
                  <p className="admin-document-detail-summary" key={recommendation}>{recommendation}</p>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}
        <section className="admin-document-detail-section">
          <h4>{ui.documentSummarySectionLabel}</h4>
          {document.summary ? <p className="admin-document-detail-summary">{document.summary}</p> : <p className="admin-document-detail-summary">{ui.noSummary}</p>}
        </section>
        <section className="admin-document-detail-section">
          <h4>{ui.documentSupplementarySectionLabel}</h4>
          <div className="admin-document-detail-grid">
            <span>{ui.documentFileNameLabel}: {document.file_name}</span>
            {document.source_reference ? <span>{ui.documentReferenceLabel}: {document.source_reference}</span> : null}
            {document.metadata_review_notes ? <span>{ui.documentReviewNotesLabel}: {document.metadata_review_notes}</span> : null}
          </div>
          <div className="admin-document-detail-actions">
            <button className="admin-inline-button" disabled={diagnosing} onClick={() => onLoadDiagnostics(document.id)} type="button">{diagnosing && diagnostics?.document_id === document.id ? ui.diagnosticsLoading : ui.diagnosticsButton}</button>
            <button className="admin-inline-button" disabled={graphViewerState?.loading && graphViewerState.documentId === document.id} onClick={() => onLoadDocumentGraph(document)} type="button">{graphViewerState?.loading && graphViewerState.documentId === document.id ? (locale === "vi" ? "Dang tai do thi" : "Loading graph") : (locale === "vi" ? "Xem do thi" : "View graph")}</button>
            <button className="admin-inline-button" disabled={document.metadata_review_status === "reviewed"} onClick={() => onMarkDocumentReviewed(document)} type="button">{document.metadata_review_status === "reviewed" ? ui.documentMetadataReviewedLabel : ui.documentReviewButton}</button>
          </div>
          {diagnostics?.document_id === document.id ? (
            <div className="admin-document-diagnostics-panel">
              <strong>{ui.diagnosticsSectionTitle}</strong>
              <div className="admin-document-detail-grid">
                <span>{diagnostics.is_extractable ? ui.extractableTitle : ui.notExtractableTitle}</span>
                <span>{ui.pagesLabel}: {diagnostics.total_pages ?? "--"}</span>
                <span>{ui.charsLabel}: {diagnostics.extracted_characters}</span>
                <span>{ui.ocrAvailableLabel}: {translateBooleanState(locale, diagnostics.ocr_available)}</span>
                <span>{ui.ocrRecommendedLabel}: {translateBooleanState(locale, diagnostics.ocr_recommended)}</span>
                <span>{ui.ocrEngineLabel}: {diagnostics.ocr_engine ?? "--"}</span>
                <span>{ui.ocrConfidenceLabel}: {diagnostics.ocr_average_confidence ?? "--"}</span>
                <span>{locale === "vi" ? "Chat luong trich xuat" : "Extraction quality"}: {diagnostics.ocr_quality_score ?? "--"} {getQualityLabel(locale, diagnostics.ocr_quality_label)}</span>
                <span>{ui.parserArticleCountLabel}: {diagnostics.parser_article_count}</span>
                <span>{ui.parserClauseCountLabel}: {diagnostics.parser_clause_count}</span>
                <span>{ui.parserPointCountLabel}: {diagnostics.parser_point_count}</span>
                <span>{ui.parserProvisionCountLabel}: {diagnostics.parser_provision_count}</span>
                <span>{ui.parserProvisionRelationCountLabel}: {diagnostics.provision_relation_count}</span>
                <span>{ui.structureQualityLabel}: {diagnostics.structure_quality_score ?? "--"} {diagnostics.structure_quality_label ?? ""}</span>
                <span>{ui.parserStatusLabel}: {diagnostics.parser_status}</span>
              </div>
              <p className="admin-document-detail-summary">{diagnostics.recommendation}</p>
              {diagnostics.parser_notes.length > 0 ? (
                <div className="admin-document-detail-grid">
                  <span>{ui.parserNotesLabel}: {diagnostics.parser_notes.join(" | ")}</span>
                </div>
              ) : null}
              {diagnostics.ocr_sample_pages.length > 0 ? (
                <div className="admin-document-detail-grid">
                  <span>{ui.ocrSamplePagesLabel}: {diagnostics.ocr_sample_pages.map((item) => `${item.page} (${item.extracted_characters})`).join(", ")}</span>
                </div>
              ) : null}
            </div>
          ) : null}
          {graphViewerState?.documentId === document.id ? (
            <DocumentGraphPanel
              adminData={adminData}
              graphConnections={graphConnections}
              graphViewerState={graphViewerState}
              locale={locale}
              selectedGraphConnection={selectedGraphConnection}
              onSelectGraphConnection={onSelectGraphConnection}
            />
          ) : null}
        </section>
      </div>
    </div>
  );
}

function DocumentGraphPanel({
  adminData,
  graphConnections,
  graphViewerState,
  locale,
  selectedGraphConnection,
  onSelectGraphConnection,
}: {
  adminData: AdminOperations;
  graphConnections: GraphConnection[];
  graphViewerState: GraphViewerState;
  locale: Locale;
  selectedGraphConnection: GraphConnection | null;
  onSelectGraphConnection: (key: string) => void;
}) {
  return (
    <div className="admin-document-diagnostics-panel">
      <strong>{locale === "vi" ? "Do thi van ban" : "Document graph"}</strong>
      {graphViewerState.loading ? <p className="admin-document-detail-summary">{locale === "vi" ? "Dang tai do thi..." : "Loading graph..."}</p> : null}
      {graphViewerState.error ? <p className="admin-document-detail-summary">{graphViewerState.error}</p> : null}
      {graphViewerState.graph ? (
        <>
          <div className="admin-document-detail-grid">
            <span>{locale === "vi" ? "Backend" : "Backend"}: {adminData.graph_backend_settings.backend === "neo4j" ? (locale === "vi" ? "Neo4j Aura" : "Neo4j Aura") : (locale === "vi" ? "Relational hien tai" : "Current relational")}</span>
            <span>{locale === "vi" ? "So node" : "Nodes"}: {graphViewerState.graph.nodes.length}</span>
            <span>{locale === "vi" ? "So canh" : "Edges"}: {graphViewerState.graph.edges.length}</span>
            <span>{locale === "vi" ? "Do sau" : "Depth"}: {graphViewerState.graph.depth}</span>
          </div>
          <div className="admin-graph-legend">
            {Object.entries(RELATION_TAXONOMY).map(([relationType]) => {
              const definition = getRelationDefinition(locale, relationType);
              return (
                <span
                  className={`admin-graph-legend-item ${definition.lineStyle === "dashed" ? "is-dashed" : ""}`}
                  key={relationType}
                  style={{ "--legend-color": definition.color } as CSSProperties}
                >
                  {definition.label}
                </span>
              );
            })}
          </div>
          {graphConnections.length > 0 ? (
            <div className="admin-graph-layout">
              <div className="admin-graph-canvas">
                {graphConnections.map((connection) => {
                  const primaryRelation = connection.relations[0];
                  const primaryDefinition = getRelationDefinition(locale, primaryRelation?.relation_type);
                  const relationCount = connection.relations.length;
                  return (
                    <button
                      className={`admin-graph-connection ${selectedGraphConnection?.key === connection.key ? "is-selected" : ""}`}
                      key={connection.key}
                      onClick={() => onSelectGraphConnection(connection.key)}
                      type="button"
                    >
                      <div className="admin-graph-node-stack">
                        <span className={`admin-graph-node ${connection.sourceNode?.is_root ? "is-root" : ""}`}>
                          <strong>{connection.sourceNode?.document_code || connection.sourceNode?.title || connection.sourceId}</strong>
                          <small>{getDocumentTypeName(locale, connection.sourceNode?.document_type, adminData.document_types)}</small>
                        </span>
                      </div>
                      <div className="admin-graph-edge-stack">
                        <span
                          className={`admin-graph-edge-line ${primaryDefinition.lineStyle === "dashed" ? "is-dashed" : ""} ${primaryDefinition.weight === "strong" ? "is-strong" : primaryDefinition.weight === "medium" ? "is-medium" : "is-light"}`}
                          style={{ "--edge-color": primaryDefinition.color } as CSSProperties}
                        />
                        <div className="admin-graph-edge-badges">
                          {connection.relations.slice(0, 3).map((relation) => {
                            const relationDefinition = getRelationDefinition(locale, relation.relation_type);
                            return (
                              <span
                                className="admin-graph-edge-badge"
                                key={relation.id}
                                style={{
                                  "--edge-badge-color": relationDefinition.color,
                                  "--edge-badge-border": relationDefinition.borderColor,
                                  "--edge-badge-bg": relationDefinition.background,
                                } as CSSProperties}
                              >
                                {relationDefinition.label}
                              </span>
                            );
                          })}
                          {relationCount > 3 ? <span className="admin-graph-edge-more">+{relationCount - 3}</span> : null}
                        </div>
                      </div>
                      <div className="admin-graph-node-stack">
                        <span className={`admin-graph-node ${connection.targetNode?.is_root ? "is-root" : ""}`}>
                          <strong>{connection.targetNode?.document_code || connection.targetNode?.title || connection.targetId}</strong>
                          <small>{getDocumentTypeName(locale, connection.targetNode?.document_type, adminData.document_types)}</small>
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
              <aside className="admin-graph-sidepanel">
                {selectedGraphConnection ? (
                  <>
                    <div className="admin-graph-sidepanel-header">
                      <strong>{locale === "vi" ? "Chi tiet quan he" : "Relationship details"}</strong>
                      <span>{selectedGraphConnection.relations.length} {locale === "vi" ? "moi quan he" : "relations"}</span>
                    </div>
                    <div className="admin-graph-sidepanel-docs">
                      <div className="admin-graph-sidepanel-doc">
                        <span className="admin-graph-sidepanel-doc-label">{locale === "vi" ? "Nguon" : "Source"}</span>
                        <strong>{selectedGraphConnection.sourceNode?.title || selectedGraphConnection.sourceNode?.label || selectedGraphConnection.sourceId}</strong>
                        <small>{selectedGraphConnection.sourceNode?.document_code || "--"} | {getDocumentTypeName(locale, selectedGraphConnection.sourceNode?.document_type, adminData.document_types)}</small>
                      </div>
                      <div className="admin-graph-sidepanel-doc">
                        <span className="admin-graph-sidepanel-doc-label">{locale === "vi" ? "Dich" : "Target"}</span>
                        <strong>{selectedGraphConnection.targetNode?.title || selectedGraphConnection.targetNode?.label || selectedGraphConnection.targetId}</strong>
                        <small>{selectedGraphConnection.targetNode?.document_code || "--"} | {getDocumentTypeName(locale, selectedGraphConnection.targetNode?.document_type, adminData.document_types)}</small>
                      </div>
                    </div>
                    <div className="admin-graph-relation-list">
                      {selectedGraphConnection.relations.map((relation) => {
                        const relationDefinition = getRelationDefinition(locale, relation.relation_type);
                        return (
                          <article className="admin-graph-relation-item" key={relation.id}>
                            <div className="admin-graph-relation-item-head">
                              <span
                                className="admin-graph-edge-badge"
                                style={{
                                  "--edge-badge-color": relationDefinition.color,
                                  "--edge-badge-border": relationDefinition.borderColor,
                                  "--edge-badge-bg": relationDefinition.background,
                                } as CSSProperties}
                              >
                                {relationDefinition.label}
                              </span>
                              <span className="admin-graph-confidence">
                                {locale === "vi" ? "Do tin cay" : "Confidence"}: {relation.confidence_score !== null ? `${Math.round(relation.confidence_score * 100)}%` : "--"}
                              </span>
                            </div>
                            <p className="admin-document-detail-summary">{relationDefinition.effect}</p>
                            {relation.legal_basis ? <EvidenceBlock label={locale === "vi" ? "Dau hieu o van ban nguon" : "Source-side evidence"} value={relation.legal_basis} /> : null}
                            {relation.target_anchor ? <EvidenceBlock label={locale === "vi" ? "Neo nhan dien o van ban dich" : "Target anchor"} value={relation.target_anchor} /> : null}
                            {relation.target_excerpt ? <EvidenceBlock label={locale === "vi" ? "Dau hieu o van ban dich" : "Target-side evidence"} value={relation.target_excerpt} /> : null}
                            {relation.provision_relation_count > 0 ? (
                              <EvidenceBlock
                                label={locale === "vi" ? "Quan he dieu khoan lien ket" : "Linked provision relations"}
                                value={`${relation.provision_relation_count} | ${relation.provision_relation_types.join(", ")}`}
                              />
                            ) : null}
                            {relation.provision_relation_samples.length > 0 ? (
                              <div className="admin-graph-legal-basis">
                                <span>{locale === "vi" ? "Mau quan he dieu khoan" : "Provision relation samples"}</span>
                                <div className="admin-graph-relation-list">
                                  {relation.provision_relation_samples.map((sample) => {
                                    const sampleMetadata = parseRelationMetadata(sample.metadata_json);
                                    return (
                                      <article className="admin-graph-relation-item" key={`sample-${sample.id}`}>
                                        <div className="admin-graph-relation-item-head">
                                          <span className="admin-graph-edge-badge">{sample.relation_label || sample.relation_type}</span>
                                          <span className="admin-graph-confidence">
                                            {locale === "vi" ? "Do tin cay" : "Confidence"}: {sample.confidence_score !== null ? `${Math.round(sample.confidence_score * 100)}%` : "--"}
                                          </span>
                                        </div>
                                        <EvidenceBlock
                                          label={locale === "vi" ? "Dieu khoan nguon" : "Source provision"}
                                          value={sampleMetadata.source_citation_label || String(sample.source_provision_id)}
                                        />
                                        {sample.source_excerpt ? <EvidenceBlock label={locale === "vi" ? "Noi dung nguon" : "Source excerpt"} value={sample.source_excerpt} /> : null}
                                        <EvidenceBlock
                                          label={locale === "vi" ? "Dieu khoan dich" : "Target provision"}
                                          value={sampleMetadata.target_citation_label || String(sample.target_provision_id)}
                                        />
                                        {sample.target_excerpt ? <EvidenceBlock label={locale === "vi" ? "Noi dung dich" : "Target excerpt"} value={sample.target_excerpt} /> : null}
                                      </article>
                                    );
                                  })}
                                </div>
                              </div>
                            ) : null}
                          </article>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <p className="admin-document-detail-summary">{locale === "vi" ? "Chon mot duong noi de xem chi tiet quan he." : "Select a connection to inspect relationship details."}</p>
                )}
              </aside>
            </div>
          ) : graphViewerState.graph.nodes.length > 0 ? (
            <div className="ticket-timeline">
              {graphViewerState.graph.nodes.map((node) => (
                <article className="timeline-item" key={node.id}>
                  <span className="timeline-label">{node.is_root ? (locale === "vi" ? "Root" : "Root") : (locale === "vi" ? "Node" : "Node")}</span>
                  <p>{node.label}</p>
                </article>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function EvidenceBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="admin-graph-legal-basis">
      <span>{label}</span>
      <p>{value}</p>
    </div>
  );
}

function parseRelationMetadata(metadataJson: string | null): { source_citation_label?: string; target_citation_label?: string } {
  if (!metadataJson) {
    return {};
  }
  try {
    return JSON.parse(metadataJson) as { source_citation_label?: string; target_citation_label?: string };
  } catch {
    return {};
  }
}
