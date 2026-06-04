import { useEffect, useMemo, useState } from "react";

import type { Locale, UiText } from "../../locales";
import type { AdminOperations, DefinitionItem } from "../../types/lawchat";
import { getDocumentTypeName, getLegalStatusLabel, normalizeSearchValue } from "./helpers";
import type { DocumentSortKey, SortDirection } from "./types";

type UseAdminDocumentCatalogParams = {
  adminData: AdminOperations | null;
  documentTypeDefinitions: DefinitionItem[];
  locale: Locale;
  ui: UiText;
};

export function useAdminDocumentCatalog({
  adminData,
  documentTypeDefinitions,
  locale,
  ui,
}: UseAdminDocumentCatalogParams) {
  const [documentSearch, setDocumentSearch] = useState("");
  const [documentStatusFilter, setDocumentStatusFilter] = useState("all");
  const [documentDomainFilter, setDocumentDomainFilter] = useState("all");
  const [documentSortKey, setDocumentSortKey] = useState<DocumentSortKey>("title");
  const [documentSortDirection, setDocumentSortDirection] = useState<SortDirection>("asc");
  const [documentPage, setDocumentPage] = useState(1);
  const [documentPageSize, setDocumentPageSize] = useState(10);
  const [expandedDocumentIds, setExpandedDocumentIds] = useState<number[]>([]);
  const [isDocumentFiltersVisible, setIsDocumentFiltersVisible] = useState(true);

  const filteredDocuments = useMemo(() => (adminData?.documents ?? []).filter((document) => {
    const normalizedSearch = normalizeSearchValue(documentSearch);
    const matchesSearch = !normalizedSearch || [
      document.title,
      document.file_name,
      document.document_code,
      document.issuing_authority,
      document.source_reference,
      getDocumentTypeName(locale, document.document_type, documentTypeDefinitions),
      adminData?.categories.find((category) => category.slug === document.legal_domain)?.name ?? document.legal_domain,
    ].some((value) => normalizeSearchValue(value).includes(normalizedSearch));
    const matchesStatus = documentStatusFilter === "all"
      || (documentStatusFilter === "active" && document.is_active)
      || (documentStatusFilter === "inactive" && !document.is_active);
    const matchesDomain = documentDomainFilter === "all" || document.legal_domain === documentDomainFilter;
    return matchesSearch && matchesStatus && matchesDomain;
  }), [adminData?.categories, adminData?.documents, documentDomainFilter, documentSearch, documentStatusFilter, documentTypeDefinitions, locale]);

  const sortedDocuments = useMemo(() => [...filteredDocuments].sort((left, right) => {
    const leftValue: string | number = (() => {
      switch (documentSortKey) {
        case "title":
          return `${left.title} ${left.file_name}`;
        case "legal_status":
          return getLegalStatusLabel(locale, left.legal_status);
        case "signed_date":
          return left.signed_date ?? "";
      }
    })();
    const rightValue: string | number = (() => {
      switch (documentSortKey) {
        case "title":
          return `${right.title} ${right.file_name}`;
        case "legal_status":
          return getLegalStatusLabel(locale, right.legal_status);
        case "signed_date":
          return right.signed_date ?? "";
      }
    })();

    const result = typeof leftValue === "number" && typeof rightValue === "number"
      ? leftValue - rightValue
      : String(leftValue).localeCompare(String(rightValue), locale === "vi" ? "vi" : "en", { numeric: true, sensitivity: "base" });
    return documentSortDirection === "asc" ? result : -result;
  }), [documentSortDirection, documentSortKey, filteredDocuments, locale]);

  const totalDocumentPages = Math.max(1, Math.ceil(sortedDocuments.length / documentPageSize));
  const currentDocumentPage = Math.min(documentPage, totalDocumentPages);
  const paginatedDocuments = sortedDocuments.slice((currentDocumentPage - 1) * documentPageSize, currentDocumentPage * documentPageSize);
  const paginationStart = sortedDocuments.length === 0 ? 0 : (currentDocumentPage - 1) * documentPageSize + 1;
  const paginationEnd = sortedDocuments.length === 0 ? 0 : Math.min(currentDocumentPage * documentPageSize, sortedDocuments.length);
  const statusFilterOptions = [
    { value: "all", label: ui.adminFilterAllLabel },
    { value: "active", label: ui.documentActivatedLabel },
    { value: "inactive", label: ui.documentDeactivatedLabel },
  ];

  useEffect(() => {
    setDocumentPage(1);
  }, [documentSearch, documentStatusFilter, documentDomainFilter, documentSortKey, documentSortDirection, documentPageSize]);

  useEffect(() => {
    if (documentPage > totalDocumentPages) {
      setDocumentPage(totalDocumentPages);
    }
  }, [documentPage, totalDocumentPages]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const media = window.matchMedia("(max-width: 900px)");
    const syncVisibility = () => setIsDocumentFiltersVisible(!media.matches);
    syncVisibility();
    media.addEventListener("change", syncVisibility);
    return () => media.removeEventListener("change", syncVisibility);
  }, []);

  function handleDocumentSort(nextKey: DocumentSortKey) {
    if (documentSortKey === nextKey) {
      setDocumentSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setDocumentSortKey(nextKey);
    setDocumentSortDirection(nextKey === "signed_date" ? "desc" : "asc");
  }

  function toggleDocumentExpanded(documentId: number) {
    setExpandedDocumentIds((current) => current.includes(documentId) ? current.filter((item) => item !== documentId) : [...current, documentId]);
  }

  return {
    currentDocumentPage,
    documentDomainFilter,
    documentPageSize,
    documentSearch,
    documentSortDirection,
    documentSortKey,
    documentStatusFilter,
    expandedDocumentIds,
    filteredDocuments,
    handleDocumentSort,
    isDocumentFiltersVisible,
    paginatedDocuments,
    paginationEnd,
    paginationStart,
    setDocumentDomainFilter,
    setDocumentPage,
    setDocumentPageSize,
    setDocumentSearch,
    setDocumentStatusFilter,
    setIsDocumentFiltersVisible,
    sortedDocuments,
    statusFilterOptions,
    toggleDocumentExpanded,
    totalDocumentPages,
  };
}
