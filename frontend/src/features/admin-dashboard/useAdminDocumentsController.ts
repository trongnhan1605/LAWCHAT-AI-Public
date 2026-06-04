import axios, { type AxiosError } from "axios";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import { lawChatApi } from "../../api/lawchat.api";
import type { Locale, UiText } from "../../locales";
import type {
  AdminOperations,
  ApiEnvelope,
  AutoIngestedDocumentResult,
  DocumentChunkItem,
  DocumentGraphPayload,
  DocumentItem,
  DuplicateDocumentAction,
  DuplicateDocumentConflictData,
  LegalProvisionItem,
  OcrCorrectionSuggestionItem,
  ProvisionRelationItem,
  UploadedDocumentFile,
} from "../../types/lawchat";
import {
  EMPTY_DEFINITION_ITEMS,
  clearDocumentExtractDraft,
  getLegalStatusLabel,
  loadDocumentExtractDraft,
  normalizeDefinitionValue,
  saveDocumentExtractDraft,
} from "./helpers";
import type {
  ChunkViewerState,
  DocumentFormPayload,
  DocumentModalState,
  DuplicateResolutionState,
  GraphConnection,
  GraphViewerState,
  ProvisionRelationViewerState,
  ProvisionViewerState,
} from "./types";
import { DOCUMENT_SOURCE_TYPES, LEGAL_STATUS_VALUES } from "./types";
import { useAdminDocumentCatalog } from "./useAdminDocumentCatalog";

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() || "http://localhost:8000/api").replace(/\/$/, "");

type DuplicateDocumentErrorEnvelope = ApiEnvelope<DuplicateDocumentConflictData>;

function isDuplicateDocumentError(caught: unknown): caught is AxiosError<DuplicateDocumentErrorEnvelope> {
  return axios.isAxiosError(caught)
    && caught.response?.status === 409
    && caught.response?.data?.data?.conflict_type === "document_duplicate";
}

type UseAdminDocumentsControllerParams = {
  adminData: AdminOperations | null;
  locale: Locale;
  onCreateDocument: (payload: DocumentFormPayload, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">, extractedTextOverride?: string) => Promise<void> | void;
  onDeleteDocument: (documentId: number) => Promise<void> | void;
  onIngest: (documentId: number) => void | Promise<void>;
  onLoadDocumentChunks: (documentId: number) => Promise<DocumentChunkItem[]>;
  onLoadDocumentProvisions: (documentId: number) => Promise<LegalProvisionItem[]>;
  onLoadProvisionRelations: (documentId: number) => Promise<ProvisionRelationItem[]>;
  onRefreshDocumentStructure: (documentId: number) => Promise<void> | void;
  onReingestAllDocuments: () => void;
  onReviewDocumentMetadata: (documentId: number, notes?: string) => Promise<void> | void;
  onUpdateDocument: (documentId: number, payload: DocumentFormPayload) => Promise<void> | void;
  onUploadAndIngestDocumentFile: (file: File, duplicateAction?: Exclude<DuplicateDocumentAction, "skip">) => Promise<AutoIngestedDocumentResult>;
  onUploadDocumentFile: (file: File) => Promise<UploadedDocumentFile>;
  ui: UiText;
};

export function useAdminDocumentsController({
  adminData,
  locale,
  onCreateDocument,
  onDeleteDocument,
  onIngest,
  onLoadDocumentChunks,
  onLoadDocumentProvisions,
  onLoadProvisionRelations,
  onRefreshDocumentStructure,
  onReingestAllDocuments,
  onReviewDocumentMetadata,
  onUpdateDocument,
  onUploadAndIngestDocumentFile,
  onUploadDocumentFile,
  ui,
}: UseAdminDocumentsControllerParams) {
  const [documentModalState, setDocumentModalState] = useState<DocumentModalState>(null);
  const [chunkViewerState, setChunkViewerState] = useState<ChunkViewerState | null>(null);
  const [provisionViewerState, setProvisionViewerState] = useState<ProvisionViewerState | null>(null);
  const [provisionRelationViewerState, setProvisionRelationViewerState] = useState<ProvisionRelationViewerState | null>(null);
  const [graphViewerState, setGraphViewerState] = useState<GraphViewerState | null>(null);
  const [selectedGraphConnectionKey, setSelectedGraphConnectionKey] = useState<string | null>(null);
  const [duplicateResolutionState, setDuplicateResolutionState] = useState<DuplicateResolutionState | null>(null);

  const [documentTitle, setDocumentTitle] = useState("");
  const [documentFileName, setDocumentFileName] = useState("");
  const [documentSourceType, setDocumentSourceType] = useState<(typeof DOCUMENT_SOURCE_TYPES)[number]>("pdf");
  const [documentLegalDomain, setDocumentLegalDomain] = useState("lao-dong");
  const [documentAuthorityLevel, setDocumentAuthorityLevel] = useState("khac");
  const [documentIssuingAuthority, setDocumentIssuingAuthority] = useState("");
  const [documentCode, setDocumentCode] = useState("");
  const [documentType, setDocumentType] = useState("khac");
  const [documentNormativeLevel, setDocumentNormativeLevel] = useState("");
  const [documentSignedDate, setDocumentSignedDate] = useState("");
  const [documentSourceReference, setDocumentSourceReference] = useState("");
  const [documentStoragePath, setDocumentStoragePath] = useState("");
  const [documentSummary, setDocumentSummary] = useState("");
  const [documentExtractedText, setDocumentExtractedText] = useState("");
  const [documentOriginalExtractedText, setDocumentOriginalExtractedText] = useState("");
  const [documentExtractedCharacters, setDocumentExtractedCharacters] = useState(0);
  const [documentEditorMode, setDocumentEditorMode] = useState<"rich" | "plain">("rich");
  const [documentEditorSearch, setDocumentEditorSearch] = useState("");
  const [documentEditorReplace, setDocumentEditorReplace] = useState("");
  const [applyingOcrCorrection, setApplyingOcrCorrection] = useState(false);
  const [documentEditorNotice, setDocumentEditorNotice] = useState<string | null>(null);
  const [documentOcrSuggestions, setDocumentOcrSuggestions] = useState<OcrCorrectionSuggestionItem[]>([]);
  const [documentEffectiveDate, setDocumentEffectiveDate] = useState("");
  const [documentExpiryDate, setDocumentExpiryDate] = useState("");
  const [documentLegalStatus, setDocumentLegalStatus] = useState<(typeof LEGAL_STATUS_VALUES)[number]>("active");
  const [documentIsActive, setDocumentIsActive] = useState(true);
  const [uploadingDocumentFile, setUploadingDocumentFile] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const documentEditorRef = useRef<HTMLTextAreaElement | null>(null);

  const documentTypeDefinitions = adminData?.document_types ?? EMPTY_DEFINITION_ITEMS;
  const authorityLevelDefinitions = adminData?.authority_levels ?? EMPTY_DEFINITION_ITEMS;
  const documentCatalog = useAdminDocumentCatalog({
    adminData,
    documentTypeDefinitions,
    locale,
    ui,
  });

  const graphConnections: GraphConnection[] = useMemo(() => {
    if (!graphViewerState?.graph) {
      return [];
    }
    const nodesByDocumentId = new Map(
      graphViewerState.graph.nodes
        .filter((node): node is NonNullable<typeof node> & { document_id: number } => typeof node.document_id === "number")
        .map((node) => [node.document_id, node]),
    );
    const grouped = new Map<string, GraphConnection>();
    for (const edge of graphViewerState.graph.edges) {
      const sourceId = Number(edge.source);
      const targetId = Number(edge.target);
      if (!Number.isFinite(sourceId) || !Number.isFinite(targetId)) {
        continue;
      }
      const key = `${sourceId}-${targetId}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.relations.push(edge);
        continue;
      }
      grouped.set(key, {
        key,
        sourceId,
        targetId,
        sourceNode: nodesByDocumentId.get(sourceId) ?? null,
        targetNode: nodesByDocumentId.get(targetId) ?? null,
        relations: [edge],
      });
    }
    return [...grouped.values()].sort((left, right) => {
      const leftTouchesRoot = left.sourceId === graphViewerState.graph?.root_document_id || left.targetId === graphViewerState.graph?.root_document_id;
      const rightTouchesRoot = right.sourceId === graphViewerState.graph?.root_document_id || right.targetId === graphViewerState.graph?.root_document_id;
      if (leftTouchesRoot !== rightTouchesRoot) {
        return leftTouchesRoot ? -1 : 1;
      }
      return right.relations.length - left.relations.length;
    });
  }, [graphViewerState]);
  const selectedGraphConnection = graphConnections.find((item) => item.key === selectedGraphConnectionKey) ?? graphConnections[0] ?? null;

  const legalDomainOptions = useMemo(() => {
    const categoryOptions = (adminData?.categories ?? []).map((category) => ({ value: category.slug, label: category.name }));
    if (!documentLegalDomain) {
      return categoryOptions;
    }
    if (categoryOptions.some((option) => option.value === documentLegalDomain)) {
      return categoryOptions;
    }
    return [{ value: documentLegalDomain, label: documentLegalDomain }, ...categoryOptions];
  }, [adminData?.categories, documentLegalDomain]);

  const documentTypeOptions = useMemo(() => documentTypeDefinitions.map((item) => ({
    value: item.slug,
    label: `${item.priority} - ${item.name}`,
  })), [documentTypeDefinitions]);
  const authorityLevelOptions = useMemo(() => authorityLevelDefinitions.map((item) => ({
    value: item.slug,
    label: `${item.priority} - ${item.name}`,
  })), [authorityLevelDefinitions]);
  const legalStatusOptions = useMemo(() => LEGAL_STATUS_VALUES.map((value) => ({
    value,
    label: getLegalStatusLabel(locale, value),
  })), [locale]);

  const documentUploadHelpText = documentModalState?.mode === "create"
    ? ui.documentAutoIngestHelp
    : ui.documentReplaceFileHelp;
  const canRestoreExtractedText = Boolean(documentOriginalExtractedText) && documentExtractedText !== documentOriginalExtractedText;
  const hasDocumentExtractDraft = Boolean(documentStoragePath.trim()) && documentExtractedText !== documentOriginalExtractedText;
  const documentSearchMatchCount = documentEditorSearch.trim()
    ? (documentExtractedText.match(new RegExp(documentEditorSearch.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi")) ?? []).length
    : 0;
  useEffect(() => {
    const matchedType = documentTypeDefinitions.find((item) => item.slug === documentType);
    if (matchedType) {
      setDocumentNormativeLevel(String(matchedType.priority));
    }
  }, [documentType, documentTypeDefinitions]);

  const resetDocumentForm = useCallback(() => {
    setDocumentTitle("");
    setDocumentFileName("");
    setDocumentSourceType("pdf");
    setDocumentLegalDomain(adminData?.categories[0]?.slug ?? "lao-dong");
    setDocumentAuthorityLevel(authorityLevelDefinitions[authorityLevelDefinitions.length - 1]?.slug ?? "khac");
    setDocumentIssuingAuthority("");
    setDocumentCode("");
    setDocumentType(documentTypeDefinitions[documentTypeDefinitions.length - 1]?.slug ?? "khac");
    setDocumentNormativeLevel("");
    setDocumentSignedDate("");
    setDocumentSourceReference("");
    setDocumentStoragePath("");
    setDocumentSummary("");
    setDocumentExtractedText("");
    setDocumentOriginalExtractedText("");
    setDocumentExtractedCharacters(0);
    setDocumentEditorMode("rich");
    setDocumentEditorSearch("");
    setDocumentEditorReplace("");
    setApplyingOcrCorrection(false);
    setDocumentEditorNotice(null);
    setDocumentOcrSuggestions([]);
    setDocumentEffectiveDate("");
    setDocumentExpiryDate("");
    setDocumentLegalStatus("active");
    setDocumentIsActive(true);
  }, [adminData?.categories, authorityLevelDefinitions, documentTypeDefinitions]);

  useEffect(() => {
    if (documentModalState === null || documentModalState.mode === "create") {
      resetDocumentForm();
      return;
    }

    setDocumentTitle(documentModalState.document.title);
    setDocumentFileName(documentModalState.document.file_name);
    setDocumentSourceType((DOCUMENT_SOURCE_TYPES.includes(documentModalState.document.source_type as (typeof DOCUMENT_SOURCE_TYPES)[number])
      ? documentModalState.document.source_type
      : "pdf") as (typeof DOCUMENT_SOURCE_TYPES)[number]);
    setDocumentLegalDomain(documentModalState.document.legal_domain);
    setDocumentAuthorityLevel(normalizeDefinitionValue(documentModalState.document.authority_level, authorityLevelDefinitions, authorityLevelDefinitions[authorityLevelDefinitions.length - 1]?.slug ?? "khac"));
    setDocumentIssuingAuthority(documentModalState.document.issuing_authority ?? "");
    setDocumentCode(documentModalState.document.document_code ?? "");
    setDocumentType(normalizeDefinitionValue(documentModalState.document.document_type, documentTypeDefinitions, documentTypeDefinitions[documentTypeDefinitions.length - 1]?.slug ?? "khac"));
    setDocumentNormativeLevel(documentModalState.document.normative_level?.toString() ?? "");
    setDocumentSignedDate(documentModalState.document.signed_date ?? "");
    setDocumentSourceReference(documentModalState.document.source_reference ?? "");
    setDocumentStoragePath(documentModalState.document.storage_path ?? "");
    setDocumentSummary(documentModalState.document.summary ?? "");
    setDocumentExtractedText("");
    setDocumentOriginalExtractedText("");
    setDocumentExtractedCharacters(0);
    setDocumentEditorMode("rich");
    setDocumentEditorSearch("");
    setDocumentEditorReplace("");
    setApplyingOcrCorrection(false);
    setDocumentEditorNotice(null);
    setDocumentOcrSuggestions([]);
    setDocumentEffectiveDate(documentModalState.document.effective_date ?? "");
    setDocumentExpiryDate(documentModalState.document.expiry_date ?? "");
    setDocumentLegalStatus((LEGAL_STATUS_VALUES.includes((documentModalState.document.legal_status ?? "active") as (typeof LEGAL_STATUS_VALUES)[number])
      ? (documentModalState.document.legal_status ?? "active")
      : "active") as (typeof LEGAL_STATUS_VALUES)[number]);
    setDocumentIsActive(documentModalState.document.is_active);
  }, [authorityLevelDefinitions, documentModalState, documentTypeDefinitions, resetDocumentForm]);

  useEffect(() => {
    if (documentModalState?.mode !== "create" || !documentStoragePath.trim()) {
      return;
    }
    if (!documentExtractedText.trim() && !documentOriginalExtractedText.trim()) {
      clearDocumentExtractDraft(documentStoragePath);
      return;
    }
    if (documentExtractedText === documentOriginalExtractedText) {
      clearDocumentExtractDraft(documentStoragePath);
      return;
    }
    saveDocumentExtractDraft(documentStoragePath, documentExtractedText);
  }, [documentExtractedText, documentModalState?.mode, documentOriginalExtractedText, documentStoragePath]);

  function openCreateDocumentModal() {
    setDocumentModalState({ mode: "create", document: null });
  }

  function openEditDocumentModal(document: DocumentItem) {
    setDocumentModalState({ mode: "edit", document });
  }

  function closeDocumentModal() {
    setDocumentModalState(null);
  }

  function closeChunkViewer() {
    setChunkViewerState(null);
  }

  function closeProvisionViewer() {
    setProvisionViewerState(null);
  }

  function closeProvisionRelationViewer() {
    setProvisionRelationViewerState(null);
  }

  function closeDuplicateResolution() {
    setDuplicateResolutionState(null);
  }

  function applyDocumentTextTransform(transform: (value: string) => string) {
    setDocumentExtractedText((current) => transform(current));
  }

  function handleRestoreExtractedText() {
    setDocumentExtractedText(documentOriginalExtractedText);
  }

  function handleClearExtractedTextDraft() {
    clearDocumentExtractDraft(documentStoragePath);
    setDocumentExtractedText(documentOriginalExtractedText);
  }

  function handleNormalizeWhitespace() {
    applyDocumentTextTransform((value) => value.split(/\r?\n/).map((line) => line.replace(/[ \t]+/g, " ").trim()).join("\n").replace(/\n{3,}/g, "\n\n"));
  }

  function handleRemoveBlankLines() {
    applyDocumentTextTransform((value) => value.split(/\r?\n/).filter((line) => line.trim().length > 0).join("\n"));
  }

  function handleJoinBrokenLines() {
    applyDocumentTextTransform((value) => {
      const lines = value.split(/\r?\n/).map((line) => line.trim());
      const headingPattern = /^(Phần|Phan|Chương|Chuong|Mục|Muc|Điều|Dieu|Khoản|Khoan|Điểm|Diem)\b/i;
      const merged: string[] = [];
      for (const line of lines) {
        if (!line) {
          if (merged[merged.length - 1] !== "") {
            merged.push("");
          }
          continue;
        }
        const previous = merged[merged.length - 1];
        if (!previous || previous === "" || headingPattern.test(line) || headingPattern.test(previous)) {
          merged.push(line);
          continue;
        }
        merged[merged.length - 1] = `${previous} ${line}`.replace(/\s+/g, " ").trim();
      }
      return merged.join("\n").replace(/\n{3,}/g, "\n\n");
    });
  }

  function handleSplitLegalHeadings() {
    applyDocumentTextTransform((value) => value
      .replace(/\s+(?=(Phần|Phan|Chương|Chuong|Mục|Muc|Điều|Dieu)\s+[A-Z0-9IVXLCĐđ]+)/g, "\n")
      .replace(/\s+(?=(Khoản|Khoan|Điểm|Diem)\s+[0-9a-zA-ZđĐ]+)/g, "\n")
      .replace(/\n{3,}/g, "\n\n"));
  }

  async function handleApplyOcrCorrection() {
    if (!documentExtractedText.trim() || applyingOcrCorrection) {
      return;
    }
    setApplyingOcrCorrection(true);
    setDocumentEditorNotice(null);
    try {
      const preview = await lawChatApi.previewOcrCorrection(documentExtractedText);
      setDocumentOcrSuggestions(preview.suggestions ?? []);
      if (preview.changed) {
        setDocumentExtractedText(preview.corrected_text);
        setDocumentEditorNotice(preview.review_required
          ? ui.documentEditorOcrReviewRecommendedLabel(preview.changed_token_count)
          : ui.documentEditorOcrCorrectedLabel(preview.changed_token_count));
      } else {
        setDocumentEditorNotice(ui.documentEditorOcrNoChangeLabel);
      }
    } catch {
      setDocumentEditorNotice(locale === "vi" ? "Không thể chạy gợi ý sửa OCR lúc này." : "Unable to run OCR correction right now.");
    } finally {
      setApplyingOcrCorrection(false);
    }
  }

  function handleFindNextInDocument() {
    if (documentEditorMode !== "plain") {
      setDocumentEditorNotice(locale === "vi" ? "Tìm tiếp hiện hỗ trợ ở chế độ Văn bản thô." : "Find next is currently supported in plain text mode.");
      return;
    }
    const textarea = documentEditorRef.current;
    const query = documentEditorSearch.trim();
    if (!textarea || !query) {
      return;
    }
    const haystack = textarea.value.toLowerCase();
    const needle = query.toLowerCase();
    const startIndex = textarea.selectionEnd || 0;
    const nextIndex = haystack.indexOf(needle, startIndex);
    const matchIndex = nextIndex >= 0 ? nextIndex : haystack.indexOf(needle);
    if (matchIndex < 0) {
      return;
    }
    textarea.focus();
    textarea.setSelectionRange(matchIndex, matchIndex + query.length);
  }

  function handleReplaceAllInDocument() {
    const query = documentEditorSearch.trim();
    if (!query) {
      return;
    }
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const expression = new RegExp(escapedQuery, "gi");
    applyDocumentTextTransform((value) => value.replace(expression, documentEditorReplace));
  }

  async function loadDocumentChunks(document: DocumentItem) {
    setChunkViewerState({ document, chunks: [], loading: true, error: null });
    try {
      const chunks = await onLoadDocumentChunks(document.id);
      setChunkViewerState({ document, chunks, loading: false, error: null });
    } catch {
      setChunkViewerState({ document, chunks: [], loading: false, error: ui.appDocumentChunksError });
    }
  }

  async function loadDocumentProvisions(document: DocumentItem) {
    setProvisionViewerState({ document, provisions: [], loading: true, error: null });
    try {
      const provisions = await onLoadDocumentProvisions(document.id);
      setProvisionViewerState({ document, provisions, loading: false, error: null });
    } catch {
      setProvisionViewerState({
        document,
        provisions: [],
        loading: false,
        error: locale === "vi" ? "Không tải được cấu trúc điều khoản của tài liệu này." : "Unable to load document provisions.",
      });
    }
  }

  async function loadProvisionRelations(document: DocumentItem) {
    setProvisionRelationViewerState({ document, relations: [], loading: true, error: null });
    try {
      const relations = await onLoadProvisionRelations(document.id);
      setProvisionRelationViewerState({ document, relations, loading: false, error: null });
    } catch {
      setProvisionRelationViewerState({
        document,
        relations: [],
        loading: false,
        error: locale === "vi" ? "Không tải được quan hệ điều khoản của tài liệu này." : "Unable to load provision relations.",
      });
    }
  }

  async function loadDocumentGraph(document: DocumentItem, depth = 1) {
    setSelectedGraphConnectionKey(null);
    setGraphViewerState({ documentId: document.id, graph: null, loading: true, error: null });
    try {
      const response = await axios.get<ApiEnvelope<DocumentGraphPayload>>(`${API_BASE_URL}/knowledge/documents/${document.id}/graph`, {
        params: { depth },
      });
      setGraphViewerState({ documentId: document.id, graph: response.data.data, loading: false, error: null });
    } catch {
      setGraphViewerState({ documentId: document.id, graph: null, loading: false, error: locale === "vi" ? "Khong tai duoc do thi van ban" : "Failed to load document graph" });
    }
  }

  async function handleChunkReingest(document: DocumentItem) {
    await onIngest(document.id);
    await loadDocumentChunks(document);
    if (provisionViewerState?.document.id === document.id) {
      await loadDocumentProvisions(document);
    }
    if (provisionRelationViewerState?.document.id === document.id) {
      await loadProvisionRelations(document);
    }
  }

  async function handleSyncDocumentStructure(document: DocumentItem, target: "provisions" | "relations" = "provisions") {
    await onRefreshDocumentStructure(document.id);
    if (chunkViewerState?.document.id === document.id) {
      await loadDocumentChunks(document);
    }
    if (target === "provisions") {
      await loadDocumentProvisions(document);
    }
    if (target === "relations") {
      await loadProvisionRelations(document);
    }
    if (graphViewerState?.documentId === document.id) {
      await loadDocumentGraph(document);
    }
  }

  function applyUploadedDocumentPreview(uploaded: UploadedDocumentFile, defaultLegalDomain: string) {
    setDocumentTitle(uploaded.title);
    setDocumentFileName(uploaded.file_name);
    setDocumentSourceType((DOCUMENT_SOURCE_TYPES.includes(uploaded.source_type as (typeof DOCUMENT_SOURCE_TYPES)[number]) ? uploaded.source_type : "pdf") as (typeof DOCUMENT_SOURCE_TYPES)[number]);
    setDocumentLegalDomain(uploaded.legal_domain ?? defaultLegalDomain);
    setDocumentAuthorityLevel(normalizeDefinitionValue(uploaded.authority_level, authorityLevelDefinitions, authorityLevelDefinitions[authorityLevelDefinitions.length - 1]?.slug ?? "khac"));
    setDocumentIssuingAuthority(uploaded.issuing_authority ?? "");
    setDocumentCode(uploaded.document_code ?? "");
    setDocumentType(normalizeDefinitionValue(uploaded.document_type, documentTypeDefinitions, documentTypeDefinitions[documentTypeDefinitions.length - 1]?.slug ?? "khac"));
    setDocumentNormativeLevel(uploaded.normative_level?.toString() ?? "");
    setDocumentSignedDate(uploaded.signed_date ?? "");
    setDocumentSourceReference(uploaded.source_reference);
    setDocumentStoragePath(uploaded.storage_path);
    setDocumentSummary(uploaded.summary ?? "");
    setDocumentOriginalExtractedText(uploaded.extracted_text ?? "");
    setDocumentExtractedText(loadDocumentExtractDraft(uploaded.storage_path) ?? uploaded.extracted_text ?? "");
    setDocumentExtractedCharacters(uploaded.extracted_characters ?? 0);
    setDocumentOcrSuggestions(uploaded.ocr_suggestions ?? []);
    if (uploaded.ocr_applied && uploaded.ocr_review_required && uploaded.ocr_correction_changed_token_count > 0) {
      setDocumentEditorNotice(ui.documentEditorOcrReviewRecommendedLabel(uploaded.ocr_correction_changed_token_count));
    } else if (uploaded.ocr_applied) {
      setDocumentEditorNotice(ui.documentEditorOcrFallbackLabel);
    } else {
      setDocumentEditorNotice(null);
    }
    setDocumentEffectiveDate(uploaded.effective_date ?? "");
    setDocumentExpiryDate(uploaded.expiry_date ?? "");
    setDocumentLegalStatus((LEGAL_STATUS_VALUES.includes((uploaded.legal_status ?? "active") as (typeof LEGAL_STATUS_VALUES)[number]) ? (uploaded.legal_status ?? "active") : "active") as (typeof LEGAL_STATUS_VALUES)[number]);
  }

  async function handleDocumentFileSelection(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      return;
    }
    setUploadingDocumentFile(true);
    try {
      const uploaded = await onUploadDocumentFile(selectedFile);
      if (documentModalState?.mode === "create") {
        applyUploadedDocumentPreview(uploaded, adminData?.categories[0]?.slug ?? "lao-dong");
      } else {
        applyUploadedDocumentPreview(uploaded, documentLegalDomain);
      }
    } catch (caught) {
      if (isDuplicateDocumentError(caught)) {
        const conflict = caught.response?.data?.data;
        if (!conflict) {
          window.alert(ui.appDuplicateDocumentError);
          return;
        }
        setDuplicateResolutionState({ mode: "upload_and_ingest", file: selectedFile, conflict, resolving: false });
      } else if (axios.isAxiosError(caught)) {
        window.alert(caught.response?.data?.message ?? ui.appAutoIngestDocumentError);
      } else {
        window.alert(ui.appAutoIngestDocumentError);
      }
    } finally {
      setUploadingDocumentFile(false);
      event.target.value = "";
    }
  }

  function buildDocumentPayload(): DocumentFormPayload {
    return {
      title: documentTitle.trim(),
      file_name: documentFileName.trim(),
      source_type: documentSourceType,
      legal_domain: documentLegalDomain.trim(),
      authority_level: documentAuthorityLevel || null,
      issuing_authority: documentIssuingAuthority.trim() || null,
      document_code: documentCode.trim() || null,
      document_type: documentType || null,
      normative_level: documentNormativeLevel.trim() ? Number(documentNormativeLevel) : null,
      signed_date: documentSignedDate || null,
      source_reference: documentSourceReference.trim() || null,
      storage_path: documentStoragePath.trim(),
      summary: documentSummary.trim() || null,
      effective_date: documentEffectiveDate || null,
      expiry_date: documentExpiryDate || null,
      legal_status: documentLegalStatus || null,
      is_active: documentIsActive,
    };
  }

  async function handleDocumentSubmit() {
    if (documentModalState?.mode === "create" && !documentStoragePath.trim()) {
      return;
    }
    const payload = buildDocumentPayload();
    if (!payload.title || !payload.file_name || !payload.storage_path || !payload.legal_domain) {
      return;
    }
    if (documentModalState?.mode === "edit") {
      await onUpdateDocument(documentModalState.document.id, payload);
      closeDocumentModal();
      return;
    }
    try {
      await onCreateDocument(payload, undefined, documentExtractedText);
      clearDocumentExtractDraft(payload.storage_path);
      closeDocumentModal();
    } catch (caught) {
      if (isDuplicateDocumentError(caught)) {
        const conflict = caught.response?.data?.data;
        if (!conflict) {
          window.alert(ui.appDuplicateDocumentError);
          return;
        }
        setDuplicateResolutionState({ mode: "create_document", payload, extractedTextOverride: documentExtractedText, conflict, resolving: false });
        return;
      }
      throw caught;
    }
  }

  async function handleDuplicateResolution(action: Exclude<DuplicateDocumentAction, "skip">) {
    if (!duplicateResolutionState) {
      return;
    }
    setDuplicateResolutionState((current) => (current ? { ...current, resolving: true } : current));
    try {
      if (duplicateResolutionState.mode === "upload_and_ingest" && duplicateResolutionState.file) {
        const result = await onUploadAndIngestDocumentFile(duplicateResolutionState.file, action);
        window.alert(ui.appAutoIngestDocumentSuccess(result.document.title, result.chunk_count));
        closeDuplicateResolution();
        closeDocumentModal();
        return;
      }
      if (duplicateResolutionState.mode === "create_document" && duplicateResolutionState.payload) {
        await onCreateDocument(duplicateResolutionState.payload, action, duplicateResolutionState.extractedTextOverride);
        clearDocumentExtractDraft(duplicateResolutionState.payload.storage_path ?? "");
        closeDuplicateResolution();
        closeDocumentModal();
      }
    } catch {
      window.alert(ui.appDuplicateDocumentError);
    } finally {
      setDuplicateResolutionState((current) => (current ? { ...current, resolving: false } : current));
    }
  }

  async function handleDocumentDelete(documentId: number) {
    if (!window.confirm(ui.deleteDocumentConfirm)) {
      return;
    }
    await onDeleteDocument(documentId);
  }

  async function handleMarkDocumentReviewed(document: DocumentItem) {
    const note = window.prompt(ui.documentReviewPrompt, document.metadata_review_notes ?? "") ?? undefined;
    await onReviewDocumentMetadata(document.id, note);
  }

  function handleDownloadSource(documentId: number) {
    window.open(`${API_BASE_URL}/admin/documents/${documentId}/download`, "_blank", "noopener,noreferrer");
  }

  function handleReingestAll() {
    if (!window.confirm(ui.reingestAllConfirm)) {
      return;
    }
    onReingestAllDocuments();
  }

  return {
    applyingOcrCorrection,
    authorityLevelOptions,
    canRestoreExtractedText,
    chunkViewerState,
    closeChunkViewer,
    closeProvisionRelationViewer,
    closeProvisionViewer,
    closeDocumentModal,
    closeDuplicateResolution,
    currentDocumentPage: documentCatalog.currentDocumentPage,
    documentAuthorityLevel,
    documentCode,
    documentDomainFilter: documentCatalog.documentDomainFilter,
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
    documentPageSize: documentCatalog.documentPageSize,
    documentSearch: documentCatalog.documentSearch,
    documentSearchMatchCount,
    documentSignedDate,
    documentSortDirection: documentCatalog.documentSortDirection,
    documentSortKey: documentCatalog.documentSortKey,
    documentSourceReference,
    documentStatusFilter: documentCatalog.documentStatusFilter,
    documentStoragePath,
    documentSummary,
    documentTitle,
    documentType,
    documentTypeOptions,
    documentUploadHelpText,
    duplicateResolutionState,
    expandedDocumentIds: documentCatalog.expandedDocumentIds,
    fileInputRef,
    graphConnections,
    graphViewerState,
    handleApplyOcrCorrection,
    handleChunkReingest,
    handleClearExtractedTextDraft,
    handleDocumentDelete,
    handleDocumentFileSelection,
    handleDocumentSort: documentCatalog.handleDocumentSort,
    handleDocumentSubmit,
    handleDownloadSource,
    handleDuplicateResolution,
    handleFindNextInDocument,
    handleJoinBrokenLines,
    handleMarkDocumentReviewed,
    handleNormalizeWhitespace,
    handleReingestAll,
    handleRemoveBlankLines,
    handleReplaceAllInDocument,
    handleRestoreExtractedText,
    handleSplitLegalHeadings,
    handleSyncDocumentStructure,
    hasDocumentExtractDraft,
    isDocumentFiltersVisible: documentCatalog.isDocumentFiltersVisible,
    legalDomainOptions,
    legalStatusOptions,
    loadDocumentChunks,
    loadDocumentProvisions,
    loadProvisionRelations,
    loadDocumentGraph,
    openCreateDocumentModal,
    openEditDocumentModal,
    paginatedDocuments: documentCatalog.paginatedDocuments,
    paginationEnd: documentCatalog.paginationEnd,
    paginationStart: documentCatalog.paginationStart,
    provisionRelationViewerState,
    provisionViewerState,
    selectedGraphConnection,
    setDocumentAuthorityLevel,
    setDocumentCode,
    setDocumentDomainFilter: documentCatalog.setDocumentDomainFilter,
    setDocumentEditorMode,
    setDocumentEditorReplace,
    setDocumentEditorSearch,
    setDocumentEffectiveDate,
    setDocumentExpiryDate,
    setDocumentExtractedText,
    setDocumentFileName,
    setDocumentIsActive,
    setDocumentIssuingAuthority,
    setDocumentLegalDomain,
    setDocumentLegalStatus,
    setDocumentPage: documentCatalog.setDocumentPage,
    setDocumentPageSize: documentCatalog.setDocumentPageSize,
    setDocumentSearch: documentCatalog.setDocumentSearch,
    setDocumentSignedDate,
    setDocumentSourceReference,
    setDocumentStatusFilter: documentCatalog.setDocumentStatusFilter,
    setDocumentSummary,
    setDocumentTitle,
    setDocumentType,
    setIsDocumentFiltersVisible: documentCatalog.setIsDocumentFiltersVisible,
    setSelectedGraphConnectionKey,
    sortedDocuments: documentCatalog.sortedDocuments,
    statusFilterOptions: documentCatalog.statusFilterOptions,
    toggleDocumentExpanded: documentCatalog.toggleDocumentExpanded,
    totalDocumentPages: documentCatalog.totalDocumentPages,
    uploadingDocumentFile,
  };
}
