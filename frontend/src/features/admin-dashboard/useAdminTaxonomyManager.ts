import { useEffect, useState } from "react";

import type { Category, DefinitionItem } from "../../types/lawchat";
import type { UiText } from "../../locales";
import type { CategoryModalState, DefinitionKind, DefinitionModalState } from "./types";

type UseAdminTaxonomyManagerParams = {
  ui: UiText;
  onCreateCategory: (name: string, slug: string, description: string) => Promise<void> | void;
  onCreateDocumentType: (name: string, slug: string, description: string, priority: number) => Promise<void> | void;
  onCreateAuthorityLevel: (name: string, slug: string, description: string, priority: number) => Promise<void> | void;
  onUpdateCategory: (categoryId: number, name: string, slug: string, description: string, isActive: boolean) => Promise<void> | void;
  onUpdateDocumentType: (itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => Promise<void> | void;
  onUpdateAuthorityLevel: (itemId: number, name: string, slug: string, description: string, priority: number, isActive: boolean) => Promise<void> | void;
  onDeleteCategory: (categoryId: number) => Promise<void> | void;
  onDeleteDocumentType: (itemId: number) => Promise<void> | void;
  onDeleteAuthorityLevel: (itemId: number) => Promise<void> | void;
};

export function useAdminTaxonomyManager({
  ui,
  onCreateCategory,
  onCreateDocumentType,
  onCreateAuthorityLevel,
  onUpdateCategory,
  onUpdateDocumentType,
  onUpdateAuthorityLevel,
  onDeleteCategory,
  onDeleteDocumentType,
  onDeleteAuthorityLevel,
}: UseAdminTaxonomyManagerParams) {
  const [categoryModalState, setCategoryModalState] = useState<CategoryModalState>(null);
  const [definitionModalState, setDefinitionModalState] = useState<DefinitionModalState>(null);

  const [categoryName, setCategoryName] = useState("");
  const [categorySlug, setCategorySlug] = useState("");
  const [categoryDescription, setCategoryDescription] = useState("");
  const [categoryIsActive, setCategoryIsActive] = useState(true);

  const [definitionName, setDefinitionName] = useState("");
  const [definitionSlug, setDefinitionSlug] = useState("");
  const [definitionDescription, setDefinitionDescription] = useState("");
  const [definitionPriority, setDefinitionPriority] = useState("0");
  const [definitionIsActive, setDefinitionIsActive] = useState(true);

  useEffect(() => {
    if (categoryModalState === null) {
      setCategoryName("");
      setCategorySlug("");
      setCategoryDescription("");
      setCategoryIsActive(true);
      return;
    }

    if (categoryModalState.mode === "create") {
      setCategoryName("");
      setCategorySlug("");
      setCategoryDescription("");
      setCategoryIsActive(true);
      return;
    }

    setCategoryName(categoryModalState.category.name);
    setCategorySlug(categoryModalState.category.slug);
    setCategoryDescription(categoryModalState.category.description ?? "");
    setCategoryIsActive(categoryModalState.category.is_active);
  }, [categoryModalState]);

  useEffect(() => {
    if (definitionModalState === null) {
      setDefinitionName("");
      setDefinitionSlug("");
      setDefinitionDescription("");
      setDefinitionPriority("0");
      setDefinitionIsActive(true);
      return;
    }

    if (definitionModalState.mode === "create") {
      setDefinitionName("");
      setDefinitionSlug("");
      setDefinitionDescription("");
      setDefinitionPriority(definitionModalState.kind === "document-type" ? "40" : "10");
      setDefinitionIsActive(true);
      return;
    }

    setDefinitionName(definitionModalState.item.name);
    setDefinitionSlug(definitionModalState.item.slug);
    setDefinitionDescription(definitionModalState.item.description ?? "");
    setDefinitionPriority(String(definitionModalState.item.priority));
    setDefinitionIsActive(definitionModalState.item.is_active);
  }, [definitionModalState]);

  function openCreateCategoryModal() {
    setCategoryModalState({ mode: "create", category: null });
  }

  function openEditCategoryModal(category: Category) {
    setCategoryModalState({ mode: "edit", category });
  }

  function closeCategoryModal() {
    setCategoryModalState(null);
  }

  function openCreateDefinitionModal(kind: DefinitionKind) {
    setDefinitionModalState({ kind, mode: "create", item: null });
  }

  function openEditDefinitionModal(kind: DefinitionKind, item: DefinitionItem) {
    setDefinitionModalState({ kind, mode: "edit", item });
  }

  function closeDefinitionModal() {
    setDefinitionModalState(null);
  }

  async function handleCategorySubmit() {
    const name = categoryName.trim();
    const slug = categorySlug.trim();
    const description = categoryDescription.trim();
    if (!name || !slug) {
      return;
    }

    if (categoryModalState?.mode === "edit") {
      await onUpdateCategory(categoryModalState.category.id, name, slug, description, categoryIsActive);
      closeCategoryModal();
      return;
    }

    await onCreateCategory(name, slug, description);
    closeCategoryModal();
  }

  async function handleCategoryDelete(categoryId: number) {
    if (!window.confirm(ui.deleteCategoryConfirm)) {
      return;
    }

    await onDeleteCategory(categoryId);
  }

  async function handleDefinitionSubmit() {
    const name = definitionName.trim();
    const slug = definitionSlug.trim();
    const description = definitionDescription.trim();
    const priority = Number(definitionPriority || "0");
    if (!definitionModalState || !name || !slug || Number.isNaN(priority)) {
      return;
    }

    if (definitionModalState.kind === "document-type") {
      if (definitionModalState.mode === "edit") {
        await onUpdateDocumentType(definitionModalState.item.id, name, slug, description, priority, definitionIsActive);
      } else {
        await onCreateDocumentType(name, slug, description, priority);
      }
      closeDefinitionModal();
      return;
    }

    if (definitionModalState.mode === "edit") {
      await onUpdateAuthorityLevel(definitionModalState.item.id, name, slug, description, priority, definitionIsActive);
    } else {
      await onCreateAuthorityLevel(name, slug, description, priority);
    }
    closeDefinitionModal();
  }

  async function handleDefinitionDelete(kind: DefinitionKind, itemId: number) {
    const confirmed = window.confirm(kind === "document-type" ? ui.deleteDocumentTypeConfirm : ui.deleteAuthorityLevelConfirm);
    if (!confirmed) {
      return;
    }

    if (kind === "document-type") {
      await onDeleteDocumentType(itemId);
      return;
    }

    await onDeleteAuthorityLevel(itemId);
  }

  return {
    categoryModalState,
    categoryName,
    categorySlug,
    categoryDescription,
    categoryIsActive,
    definitionModalState,
    definitionName,
    definitionSlug,
    definitionDescription,
    definitionPriority,
    definitionIsActive,
    setCategoryName,
    setCategorySlug,
    setCategoryDescription,
    setCategoryIsActive,
    setDefinitionName,
    setDefinitionSlug,
    setDefinitionDescription,
    setDefinitionPriority,
    setDefinitionIsActive,
    openCreateCategoryModal,
    openEditCategoryModal,
    closeCategoryModal,
    openCreateDefinitionModal,
    openEditDefinitionModal,
    closeDefinitionModal,
    handleCategorySubmit,
    handleCategoryDelete,
    handleDefinitionSubmit,
    handleDefinitionDelete,
  };
}