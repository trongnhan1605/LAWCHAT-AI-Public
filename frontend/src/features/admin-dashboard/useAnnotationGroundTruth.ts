import { useState } from "react";

import { lawChatApi } from "../../api/lawchat.api";
import type { AnnotationDocumentPayload, AnnotationGroundTruthSavePayload, AnnotationVendorExportPayload } from "../../types/lawchat";

export function useAnnotationGroundTruth() {
  const [annotationPreview, setAnnotationPreview] = useState<AnnotationVendorExportPayload | null>(null);
  const [annotationPreviewLoading, setAnnotationPreviewLoading] = useState(false);
  const [annotationPreviewDocumentId, setAnnotationPreviewDocumentId] = useState<number | null>(null);
  const [annotationSaveLoading, setAnnotationSaveLoading] = useState(false);
  const [annotationGroundTruthSave, setAnnotationGroundTruthSave] = useState<AnnotationGroundTruthSavePayload | null>(null);

  async function handleLoadAnnotationPreview(documentId: number) {
    setAnnotationPreviewLoading(true);
    setAnnotationPreviewDocumentId(documentId);
    setAnnotationGroundTruthSave(null);
    try {
      const payload = await lawChatApi.getLabelStudioAnnotationPreview(documentId);
      setAnnotationPreview(payload);
    } catch {
      setAnnotationPreview(null);
    } finally {
      setAnnotationPreviewLoading(false);
    }
  }

  async function handleSaveAnnotationGroundTruth(payload: AnnotationDocumentPayload) {
    setAnnotationSaveLoading(true);
    try {
      const saved = await lawChatApi.saveAnnotationGroundTruth(payload);
      setAnnotationGroundTruthSave(saved);
    } finally {
      setAnnotationSaveLoading(false);
    }
  }

  async function handleDownloadAnnotationGroundTruth(fileName: string) {
    const blob = await lawChatApi.downloadAnnotationGroundTruth(fileName);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  return {
    annotationGroundTruthSave,
    annotationPreview,
    annotationPreviewDocumentId,
    annotationPreviewLoading,
    annotationSaveLoading,
    handleDownloadAnnotationGroundTruth,
    handleLoadAnnotationPreview,
    handleSaveAnnotationGroundTruth,
  };
}
