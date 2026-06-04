import type { DefinitionItem } from "../../types/lawchat";
import type { AdminOperations } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { translateAdminTabLabel, translateBooleanState } from "../../locales/metadata";
import type { CategoryModalState, DefinitionKind, DefinitionModalState } from "./types";
import { CloseIcon, DeleteIcon, EditIcon } from "./icons";
import { SimpleSearchSection } from "./section-shell";

export function CategoriesSection({
  actionsColumnLabel,
  filteredCategories,
  locale,
  search,
  ui,
  onClear,
  onDelete,
  onEdit,
  onSearchChange,
}: {
  actionsColumnLabel: string;
  filteredCategories: AdminOperations["categories"];
  locale: Locale;
  search: string;
  ui: UiText;
  onClear: () => void;
  onDelete: (categoryId: number) => void;
  onEdit: (category: AdminOperations["categories"][number]) => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <SimpleSearchSection
      toolbar={
        <>
          <div className="admin-table-filters">
            <input className="admin-filter-input" onChange={(event) => onSearchChange(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={search} />
          </div>
          <button className="ghost-button admin-filter-clear-button" onClick={onClear} type="button">{ui.adminClearFiltersButton}</button>
        </>
      }
    >
      <table className="admin-table admin-table-compact">
        <thead>
          <tr>
            <th>{ui.categoryNameLabel}</th>
            <th>{ui.categorySlugLabel}</th>
            <th>{ui.categoryDescriptionLabel}</th>
            <th>{ui.statusLabel}</th>
            <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
          </tr>
        </thead>
        <tbody>
          {filteredCategories.length === 0 ? (
            <tr>
              <td colSpan={5}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td>
            </tr>
          ) : filteredCategories.map((category) => (
            <tr key={category.id}>
              <td className="admin-table-title-cell">{category.name}</td>
              <td>{category.slug}</td>
              <td>{category.description ?? ui.noDescription}</td>
              <td>
                <span className={`document-chip ${category.is_active ? "active-chip" : "inactive-chip"}`}>
                  {translateBooleanState(locale, category.is_active)}
                </span>
              </td>
              <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                <div className="admin-table-actions">
                  <button className="admin-icon-button" onClick={() => onEdit(category)} title={ui.editCategoryAction} type="button"><EditIcon /></button>
                  <button className="admin-icon-button danger" onClick={() => onDelete(category.id)} title={ui.deleteCategoryAction} type="button"><DeleteIcon /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </SimpleSearchSection>
  );
}

export function DefinitionsSection({
  actionsColumnLabel,
  items,
  kind,
  locale,
  search,
  ui,
  onClear,
  onDelete,
  onEdit,
  onSearchChange,
}: {
  actionsColumnLabel: string;
  items: (DefinitionItem & { count: number })[];
  kind: DefinitionKind;
  locale: Locale;
  search: string;
  ui: UiText;
  onClear: () => void;
  onDelete: (itemId: number) => void;
  onEdit: (item: DefinitionItem) => void;
  onSearchChange: (value: string) => void;
}) {
  const title = kind === "document-type" ? ui.documentTypeLabel : ui.documentAuthorityLevelLabel;
  const deleteTitle = kind === "document-type" ? ui.deleteDocumentTypeAction : ui.deleteAuthorityLevelAction;
  const editTitle = kind === "document-type" ? ui.editDocumentTypeAction : ui.editAuthorityLevelAction;

  return (
    <SimpleSearchSection
      toolbar={
        <>
          <div className="admin-table-filters">
            <input className="admin-filter-input" onChange={(event) => onSearchChange(event.target.value)} placeholder={ui.adminSearchPlaceholder} type="search" value={search} />
          </div>
          <button className="ghost-button admin-filter-clear-button" onClick={onClear} type="button">{ui.adminClearFiltersButton}</button>
        </>
      }
    >
      <table className="admin-table admin-table-compact">
        <thead>
          <tr>
            <th>{title}</th>
            <th>{ui.categorySlugLabel}</th>
            <th>{ui.definitionPriorityLabel}</th>
            <th>{translateAdminTabLabel(locale, "documents")}</th>
            <th>{ui.statusLabel}</th>
            <th>{ui.categoryDescriptionLabel}</th>
            <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={7}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td>
            </tr>
          ) : items.map((item) => (
            <tr key={item.id}>
              <td className="admin-table-title-cell">{item.name}</td>
              <td>{item.slug}</td>
              <td>{item.priority}</td>
              <td>{item.count}</td>
              <td>
                <span className={`document-chip ${item.is_active ? "active-chip" : "inactive-chip"}`}>
                  {translateBooleanState(locale, item.is_active)}
                </span>
              </td>
              <td>{item.description ?? ui.noDescription}</td>
              <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                <div className="admin-table-actions">
                  <button className="admin-icon-button" onClick={() => onEdit(item)} title={editTitle} type="button"><EditIcon /></button>
                  <button className="admin-icon-button danger" onClick={() => onDelete(item.id)} title={deleteTitle} type="button"><DeleteIcon /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </SimpleSearchSection>
  );
}

export function CategoryModal({
  categoryDescription,
  categoryIsActive,
  categoryModalState,
  categoryName,
  categorySlug,
  locale,
  savingAdmin,
  ui,
  onCategoryDescriptionChange,
  onCategoryIsActiveChange,
  onCategoryNameChange,
  onCategorySlugChange,
  onClose,
  onSubmit,
}: {
  categoryDescription: string;
  categoryIsActive: boolean;
  categoryModalState: CategoryModalState;
  categoryName: string;
  categorySlug: string;
  locale: Locale;
  savingAdmin: boolean;
  ui: UiText;
  onCategoryDescriptionChange: (value: string) => void;
  onCategoryIsActiveChange: (value: boolean) => void;
  onCategoryNameChange: (value: string) => void;
  onCategorySlugChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  if (!categoryModalState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop">
      <div className="admin-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{translateAdminTabLabel(locale, "categories")}</p>
            <h3>{categoryModalState.mode === "create" ? ui.createCategoryButton : ui.editCategoryButton}</h3>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button">
            <CloseIcon />
          </button>
        </div>

        <div className="admin-modal-form admin-modal-scrollable">
          <div className="admin-form-field">
            <label className="composer-label" htmlFor="dashboard-category-name">{ui.categoryNameLabel}</label>
            <input id="dashboard-category-name" onChange={(event) => onCategoryNameChange(event.target.value)} value={categoryName} />
          </div>

          <div className="admin-form-field">
            <label className="composer-label" htmlFor="dashboard-category-slug">{ui.categorySlugLabel}</label>
            <input id="dashboard-category-slug" onChange={(event) => onCategorySlugChange(event.target.value)} value={categorySlug} />
          </div>

          <div className="admin-form-field admin-form-field-wide">
            <label className="composer-label" htmlFor="dashboard-category-description">{ui.categoryDescriptionLabel}</label>
            <textarea id="dashboard-category-description" onChange={(event) => onCategoryDescriptionChange(event.target.value)} rows={4} value={categoryDescription} />
          </div>

          <label className="admin-switch-row" htmlFor="dashboard-category-active">
            <input checked={categoryIsActive} id="dashboard-category-active" onChange={(event) => onCategoryIsActiveChange(event.target.checked)} type="checkbox" />
            <span>{ui.activeCategoryLabel}</span>
          </label>
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          <button className="primary-button" disabled={savingAdmin || !categoryName.trim() || !categorySlug.trim()} onClick={onSubmit} type="button">
            {savingAdmin ? ui.creatingCategoryButton : categoryModalState.mode === "create" ? ui.createCategoryButton : ui.saveChangesButton}
          </button>
        </div>
      </div>
    </div>
  );
}

export function DefinitionModal({
  definitionDescription,
  definitionIsActive,
  definitionModalState,
  definitionName,
  definitionPriority,
  definitionSlug,
  locale,
  savingAdmin,
  ui,
  onClose,
  onDefinitionDescriptionChange,
  onDefinitionIsActiveChange,
  onDefinitionNameChange,
  onDefinitionPriorityChange,
  onDefinitionSlugChange,
  onSubmit,
}: {
  definitionDescription: string;
  definitionIsActive: boolean;
  definitionModalState: DefinitionModalState;
  definitionName: string;
  definitionPriority: string;
  definitionSlug: string;
  locale: Locale;
  savingAdmin: boolean;
  ui: UiText;
  onClose: () => void;
  onDefinitionDescriptionChange: (value: string) => void;
  onDefinitionIsActiveChange: (value: boolean) => void;
  onDefinitionNameChange: (value: string) => void;
  onDefinitionPriorityChange: (value: string) => void;
  onDefinitionSlugChange: (value: string) => void;
  onSubmit: () => void;
}) {
  if (!definitionModalState) {
    return null;
  }

  return (
    <div className="admin-modal-backdrop">
      <div className="admin-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{translateAdminTabLabel(locale, definitionModalState.kind === "document-type" ? "document-types" : "authority-levels")}</p>
            <h3>
              {definitionModalState.kind === "document-type"
                ? (definitionModalState.mode === "create" ? ui.createDocumentTypeButton : ui.editDocumentTypeButton)
                : (definitionModalState.mode === "create" ? ui.createAuthorityLevelButton : ui.editAuthorityLevelButton)}
            </h3>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button">
            <CloseIcon />
          </button>
        </div>

        <div className="admin-modal-form admin-modal-scrollable">
          <div className="admin-form-field">
            <label className="composer-label" htmlFor="dashboard-definition-name">{ui.categoryNameLabel}</label>
            <input id="dashboard-definition-name" onChange={(event) => onDefinitionNameChange(event.target.value)} value={definitionName} />
          </div>

          <div className="admin-form-field">
            <label className="composer-label" htmlFor="dashboard-definition-slug">{ui.categorySlugLabel}</label>
            <input id="dashboard-definition-slug" onChange={(event) => onDefinitionSlugChange(event.target.value)} value={definitionSlug} />
          </div>

          <div className="admin-form-field">
            <label className="composer-label" htmlFor="dashboard-definition-priority">{ui.definitionPriorityLabel}</label>
            <input id="dashboard-definition-priority" min="0" onChange={(event) => onDefinitionPriorityChange(event.target.value)} step="1" type="number" value={definitionPriority} />
          </div>

          <div className="admin-form-field admin-form-field-wide">
            <label className="composer-label" htmlFor="dashboard-definition-description">{ui.categoryDescriptionLabel}</label>
            <textarea id="dashboard-definition-description" onChange={(event) => onDefinitionDescriptionChange(event.target.value)} rows={4} value={definitionDescription} />
          </div>

          <label className="admin-switch-row" htmlFor="dashboard-definition-active">
            <input checked={definitionIsActive} id="dashboard-definition-active" onChange={(event) => onDefinitionIsActiveChange(event.target.checked)} type="checkbox" />
            <span>{ui.activeCategoryLabel}</span>
          </label>
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">{ui.cancelButton}</button>
          <button className="primary-button" disabled={savingAdmin || !definitionName.trim() || !definitionSlug.trim()} onClick={onSubmit} type="button">
            {savingAdmin
              ? ui.savingDocumentButton
              : definitionModalState.kind === "document-type"
                ? (definitionModalState.mode === "create" ? ui.createDocumentTypeButton : ui.saveChangesButton)
                : (definitionModalState.mode === "create" ? ui.createAuthorityLevelButton : ui.saveChangesButton)}
          </button>
        </div>
      </div>
    </div>
  );
}
