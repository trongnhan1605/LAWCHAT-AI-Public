import { Suspense, lazy, type ChangeEvent, type CSSProperties, type RefObject } from "react";

import type { DocumentItem, LegalProvisionItem, OcrCorrectionSuggestionItem } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { translateAdminTabLabel } from "../../locales/metadata";
import { CloseIcon } from "./icons";
import type { ChunkViewerState, DocumentEditorMode, DocumentModalState, DuplicateResolutionState, ProvisionRelationViewerState, ProvisionViewerState } from "./types";

const DocumentRichTextEditor = lazy(() => import("../../components/DocumentRichTextEditor"));

export function DocumentModal({
  applyingOcrCorrection,
  authorityLevel,
  authorityLevelOptions,
  canRestoreExtractedText,
  documentCode,
  documentEditorMode,
  documentEditorNotice,
  documentEditorRef,
  documentEditorReplace,
  documentEditorSearch,
  documentEffectiveDate,
  documentExpiryDate,
  documentExtractedCharacters,
  documentExtractedText,
  documentFileName,
  documentIsActive,
  documentIssuingAuthority,
  documentLegalDomain,
  documentLegalStatus,
  documentModalState,
  documentOcrSuggestions,
  documentSearchMatchCount,
  documentSignedDate,
  documentSourceReference,
  documentStoragePath,
  documentSummary,
  documentTitle,
  documentType,
  documentTypeOptions,
  documentUploadHelpText,
  fileInputRef,
  hasDocumentExtractDraft,
  legalDomainOptions,
  legalStatusOptions,
  locale,
  savingAdmin,
  ui,
  uploadingDocumentFile,
  onApplyOcrCorrection,
  onAuthorityLevelChange,
  onClearExtractedTextDraft,
  onClose,
  onDocumentCodeChange,
  onDocumentEffectiveDateChange,
  onDocumentEditorModeChange,
  onDocumentEditorReplaceChange,
  onDocumentEditorSearchChange,
  onDocumentExpiryDateChange,
  onDocumentExtractedTextChange,
  onDocumentFileNameChange,
  onDocumentFindNext,
  onDocumentIsActiveChange,
  onDocumentIssuingAuthorityChange,
  onDocumentLegalDomainChange,
  onDocumentLegalStatusChange,
  onDocumentSignedDateChange,
  onDocumentSourceReferenceChange,
  onDocumentSummaryChange,
  onDocumentTitleChange,
  onDocumentTypeChange,
  onFileSelection,
  onJoinBrokenLines,
  onNormalizeWhitespace,
  onRemoveBlankLines,
  onReplaceAll,
  onRestoreExtractedText,
  onSplitLegalHeadings,
  onSubmit,
}: {
  applyingOcrCorrection: boolean;
  authorityLevel: string;
  authorityLevelOptions: { value: string; label: string }[];
  canRestoreExtractedText: boolean;
  documentCode: string;
  documentEditorMode: DocumentEditorMode;
  documentEditorNotice: string | null;
  documentEditorRef: RefObject<HTMLTextAreaElement | null>;
  documentEditorReplace: string;
  documentEditorSearch: string;
  documentEffectiveDate: string;
  documentExpiryDate: string;
  documentExtractedCharacters: number;
  documentExtractedText: string;
  documentFileName: string;
  documentIsActive: boolean;
  documentIssuingAuthority: string;
  documentLegalDomain: string;
  documentLegalStatus: string;
  documentModalState: DocumentModalState;
  documentOcrSuggestions: OcrCorrectionSuggestionItem[];
  documentSearchMatchCount: number;
  documentSignedDate: string;
  documentSourceReference: string;
  documentStoragePath: string;
  documentSummary: string;
  documentTitle: string;
  documentType: string;
  documentTypeOptions: { value: string; label: string }[];
  documentUploadHelpText: string;
  fileInputRef: RefObject<HTMLInputElement | null>;
  hasDocumentExtractDraft: boolean;
  legalDomainOptions: { value: string; label: string }[];
  legalStatusOptions: { value: string; label: string }[];
  locale: Locale;
  savingAdmin: boolean;
  ui: UiText;
  uploadingDocumentFile: boolean;
  onApplyOcrCorrection: () => void;
  onAuthorityLevelChange: (value: string) => void;
  onClearExtractedTextDraft: () => void;
  onClose: () => void;
  onDocumentCodeChange: (value: string) => void;
  onDocumentEffectiveDateChange: (value: string) => void;
  onDocumentEditorModeChange: (value: DocumentEditorMode) => void;
  onDocumentEditorReplaceChange: (value: string) => void;
  onDocumentEditorSearchChange: (value: string) => void;
  onDocumentExpiryDateChange: (value: string) => void;
  onDocumentExtractedTextChange: (value: string) => void;
  onDocumentFileNameChange: (value: string) => void;
  onDocumentFindNext: () => void;
  onDocumentIsActiveChange: (value: boolean) => void;
  onDocumentIssuingAuthorityChange: (value: string) => void;
  onDocumentLegalDomainChange: (value: string) => void;
  onDocumentLegalStatusChange: (value: string) => void;
  onDocumentSignedDateChange: (value: string) => void;
  onDocumentSourceReferenceChange: (value: string) => void;
  onDocumentSummaryChange: (value: string) => void;
  onDocumentTitleChange: (value: string) => void;
  onDocumentTypeChange: (value: string) => void;
  onFileSelection: (event: ChangeEvent<HTMLInputElement>) => void;
  onJoinBrokenLines: () => void;
  onNormalizeWhitespace: () => void;
  onRemoveBlankLines: () => void;
  onReplaceAll: () => void;
  onRestoreExtractedText: () => void;
  onSplitLegalHeadings: () => void;
  onSubmit: () => void;
}) {
  if (!documentModalState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop">
      <div className="admin-modal-sheet admin-modal-sheet-wide admin-modal-sheet-editor" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{translateAdminTabLabel(locale, "documents")}</p>
            <h3>{documentModalState.mode === "create" ? ui.addDocumentButton : ui.editDocumentButton}</h3>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-document-layout">
          <div className="admin-document-metadata-pane admin-modal-scrollable">
            <div className="admin-form-field admin-form-field-wide">
              <label className="composer-label">{ui.documentStoragePathLabel}</label>
              <div className="admin-file-upload-row">
                <button className="secondary-button admin-upload-button" disabled={uploadingDocumentFile} onClick={() => fileInputRef.current?.click()} type="button">
                  {uploadingDocumentFile ? ui.browsingFileButton : ui.browseFileButton}
                </button>
                <span className="admin-upload-help">{documentUploadHelpText}</span>
              </div>
              <input accept=".pdf,.txt,.docx" className="admin-hidden-file-input" onChange={onFileSelection} ref={fileInputRef} type="file" />
              <div className="admin-storage-path-label">{documentStoragePath || ui.noStoragePathLabel}</div>
            </div>

            <TextField id="dashboard-document-title" label={ui.documentTitleLabel} value={documentTitle} onChange={onDocumentTitleChange} />
            <TextField id="dashboard-document-file-name" label={ui.documentFileNameLabel} value={documentFileName} onChange={onDocumentFileNameChange} />
            <SelectField id="dashboard-document-legal-domain" label={ui.documentLegalDomainLabel} options={legalDomainOptions} value={documentLegalDomain} onChange={onDocumentLegalDomainChange} />
            <SelectField id="dashboard-document-type" label={ui.documentTypeLabel} options={documentTypeOptions} value={documentType} onChange={onDocumentTypeChange} />
            <SelectField id="dashboard-document-authority-level" label={ui.documentAuthorityLevelLabel} options={authorityLevelOptions} value={authorityLevel} onChange={onAuthorityLevelChange} />
            <TextField id="dashboard-document-authority" label={ui.documentAuthorityLabel} value={documentIssuingAuthority} onChange={onDocumentIssuingAuthorityChange} />
            <TextField id="dashboard-document-code" label={ui.documentCodeLabel} value={documentCode} onChange={onDocumentCodeChange} />
            <DateField id="dashboard-document-signed-date" label={ui.documentSignedDateLabel} value={documentSignedDate} onChange={onDocumentSignedDateChange} />
            <DateField id="dashboard-document-effective-date" label={ui.documentEffectiveDateLabel} value={documentEffectiveDate} onChange={onDocumentEffectiveDateChange} />
            <DateField id="dashboard-document-expiry-date" label={ui.documentExpiryDateLabel} value={documentExpiryDate} onChange={onDocumentExpiryDateChange} />
            <SelectField id="dashboard-document-legal-status" label={ui.documentLegalStatusLabel} options={legalStatusOptions} value={documentLegalStatus} onChange={onDocumentLegalStatusChange} />
            <label className="admin-switch-row admin-form-field" htmlFor="dashboard-document-active">
              <input checked={documentIsActive} id="dashboard-document-active" onChange={(event) => onDocumentIsActiveChange(event.target.checked)} type="checkbox" />
              <span>
                <strong>{ui.activeDocumentLabel}</strong>
                <small>{ui.activeDocumentHelpText}</small>
              </span>
            </label>
            <TextAreaField id="dashboard-document-summary" label={ui.documentSummaryLabel} rows={5} value={documentSummary} onChange={onDocumentSummaryChange} />
            <TextField id="dashboard-document-reference" label={ui.documentReferenceLabel} value={documentSourceReference} onChange={onDocumentSourceReferenceChange} />
          </div>

          <div className="admin-document-editor-pane">
            <div className="admin-document-editor-pane-head">
              <div>
                <p className="section-label">{ui.documentExtractedTextPanelLabel}</p>
                <h4>{ui.documentExtractedTextLabel}</h4>
              </div>
            </div>
            {documentModalState.mode === "create" ? (
              <div className="admin-form-field admin-form-field-wide admin-document-editor-field">
                <div className="admin-document-editor-head">
                  <div>
                    <label className="composer-label" htmlFor="dashboard-document-extracted-text">{ui.documentExtractedTextLabel}</label>
                    <p className="admin-upload-help">{ui.documentExtractedTextHelp}</p>
                  </div>
                  <div className="admin-document-editor-toolbar">
                    <span className="admin-document-editor-meta">{ui.documentExtractedTextStats(documentExtractedCharacters, documentExtractedText.length)}</span>
                    <span className="admin-document-editor-meta">{hasDocumentExtractDraft ? ui.documentExtractedTextDraftSavedLabel : ui.documentExtractedTextOriginalLabel}</span>
                    <button className="ghost-button admin-document-restore-button" disabled={!canRestoreExtractedText} onClick={onRestoreExtractedText} type="button">{ui.documentExtractedTextRestoreButton}</button>
                    <button className="ghost-button admin-document-restore-button" disabled={!hasDocumentExtractDraft} onClick={onClearExtractedTextDraft} type="button">{ui.documentExtractedTextClearDraftButton}</button>
                  </div>
                </div>
                <div className="admin-document-editor-tools">
                  <div className="admin-document-editor-tool-group">
                    <button className={`secondary-button admin-document-tool-button ${documentEditorMode === "rich" ? "is-active" : ""}`} onClick={() => onDocumentEditorModeChange("rich")} type="button">{ui.documentExtractedTextRichModeLabel}</button>
                    <button className={`secondary-button admin-document-tool-button ${documentEditorMode === "plain" ? "is-active" : ""}`} onClick={() => onDocumentEditorModeChange("plain")} type="button">{ui.documentExtractedTextPlainModeLabel}</button>
                    <input className="admin-document-tool-input" onChange={(event) => onDocumentEditorSearchChange(event.target.value)} placeholder={ui.documentEditorSearchPlaceholder} type="text" value={documentEditorSearch} />
                    <input className="admin-document-tool-input" onChange={(event) => onDocumentEditorReplaceChange(event.target.value)} placeholder={ui.documentEditorReplacePlaceholder} type="text" value={documentEditorReplace} />
                    <button className="secondary-button admin-document-tool-button" disabled={!documentEditorSearch.trim()} onClick={onDocumentFindNext} type="button">{ui.documentEditorFindNextButton}</button>
                    <button className="secondary-button admin-document-tool-button" disabled={!documentEditorSearch.trim()} onClick={onReplaceAll} type="button">{ui.documentEditorReplaceAllButton}</button>
                    <span className="admin-document-editor-meta">{ui.documentEditorMatchCountLabel(documentSearchMatchCount)}</span>
                  </div>
                  <div className="admin-document-editor-tool-group">
                    <button className="secondary-button admin-document-tool-button" disabled={!documentExtractedText.trim() || applyingOcrCorrection} onClick={onApplyOcrCorrection} type="button">{applyingOcrCorrection ? ui.documentEditorOcrCorrectionRunningLabel : ui.documentEditorOcrCorrectionButton}</button>
                    <button className="secondary-button admin-document-tool-button" disabled={!documentExtractedText.trim()} onClick={onNormalizeWhitespace} type="button">{ui.documentEditorNormalizeSpacesButton}</button>
                    <button className="secondary-button admin-document-tool-button" disabled={!documentExtractedText.trim()} onClick={onRemoveBlankLines} type="button">{ui.documentEditorRemoveBlankLinesButton}</button>
                    <button className="secondary-button admin-document-tool-button" disabled={!documentExtractedText.trim()} onClick={onJoinBrokenLines} type="button">{ui.documentEditorJoinBrokenLinesButton}</button>
                    <button className="secondary-button admin-document-tool-button" disabled={!documentExtractedText.trim()} onClick={onSplitLegalHeadings} type="button">{ui.documentEditorSplitHeadingsButton}</button>
                  </div>
                </div>
                {documentEditorNotice ? <p className="admin-document-editor-notice">{documentEditorNotice}</p> : null}
                {documentEditorMode === "rich" ? (
                  <Suspense fallback={<div className="admin-document-rich-editor admin-document-rich-editor-loading" />}>
                    <DocumentRichTextEditor onChange={onDocumentExtractedTextChange} placeholder={ui.documentExtractedTextPlaceholder} value={documentExtractedText} />
                  </Suspense>
                ) : (
                  <textarea autoComplete="off" className="admin-document-editor-textarea" id="dashboard-document-extracted-text" onChange={(event) => onDocumentExtractedTextChange(event.target.value)} placeholder={ui.documentExtractedTextPlaceholder} ref={documentEditorRef} rows={18} spellCheck={false} value={documentExtractedText} />
                )}
                {documentOcrSuggestions.length > 0 ? (
                  <div className="admin-document-ocr-suggestions">
                    <strong>{ui.documentEditorOcrSuggestionsLabel}</strong>
                    <div className="admin-document-ocr-suggestion-list">
                      {documentOcrSuggestions.slice(0, 24).map((suggestion) => (
                        <span className="admin-document-ocr-suggestion-chip" key={`${suggestion.line_number ?? 0}-${suggestion.token_index}-${suggestion.original}-${suggestion.corrected}`} title={suggestion.context_excerpt ?? undefined}>
                          {suggestion.original} {"->"} {suggestion.corrected}
                          {typeof suggestion.confidence_score === "number" ? ` (${Math.round(suggestion.confidence_score * 100)}%)` : ""}
                        </span>
                      ))}
                      {documentOcrSuggestions.length > 24 ? <span className="admin-document-ocr-suggestion-chip">+{documentOcrSuggestions.length - 24}</span> : null}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="admin-document-editor-empty-state">
                <p>{ui.documentExtractedTextEditOnlyOnCreate}</p>
              </div>
            )}
          </div>
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          <button className="primary-button" disabled={savingAdmin || uploadingDocumentFile || !documentTitle.trim() || !documentFileName.trim() || !documentStoragePath.trim() || !documentLegalDomain.trim()} onClick={onSubmit} type="button">
            {savingAdmin ? ui.savingDocumentButton : documentModalState.mode === "create" ? ui.addDocumentButton : ui.saveChangesButton}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ChunkViewerModal({
  chunkViewerState,
  ingesting,
  ui,
  onClose,
  onRefresh,
  onReingest,
}: {
  chunkViewerState: ChunkViewerState | null;
  ingesting: boolean;
  ui: UiText;
  onClose: () => void;
  onRefresh: (document: DocumentItem) => void;
  onReingest: (document: DocumentItem) => void;
}) {
  if (!chunkViewerState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop" onClick={onClose}>
      <div className="admin-modal-sheet admin-modal-sheet-wide admin-chunk-viewer-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{ui.chunkViewerTitle}</p>
            <h3>{chunkViewerState.document.title}</h3>
            <p className="admin-chunk-viewer-description">{ui.chunkViewerDescription(chunkViewerState.document.title, chunkViewerState.chunks.length)}</p>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-modal-scrollable admin-chunk-viewer-scroll">
          {chunkViewerState.loading ? <p className="admin-chunk-viewer-status">{ui.refreshingDashboardButton}</p> : null}
          {!chunkViewerState.loading && chunkViewerState.error ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{chunkViewerState.error}</p>
              <button className="secondary-button" onClick={() => onRefresh(chunkViewerState.document)} type="button">{ui.chunkViewerRetryButton}</button>
            </div>
          ) : null}
          {!chunkViewerState.loading && !chunkViewerState.error && chunkViewerState.chunks.length === 0 ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{ui.chunkViewerEmpty}</p>
              <button className="secondary-button" disabled={ingesting} onClick={() => onReingest(chunkViewerState.document)} type="button">{ingesting ? ui.ingestLoading : ui.ingestButton}</button>
            </div>
          ) : null}
          {!chunkViewerState.loading && !chunkViewerState.error && chunkViewerState.chunks.length > 0 ? (
            <div className="admin-chunk-viewer-list">
              {chunkViewerState.chunks.map((chunk) => (
                <article className="admin-chunk-card" key={chunk.id}>
                  <div className="admin-chunk-card-head">
                    <strong>#{chunk.chunk_index}</strong>
                    <div className="admin-chip-row">
                      <span className="document-chip">{chunk.citation_label || chunk.section_title || ui.chunkSectionFallback}</span>
                      {chunk.chunk_type ? <span className="document-chip muted-chip">{chunk.chunk_type}</span> : null}
                      <span className="document-chip muted-chip">{ui.charsLabel}: {chunk.char_count}</span>
                    </div>
                  </div>
                  {chunk.hierarchy_path ? <div className="admin-row-time">{chunk.hierarchy_path}</div> : null}
                  <div className="admin-chunk-content">{chunk.content}</div>
                </article>
              ))}
            </div>
          ) : null}
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          {chunkViewerState.chunks.length === 0 ? (
            <button className="secondary-button" disabled={ingesting} onClick={() => onReingest(chunkViewerState.document)} type="button">{ingesting ? ui.ingestLoading : ui.ingestButton}</button>
          ) : (
            <button className="secondary-button" onClick={() => onRefresh(chunkViewerState.document)} type="button">{ui.chunkViewerRetryButton}</button>
          )}
        </div>
      </div>
    </div>
  );
}

function getProvisionIndentLevel(provision: LegalProvisionItem): number {
  if (provision.provision_level === "point") {
    return 2;
  }
  if (provision.provision_level === "clause") {
    return 1;
  }
  return 0;
}

function getProvisionBadge(ui: UiText, provision: LegalProvisionItem): string {
  if (provision.provision_level === "point") {
    return `${ui.pointLabelShort} ${provision.point_code ?? ""}`.trim();
  }
  if (provision.provision_level === "clause") {
    return `${ui.clauseLabelShort} ${provision.clause_number ?? ""}`.trim();
  }
  return `${ui.articleLabelShort} ${provision.article_number ?? ""}`.trim();
}

export function ProvisionViewerModal({
  provisionViewerState,
  ui,
  onClose,
  onRefresh,
  onSync,
}: {
  provisionViewerState: ProvisionViewerState | null;
  ui: UiText;
  onClose: () => void;
  onRefresh: (document: DocumentItem) => void;
  onSync: (document: DocumentItem) => void;
}) {
  if (!provisionViewerState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop" onClick={onClose}>
      <div className="admin-modal-sheet admin-modal-sheet-wide admin-chunk-viewer-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{ui.provisionViewerTitle}</p>
            <h3>{provisionViewerState.document.title}</h3>
            <p className="admin-chunk-viewer-description">{ui.provisionViewerDescription(provisionViewerState.document.title, provisionViewerState.provisions.length)}</p>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-modal-scrollable admin-chunk-viewer-scroll">
          {provisionViewerState.loading ? <p className="admin-chunk-viewer-status">{ui.refreshingDashboardButton}</p> : null}
          {!provisionViewerState.loading && provisionViewerState.error ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{provisionViewerState.error}</p>
              <button className="secondary-button" onClick={() => onRefresh(provisionViewerState.document)} type="button">{ui.provisionViewerRetryButton}</button>
            </div>
          ) : null}
          {!provisionViewerState.loading && !provisionViewerState.error && provisionViewerState.provisions.length === 0 ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{ui.provisionViewerEmpty}</p>
            </div>
          ) : null}
          {!provisionViewerState.loading && !provisionViewerState.error && provisionViewerState.provisions.length > 0 ? (
            <div className="admin-chunk-viewer-list">
              {provisionViewerState.provisions.map((provision) => (
                <article className="admin-chunk-card" key={provision.id} style={{ marginLeft: `${getProvisionIndentLevel(provision) * 20}px` } as CSSProperties}>
                  <div className="admin-chunk-card-head">
                    <strong>{getProvisionBadge(ui, provision)}</strong>
                    <div className="admin-chip-row">
                      <span className="document-chip">{provision.citation_label || provision.heading || ui.provisionViewerFallback}</span>
                      <span className="document-chip muted-chip">{provision.provision_level}</span>
                    </div>
                  </div>
                  {provision.heading ? <div className="admin-row-time">{provision.heading}</div> : null}
                  <div className="admin-chunk-content">{provision.content}</div>
                </article>
              ))}
            </div>
          ) : null}
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          <button className="secondary-button" onClick={() => onSync(provisionViewerState.document)} type="button">{ui.documentStructureSyncButton}</button>
          <button className="secondary-button" onClick={() => onRefresh(provisionViewerState.document)} type="button">{ui.provisionViewerRetryButton}</button>
        </div>
      </div>
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

export function ProvisionRelationViewerModal({
  provisionRelationViewerState,
  ui,
  onClose,
  onRefresh,
  onSync,
}: {
  provisionRelationViewerState: ProvisionRelationViewerState | null;
  ui: UiText;
  onClose: () => void;
  onRefresh: (document: DocumentItem) => void;
  onSync: (document: DocumentItem) => void;
}) {
  if (!provisionRelationViewerState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop" onClick={onClose}>
      <div className="admin-modal-sheet admin-modal-sheet-wide admin-chunk-viewer-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{ui.provisionRelationViewerTitle}</p>
            <h3>{provisionRelationViewerState.document.title}</h3>
            <p className="admin-chunk-viewer-description">{ui.provisionRelationViewerDescription(provisionRelationViewerState.document.title, provisionRelationViewerState.relations.length)}</p>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-modal-scrollable admin-chunk-viewer-scroll">
          {provisionRelationViewerState.loading ? <p className="admin-chunk-viewer-status">{ui.refreshingDashboardButton}</p> : null}
          {!provisionRelationViewerState.loading && provisionRelationViewerState.error ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{provisionRelationViewerState.error}</p>
              <button className="secondary-button" onClick={() => onRefresh(provisionRelationViewerState.document)} type="button">{ui.provisionRelationViewerRetryButton}</button>
            </div>
          ) : null}
          {!provisionRelationViewerState.loading && !provisionRelationViewerState.error && provisionRelationViewerState.relations.length === 0 ? (
            <div className="admin-chunk-viewer-status admin-chunk-viewer-error">
              <p>{ui.provisionRelationViewerEmpty}</p>
            </div>
          ) : null}
          {!provisionRelationViewerState.loading && !provisionRelationViewerState.error && provisionRelationViewerState.relations.length > 0 ? (
            <div className="admin-chunk-viewer-list">
              {provisionRelationViewerState.relations.map((relation) => {
                const metadata = parseRelationMetadata(relation.metadata_json);
                return (
                  <article className="admin-chunk-card" key={relation.id}>
                    <div className="admin-chunk-card-head">
                      <strong>{relation.relation_label || relation.relation_type}</strong>
                      <div className="admin-chip-row">
                        <span className="document-chip">{relation.relation_type}</span>
                        {typeof relation.confidence_score === "number" ? <span className="document-chip muted-chip">{ui.provisionRelationConfidenceLabel(Math.round(relation.confidence_score * 100))}</span> : null}
                      </div>
                    </div>
                    <div className="admin-row-time">{ui.provisionRelationSourceLabel}: {metadata.source_citation_label || relation.source_provision_id}</div>
                    <div className="admin-chunk-content">{relation.source_excerpt || ui.provisionRelationNoExcerpt}</div>
                    <div className="admin-row-time">{ui.provisionRelationTargetLabel}: {metadata.target_citation_label || relation.target_provision_id}</div>
                    <div className="admin-chunk-content">{relation.target_excerpt || ui.provisionRelationNoExcerpt}</div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          <button className="secondary-button" onClick={() => onSync(provisionRelationViewerState.document)} type="button">{ui.documentStructureSyncButton}</button>
          <button className="secondary-button" onClick={() => onRefresh(provisionRelationViewerState.document)} type="button">{ui.provisionRelationViewerRetryButton}</button>
        </div>
      </div>
    </div>
  );
}

export function DuplicateResolutionModal({
  duplicateResolutionState,
  ui,
  onClose,
  onResolve,
}: {
  duplicateResolutionState: DuplicateResolutionState | null;
  ui: UiText;
  onClose: () => void;
  onResolve: (action: "create_new" | "overwrite") => void;
}) {
  if (!duplicateResolutionState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop" onClick={onClose}>
      <div className="admin-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{ui.duplicateDocumentTitle}</p>
            <h3>{duplicateResolutionState.conflict.existing_document.title}</h3>
            <p className="admin-chunk-viewer-description">{ui.duplicateDocumentDescription}</p>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-modal-form admin-modal-scrollable">
          <div className="admin-duplicate-card">
            <strong>{ui.duplicateDocumentExistingLabel}</strong>
            <div className="admin-duplicate-grid">
              <span>{ui.documentTitleLabel}: {duplicateResolutionState.conflict.existing_document.title}</span>
              <span>{ui.documentFileNameLabel}: {duplicateResolutionState.conflict.existing_document.file_name}</span>
              <span>{ui.duplicateDocumentMatchingFieldsLabel}: {duplicateResolutionState.conflict.matching_fields.join(", ")}</span>
              <span>{ui.duplicateDocumentSuggestedTitleLabel}: {duplicateResolutionState.conflict.suggested_title}</span>
              <span>{ui.duplicateDocumentSuggestedFileNameLabel}: {duplicateResolutionState.conflict.suggested_file_name}</span>
            </div>
          </div>
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.duplicateDocumentSkipButton}</button>
          <button className="secondary-button" disabled={duplicateResolutionState.resolving} onClick={() => onResolve("create_new")} type="button">{ui.duplicateDocumentCreateNewButton}</button>
          <button className="primary-button" disabled={duplicateResolutionState.resolving} onClick={() => onResolve("overwrite")} type="button">{ui.duplicateDocumentOverwriteButton}</button>
        </div>
      </div>
    </div>
  );
}

function TextField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="admin-form-field">
      <label className="composer-label" htmlFor={id}>{label}</label>
      <input autoComplete="off" id={id} onChange={(event) => onChange(event.target.value)} spellCheck={false} value={value} />
    </div>
  );
}

function TextAreaField({ id, label, rows, value, onChange }: { id: string; label: string; rows: number; value: string; onChange: (value: string) => void }) {
  return (
    <div className="admin-form-field admin-form-field-wide">
      <label className="composer-label" htmlFor={id}>{label}</label>
      <textarea autoComplete="off" id={id} onChange={(event) => onChange(event.target.value)} rows={rows} spellCheck={false} value={value} />
    </div>
  );
}

function SelectField({ id, label, options, value, onChange }: { id: string; label: string; options: { value: string; label: string }[]; value: string; onChange: (value: string) => void }) {
  return (
    <div className="admin-form-field">
      <label className="composer-label" htmlFor={id}>{label}</label>
      <select id={id} onChange={(event) => onChange(event.target.value)} value={value}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
}

function DateField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="admin-form-field">
      <label className="composer-label" htmlFor={id}>{label}</label>
      <input id={id} onChange={(event) => onChange(event.target.value)} type="date" value={value} />
    </div>
  );
}
