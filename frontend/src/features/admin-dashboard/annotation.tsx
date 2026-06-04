import { useEffect, useMemo, useRef, useState } from "react";

import type { AdminOperations, AnnotationDocumentPayload, AnnotationEntityPayload, AnnotationGroundTruthSavePayload, AnnotationVendorExportPayload } from "../../types/lawchat";
import type { Locale } from "../../locales";

const ANNOTATION_LABEL_OPTIONS = [
  "ARTICLE",
  "CLAUSE",
  "POINT",
  "SUBJECT",
  "ACTION",
  "LEGAL_OBJECT",
  "CONDITION",
  "EXCEPTION",
  "CONSEQUENCE",
  "DOCUMENT_REFERENCE",
  "PROVISION_REFERENCE",
  "LEGAL_BASIS_REFERENCE",
  "AUTHORITY",
  "PROCEDURE",
  "RIGHT",
  "OBLIGATION",
  "PROHIBITION",
  "PERMISSION",
  "NEEDS_REVIEW",
  "UNCERTAIN_PARSE",
];

type AnnotationSelectionDraft = {
  text: string;
  start: number;
  end: number;
};

type AnnotationTextSegment = {
  key: string;
  text: string;
  entity: AnnotationEntityPayload | null;
};

type AnnotationDocumentOption = {
  id: number;
  title: string;
  file_name: string;
  document_code?: string | null;
  document_type?: string | null;
};

function compactDocumentOptionLabel(document: AnnotationDocumentOption): string {
  const stableIdentifier = document.document_code?.trim() || document.file_name?.trim() || document.title?.trim();
  const documentType = document.document_type?.trim();
  return `#${document.id} | ${stableIdentifier}${documentType ? ` | ${documentType}` : ""}`;
}

function buildAnnotationTextSegments(text: string, entities: AnnotationEntityPayload[]): AnnotationTextSegment[] {
  const anchoredEntities = entities
    .filter((entity) => Number.isFinite(entity.start) && Number.isFinite(entity.end) && entity.start !== null && entity.end !== null && entity.start < entity.end)
    .sort((left, right) => {
      const startDelta = (left.start ?? 0) - (right.start ?? 0);
      if (startDelta !== 0) {
        return startDelta;
      }
      const leftManual = left.id.startsWith("manual-") ? 0 : 1;
      const rightManual = right.id.startsWith("manual-") ? 0 : 1;
      if (leftManual !== rightManual) {
        return leftManual - rightManual;
      }
      return (right.end ?? 0) - (left.end ?? 0);
    });

  const segments: AnnotationTextSegment[] = [];
  let cursor = 0;
  anchoredEntities.forEach((entity) => {
    const start = Math.max(0, Math.min(text.length, entity.start ?? 0));
    const end = Math.max(0, Math.min(text.length, entity.end ?? 0));
    if (start < cursor || end <= start) {
      return;
    }
    if (start > cursor) {
      segments.push({ key: `plain-${cursor}-${start}`, text: text.slice(cursor, start), entity: null });
    }
    segments.push({ key: `entity-${entity.id}-${start}-${end}`, text: text.slice(start, end), entity });
    cursor = end;
  });

  if (cursor < text.length) {
    segments.push({ key: `plain-${cursor}-${text.length}`, text: text.slice(cursor), entity: null });
  }

  return segments.length > 0 ? segments : [{ key: "plain-empty", text, entity: null }];
}

export function AnnotationSection({
  adminData,
  annotationGroundTruthSave,
  annotationPreview,
  annotationPreviewDocumentId,
  annotationPreviewLoading,
  annotationSaveLoading,
  locale,
  onDownloadAnnotationGroundTruth,
  onLoadAnnotationPreview,
  onSaveAnnotationGroundTruth,
}: {
  adminData: AdminOperations;
  annotationGroundTruthSave: AnnotationGroundTruthSavePayload | null;
  annotationPreview: AnnotationVendorExportPayload | null;
  annotationPreviewDocumentId: number | null;
  annotationPreviewLoading: boolean;
  annotationSaveLoading: boolean;
  locale: Locale;
  onDownloadAnnotationGroundTruth: (fileName: string) => void;
  onLoadAnnotationPreview: (documentId: number) => void;
  onSaveAnnotationGroundTruth: (payload: AnnotationDocumentPayload) => void;
}) {
  const textContainerRef = useRef<HTMLDivElement | null>(null);
  const [manualEntities, setManualEntities] = useState<AnnotationEntityPayload[]>([]);
  const [selectionDraft, setSelectionDraft] = useState<AnnotationSelectionDraft | null>(null);
  const [manualLabel, setManualLabel] = useState("SUBJECT");

  useEffect(() => {
    setManualEntities([]);
    setSelectionDraft(null);
  }, [annotationPreview?.document_id]);

  const sourceText = annotationPreview?.internal_payload.source_text ?? "";
  const selectedDocument = adminData.documents.find((document) => document.id === annotationPreviewDocumentId) ?? null;
  const visibleEntities = useMemo(
    () => [...manualEntities, ...(annotationPreview?.internal_payload.entities ?? [])],
    [annotationPreview?.internal_payload.entities, manualEntities],
  );
  const textSegments = useMemo(() => buildAnnotationTextSegments(sourceText, visibleEntities), [sourceText, visibleEntities]);
  const reviewedPayload = useMemo<AnnotationDocumentPayload | null>(() => {
    if (!annotationPreview) {
      return null;
    }
    return {
      ...annotationPreview.internal_payload,
      vendor: "internal_review",
      review_status: "reviewed",
      entities: visibleEntities,
      relations: annotationPreview.internal_payload.relations,
    };
  }, [annotationPreview, visibleEntities]);

  function captureSelection() {
    const container = textContainerRef.current;
    const selection = window.getSelection();
    if (!container || !selection || selection.rangeCount === 0) {
      return;
    }
    const selectedText = selection.toString();
    if (!selectedText.trim()) {
      return;
    }
    const range = selection.getRangeAt(0);
    if (!container.contains(range.commonAncestorContainer)) {
      return;
    }
    const beforeRange = range.cloneRange();
    beforeRange.selectNodeContents(container);
    beforeRange.setEnd(range.startContainer, range.startOffset);
    const start = beforeRange.toString().length;
    const end = start + selectedText.length;
    if (start < 0 || end <= start || end > sourceText.length) {
      return;
    }
    setSelectionDraft({ start, end, text: sourceText.slice(start, end) });
  }

  function addManualEntity() {
    if (!selectionDraft) {
      return;
    }
    const trimmedText = selectionDraft.text.trim();
    if (!trimmedText) {
      return;
    }
    const leadingWhitespace = selectionDraft.text.length - selectionDraft.text.trimStart().length;
    const trailingWhitespace = selectionDraft.text.length - selectionDraft.text.trimEnd().length;
    const start = selectionDraft.start + leadingWhitespace;
    const end = selectionDraft.end - trailingWhitespace;
    setManualEntities((current) => [
      ...current,
      {
        id: `manual-${Date.now()}-${current.length + 1}`,
        label: manualLabel,
        text: sourceText.slice(start, end),
        start,
        end,
        normalized_value: null,
        attributes: {
          prediction_provenance: "manual",
          review_status: "draft",
        },
      },
    ]);
    setSelectionDraft(null);
    window.getSelection()?.removeAllRanges();
  }

  function removeManualEntity(entityId: string) {
    setManualEntities((current) => current.filter((entity) => entity.id !== entityId));
  }

  return (
    <div className="admin-overview-shell annotation-workspace-shell">
      <div className="admin-hero-card admin-hero-card-modern">
        <div className="admin-hero-copy-block">
          <p className="section-label">{locale === "vi" ? "Ground-truth workflow" : "Ground-truth workflow"}</p>
          <h3>{locale === "vi" ? "Pre-label, rà soát và gán nhãn lại" : "Pre-label, review, and relabel"}</h3>
          <p>
            {locale === "vi"
              ? "Hệ thống sinh nhãn từ cấu trúc, relation parser và rule semantic. Người dùng có thể quét text để thêm nhãn nháp trước khi đưa sang review chính thức."
              : "The system generates labels from structure, relation parsing, and semantic rules. Users can select text and add draft labels before formal review."}
          </p>
        </div>
        <div className="admin-hero-badges admin-hero-metrics">
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Pre-label" : "Pre-label"}</span>
            <strong>{annotationPreview?.import_summary.entity_count ?? 0}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Relation" : "Relations"}</span>
            <strong>{annotationPreview?.import_summary.relation_count ?? 0}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Nhãn nháp" : "Draft labels"}</span>
            <strong>{manualEntities.length}</strong>
          </div>
        </div>
      </div>

      <div className="admin-list-shell">
        <article className="admin-list-row">
          <div className="admin-row-main">
            <strong>{locale === "vi" ? "Xem trước pre-label Label Studio" : "Label Studio pre-label preview"}</strong>
            <p>
              {locale === "vi"
                ? "LawChat sinh nhãn trước từ metadata, cấu trúc điều khoản và relation parser. Legal team sẽ review ở bước sau."
                : "LawChat generates draft labels from metadata, provision structure, and relation parsing. The legal team reviews them in the next step."}
            </p>
          </div>
        </article>
        <div className="admin-list-row">
          <div className="admin-row-main">
            <div className="admin-file-upload-row">
              <label className="admin-form-field">
                <span>{locale === "vi" ? "Tài liệu" : "Document"}</span>
                <select
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    if (Number.isFinite(value) && value > 0) {
                      onLoadAnnotationPreview(value);
                    }
                  }}
                  value={annotationPreviewDocumentId ?? ""}
                >
                  <option value="">{locale === "vi" ? "Chọn tài liệu để xem trước" : "Select a document to preview"}</option>
                  {adminData.documents.map((document) => (
                    <option key={`annotation-preview-${document.id}`} title={document.title} value={document.id}>
                      {compactDocumentOptionLabel(document)}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="secondary-button"
                disabled={annotationPreviewLoading || !annotationPreviewDocumentId}
                onClick={() => annotationPreviewDocumentId ? onLoadAnnotationPreview(annotationPreviewDocumentId) : undefined}
                type="button"
              >
                {annotationPreviewLoading
                  ? (locale === "vi" ? "Đang tạo preview" : "Generating preview")
                  : (locale === "vi" ? "Tải lại preview" : "Reload preview")}
              </button>
            </div>
            {selectedDocument ? (
              <div className="annotation-selected-document-card">
                <span>{locale === "vi" ? "Tài liệu đang xem" : "Selected document"}</span>
                <strong title={selectedDocument.title}>{selectedDocument.document_code?.trim() || selectedDocument.file_name || selectedDocument.title}</strong>
                <small title={selectedDocument.title}>
                  {locale === "vi" ? "Tiêu đề OCR/parse" : "OCR/parsed title"}: {selectedDocument.title}
                </small>
              </div>
            ) : null}
            {annotationPreview ? (
              <div className="annotation-workspace-grid">
                <section className="admin-document-detail-section">
                  <h4>{locale === "vi" ? "Tóm tắt import nội bộ" : "Internal import summary"}</h4>
                  <div className="admin-document-detail-grid">
                    <span>{locale === "vi" ? "Entity" : "Entities"}: {annotationPreview.import_summary.entity_count}</span>
                    <span>{locale === "vi" ? "Relation" : "Relations"}: {annotationPreview.import_summary.relation_count}</span>
                    <span>{locale === "vi" ? "Provision" : "Provisions"}: {annotationPreview.import_summary.provision_count}</span>
                    <span>{locale === "vi" ? "Provision relations" : "Provision relations"}: {annotationPreview.import_summary.provision_relation_count}</span>
                    <span>{locale === "vi" ? "Semantic entities" : "Semantic entities"}: {annotationPreview.import_summary.semantic_entity_count}</span>
                    <span>{locale === "vi" ? "Vendor" : "Vendor"}: {annotationPreview.import_summary.vendor}</span>
                  </div>
                  {annotationPreview.import_summary.warnings.length > 0 ? (
                    <ul className="admin-document-detail-list">
                      {annotationPreview.import_summary.warnings.map((warning, index) => (
                        <li key={`annotation-warning-${index}`}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="admin-card-actions">
                    <button
                      className="primary-button"
                      disabled={!reviewedPayload || annotationSaveLoading}
                      onClick={() => reviewedPayload ? onSaveAnnotationGroundTruth(reviewedPayload) : undefined}
                      type="button"
                    >
                      {annotationSaveLoading
                        ? (locale === "vi" ? "Đang lưu ground-truth" : "Saving ground-truth")
                        : (locale === "vi" ? "Lưu ground-truth" : "Save ground-truth")}
                    </button>
                    {annotationGroundTruthSave ? (
                      <button
                        className="secondary-button"
                        onClick={() => onDownloadAnnotationGroundTruth(annotationGroundTruthSave.file_name)}
                        type="button"
                      >
                        {locale === "vi" ? "Tải JSON đã lưu" : "Download saved JSON"}
                      </button>
                    ) : null}
                  </div>
                  {annotationGroundTruthSave ? (
                    <div className="diagnostic-box ok">
                      <strong>{locale === "vi" ? "Đã lưu bundle review" : "Review bundle saved"}</strong>
                      <p>
                        {annotationGroundTruthSave.file_name} · {locale === "vi" ? "Entity" : "Entities"}: {annotationGroundTruthSave.import_summary.entity_count} · {locale === "vi" ? "Norm statements" : "Norm statements"}: {annotationGroundTruthSave.bundle_counts.norm_statements ?? 0}
                      </p>
                    </div>
                  ) : null}
                </section>
                <section className="admin-document-detail-section annotation-manual-label-panel">
                  <h4>{locale === "vi" ? "Gán nhãn từ vùng chọn" : "Label selected text"}</h4>
                  <div className="admin-file-upload-row">
                    <label className="admin-form-field">
                      <span>{locale === "vi" ? "Loại nhãn" : "Label"}</span>
                      <select onChange={(event) => setManualLabel(event.target.value)} value={manualLabel}>
                        {ANNOTATION_LABEL_OPTIONS.map((label) => (
                          <option key={`annotation-label-${label}`} value={label}>{label}</option>
                        ))}
                      </select>
                    </label>
                    <button className="primary-button" disabled={!selectionDraft} onClick={addManualEntity} type="button">
                      {locale === "vi" ? "Gán nhãn vùng chọn" : "Add label"}
                    </button>
                  </div>
                  <p className="admin-row-time">
                    {selectionDraft
                      ? `${locale === "vi" ? "Đang chọn" : "Selected"}: ${selectionDraft.text.slice(0, 160)}${selectionDraft.text.length > 160 ? "..." : ""}`
                      : (locale === "vi" ? "Quét một đoạn trong văn bản bên dưới để tạo nhãn nháp." : "Select text in the document viewer below to create a draft label.")}
                  </p>
                  {manualEntities.length > 0 ? (
                    <div className="annotation-draft-list">
                      {manualEntities.map((entity) => (
                        <article className="admin-graph-relation-item" key={entity.id}>
                          <div className="admin-graph-relation-item-head">
                            <span className={`annotation-label-pill annotation-label-${entity.label.toLowerCase().replace(/_/g, "-")}`}>{entity.label}</span>
                            <button className="ghost-button" onClick={() => removeManualEntity(entity.id)} type="button">
                              {locale === "vi" ? "Bỏ" : "Remove"}
                            </button>
                          </div>
                          <p className="annotation-entity-text">{entity.text}</p>
                        </article>
                      ))}
                    </div>
                  ) : null}
                </section>
                <section className="admin-document-detail-section annotation-document-viewer-section">
                  <h4>{locale === "vi" ? "Toàn văn và highlight nhãn" : "Full text with label highlights"}</h4>
                  <div className="annotation-label-legend">
                    {ANNOTATION_LABEL_OPTIONS.slice(0, 9).map((label) => (
                      <span className={`annotation-label-pill annotation-label-${label.toLowerCase().replace(/_/g, "-")}`} key={`legend-${label}`}>{label}</span>
                    ))}
                  </div>
                  <div className="annotation-document-viewer" onMouseUp={captureSelection} ref={textContainerRef}>
                    {sourceText ? textSegments.map((segment) => (
                      segment.entity ? (
                        <mark
                          className={`annotation-highlight annotation-label-${segment.entity.label.toLowerCase().replace(/_/g, "-")}`}
                          data-label={segment.entity.label}
                          key={segment.key}
                          title={`${segment.entity.label} | ${String(segment.entity.attributes.prediction_provenance ?? "--")}`}
                        >
                          {segment.text}
                        </mark>
                      ) : (
                        <span key={segment.key}>{segment.text}</span>
                      )
                    )) : <span>{locale === "vi" ? "Không có text nguồn." : "No source text available."}</span>}
                  </div>
                </section>
                <section className="admin-document-detail-section">
                  <h4>{locale === "vi" ? "Nhãn dự đoán" : "Predicted labels"}</h4>
                  <div className="admin-graph-relation-list">
                    {visibleEntities.slice(0, 40).map((entity) => (
                        <article className="admin-graph-relation-item" key={`annotation-entity-${entity.id}`}>
                          <div className="admin-graph-relation-item-head">
                            <span className={`annotation-label-pill annotation-label-${entity.label.toLowerCase().replace(/_/g, "-")}`}>{entity.label}</span>
                            <span className="admin-graph-confidence">
                              {typeof entity.attributes.prediction_provenance === "string"
                                ? String(entity.attributes.prediction_provenance)
                                : "--"}
                            </span>
                          </div>
                          <p className="admin-document-detail-summary">{entity.text}</p>
                        </article>
                    ))}
                  </div>
                </section>
                <section className="admin-document-detail-section">
                  <h4>{locale === "vi" ? "Quan hệ dự đoán" : "Predicted relations"}</h4>
                  {annotationPreview.internal_payload.relations.length === 0 ? (
                    <p className="admin-row-time">{locale === "vi" ? "Chưa có relation trong preview này." : "No relations in this preview."}</p>
                  ) : (
                    <div className="admin-graph-relation-list">
                      {annotationPreview.internal_payload.relations.slice(0, 20).map((relation) => (
                        <article className="admin-graph-relation-item" key={`annotation-relation-${relation.id}`}>
                          <div className="admin-graph-relation-item-head">
                            <span className="admin-graph-edge-badge">{relation.relation_type}</span>
                            <span className="admin-graph-confidence">
                              {typeof relation.confidence_score === "number" ? `${Math.round(relation.confidence_score * 100)}%` : "--"}
                            </span>
                          </div>
                          <p className="admin-document-detail-summary">{relation.source_entity_id} {" -> "} {relation.target_entity_id}</p>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            ) : (
              <p className="admin-row-time">{locale === "vi" ? "Chưa có preview. Chọn một tài liệu để xem trước pre-label." : "No preview yet. Select a document to inspect generated pre-labels."}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

