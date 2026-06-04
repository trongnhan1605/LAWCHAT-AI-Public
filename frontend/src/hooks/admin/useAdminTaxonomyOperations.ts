import axios from "axios";
import { useState } from "react";

import { lawChatApi } from "../../api/lawchat.api";
import type { SharedAdminOperationParams } from "./types";

export function useAdminTaxonomyOperations({
  loadAdminOperations,
  savingAdmin,
  setError,
  setKnowledge,
  setSavingAdmin,
  ui,
}: SharedAdminOperationParams) {
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newCategorySlug, setNewCategorySlug] = useState("");
  const [newCategoryDescription, setNewCategoryDescription] = useState("");

  async function refreshKnowledgeOverview() {
    const overview = await lawChatApi.getKnowledgeOverview();
    setKnowledge(overview);
  }

  async function handleCreateCategory(name: string, slug: string, description: string) {
    if (!name.trim() || !slug.trim() || savingAdmin) {
      return;
    }

    setSavingAdmin(true);
    try {
      await lawChatApi.createCategory(name.trim(), slug.trim(), description.trim());
      setNewCategoryName("");
      setNewCategorySlug("");
      setNewCategoryDescription("");
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appCreateCategoryError);
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleToggleCategory(categoryId: number, isActive: boolean) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.toggleCategory(categoryId, isActive);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateCategoryError);
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateCategory(categoryId: number, name: string, slug: string, description: string, isActive: boolean) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateCategory(categoryId, name.trim(), slug.trim(), description.trim(), isActive);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateCategoryError);
      throw new Error("update-category-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteCategory(categoryId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteCategory(categoryId);
      await refreshKnowledgeOverview();
      await loadAdminOperations();
    } catch {
      setError(ui.appDeleteCategoryError);
      throw new Error("delete-category-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleCreateDocumentType(name: string, slug: string, description: string, priority: number) {
    if (!name.trim() || !slug.trim() || savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.createDocumentType(name.trim(), slug.trim(), description.trim(), priority);
      await loadAdminOperations();
    } catch {
      setError(ui.appCreateDocumentTypeError);
      throw new Error("create-document-type-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateDocumentType(itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateDocumentType(itemId, name.trim(), slug.trim(), description.trim(), priority, isActive);
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateDocumentTypeError);
      throw new Error("update-document-type-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteDocumentType(itemId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteDocumentType(itemId);
      await loadAdminOperations();
    } catch (caught) {
      setError(axios.isAxiosError(caught) ? (caught.response?.data?.message ?? ui.appDeleteDocumentTypeError) : ui.appDeleteDocumentTypeError);
      throw new Error("delete-document-type-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleCreateAuthorityLevel(name: string, slug: string, description: string, priority: number) {
    if (!name.trim() || !slug.trim() || savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.createAuthorityLevel(name.trim(), slug.trim(), description.trim(), priority);
      await loadAdminOperations();
    } catch {
      setError(ui.appCreateAuthorityLevelError);
      throw new Error("create-authority-level-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateAuthorityLevel(itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateAuthorityLevel(itemId, name.trim(), slug.trim(), description.trim(), priority, isActive);
      await loadAdminOperations();
    } catch {
      setError(ui.appUpdateAuthorityLevelError);
      throw new Error("update-authority-level-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteAuthorityLevel(itemId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteAuthorityLevel(itemId);
      await loadAdminOperations();
    } catch (caught) {
      setError(axios.isAxiosError(caught) ? (caught.response?.data?.message ?? ui.appDeleteAuthorityLevelError) : ui.appDeleteAuthorityLevelError);
      throw new Error("delete-authority-level-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  return {
    handleCreateAuthorityLevel,
    handleCreateCategory,
    handleCreateDocumentType,
    handleDeleteAuthorityLevel,
    handleDeleteCategory,
    handleDeleteDocumentType,
    handleToggleCategory,
    handleUpdateAuthorityLevel,
    handleUpdateCategory,
    handleUpdateDocumentType,
    newCategoryDescription,
    newCategoryName,
    newCategorySlug,
    setNewCategoryDescription,
    setNewCategoryName,
    setNewCategorySlug,
  };
}
