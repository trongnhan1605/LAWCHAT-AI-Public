import type { ContentArticle, ContentArticleWritePayload, LawyerProfile, LawyerProfileWritePayload } from "../../types/lawchat";
import type { Locale, UiText } from "../../locales";
import { translateBooleanState } from "../../locales/metadata";
import { CloseIcon, DeleteIcon, EditIcon } from "./icons";
import { SimpleSearchSection } from "./section-shell";

type ContentModalState =
  | { kind: "article"; mode: "create"; item: null }
  | { kind: "article"; mode: "edit"; item: ContentArticle }
  | { kind: "lawyer"; mode: "create"; item: null }
  | { kind: "lawyer"; mode: "edit"; item: LawyerProfile }
  | null;

export type { ContentModalState };

export function ContentArticlesSection({
  actionsColumnLabel,
  articles,
  locale,
  search,
  ui,
  onClear,
  onDelete,
  onEdit,
  onSearchChange,
}: {
  actionsColumnLabel: string;
  articles: ContentArticle[];
  locale: Locale;
  search: string;
  ui: UiText;
  onClear: () => void;
  onDelete: (articleId: number) => void;
  onEdit: (article: ContentArticle) => void;
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
            <th>{locale === "vi" ? "Tiêu đề" : "Title"}</th>
            <th>{locale === "vi" ? "Danh mục" : "Category"}</th>
            <th>{locale === "vi" ? "Tóm tắt" : "Excerpt"}</th>
            <th>{locale === "vi" ? "Nổi bật" : "Featured"}</th>
            <th>{ui.statusLabel}</th>
            <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
          </tr>
        </thead>
        <tbody>
          {articles.length === 0 ? (
            <tr><td colSpan={6}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td></tr>
          ) : articles.map((article) => (
            <tr key={article.id}>
              <td className="admin-table-title-cell">{article.title}</td>
              <td>{article.category}</td>
              <td>{article.excerpt}</td>
              <td>{translateBooleanState(locale, article.is_featured)}</td>
              <td><span className={`document-chip ${article.is_active ? "active-chip" : "inactive-chip"}`}>{translateBooleanState(locale, article.is_active)}</span></td>
              <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                <div className="admin-table-actions">
                  <button className="admin-icon-button" onClick={() => onEdit(article)} title={locale === "vi" ? "Sửa bài viết" : "Edit article"} type="button"><EditIcon /></button>
                  <button className="admin-icon-button danger" onClick={() => onDelete(article.id)} title={locale === "vi" ? "Xóa bài viết" : "Delete article"} type="button"><DeleteIcon /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </SimpleSearchSection>
  );
}

export function LawyerProfilesSection({
  actionsColumnLabel,
  lawyers,
  locale,
  search,
  ui,
  onClear,
  onDelete,
  onEdit,
  onSearchChange,
}: {
  actionsColumnLabel: string;
  lawyers: LawyerProfile[];
  locale: Locale;
  search: string;
  ui: UiText;
  onClear: () => void;
  onDelete: (lawyerId: number) => void;
  onEdit: (lawyer: LawyerProfile) => void;
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
            <th>{locale === "vi" ? "Luật sư" : "Lawyer"}</th>
            <th>{locale === "vi" ? "Địa điểm" : "Location"}</th>
            <th>{locale === "vi" ? "Chuyên môn" : "Specialties"}</th>
            <th>{locale === "vi" ? "Kinh nghiệm" : "Experience"}</th>
            <th>{ui.statusLabel}</th>
            <th className="admin-table-sticky-col admin-table-sticky-col-actions">{actionsColumnLabel}</th>
          </tr>
        </thead>
        <tbody>
          {lawyers.length === 0 ? (
            <tr><td colSpan={6}><div className="admin-table-empty">{ui.adminNoMatchingResultsLabel}</div></td></tr>
          ) : lawyers.map((lawyer) => (
            <tr key={lawyer.id}>
              <td className="admin-table-title-cell"><strong>{lawyer.full_name}</strong><p>{lawyer.title}</p></td>
              <td>{lawyer.location}</td>
              <td>{lawyer.specialties}</td>
              <td>{lawyer.experience_years} năm</td>
              <td><span className={`document-chip ${lawyer.is_active ? "active-chip" : "inactive-chip"}`}>{translateBooleanState(locale, lawyer.is_active)}</span></td>
              <td className="admin-table-sticky-col admin-table-sticky-col-actions">
                <div className="admin-table-actions">
                  <button className="admin-icon-button" onClick={() => onEdit(lawyer)} title={locale === "vi" ? "Sửa luật sư" : "Edit lawyer"} type="button"><EditIcon /></button>
                  <button className="admin-icon-button danger" onClick={() => onDelete(lawyer.id)} title={locale === "vi" ? "Xóa luật sư" : "Delete lawyer"} type="button"><DeleteIcon /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </SimpleSearchSection>
  );
}

export function ContentManagementModal({
  article,
  lawyer,
  locale,
  modalState,
  savingAdmin,
  onArticleChange,
  onClose,
  onLawyerChange,
  onSubmit,
}: {
  article: ContentArticleWritePayload;
  lawyer: LawyerProfileWritePayload;
  locale: Locale;
  modalState: ContentModalState;
  savingAdmin: boolean;
  onArticleChange: (payload: ContentArticleWritePayload) => void;
  onClose: () => void;
  onLawyerChange: (payload: LawyerProfileWritePayload) => void;
  onSubmit: () => void;
}) {
  if (!modalState) {
    return null;
  }
  const isArticle = modalState.kind === "article";
  const title = isArticle
    ? modalState.mode === "create" ? "Thêm bài viết" : "Sửa bài viết"
    : modalState.mode === "create" ? "Thêm luật sư" : "Sửa luật sư";

  return (
    <div className="admin-modal-backdrop">
      <div className="admin-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="admin-modal-head">
          <div>
            <p className="section-label">{isArticle ? "Nội dung website" : "Hồ sơ luật sư"}</p>
            <h3>{locale === "vi" ? title : title}</h3>
          </div>
          <button className="admin-icon-button" onClick={onClose} type="button"><CloseIcon /></button>
        </div>

        <div className="admin-modal-form admin-modal-scrollable">
          {isArticle ? (
            <>
              <TextField id="content-title" label="Tiêu đề" value={article.title} onChange={(value) => onArticleChange({ ...article, title: value })} />
              <TextField id="content-slug" label="Slug" value={article.slug} onChange={(value) => onArticleChange({ ...article, slug: value })} />
              <TextField id="content-category" label="Danh mục" value={article.category} onChange={(value) => onArticleChange({ ...article, category: value })} />
              <TextField id="content-source" label="Link nguồn" value={article.source_url ?? ""} onChange={(value) => onArticleChange({ ...article, source_url: value || null })} />
              <TextAreaField id="content-excerpt" label="Tóm tắt" value={article.excerpt} onChange={(value) => onArticleChange({ ...article, excerpt: value })} />
              <SwitchField id="content-featured" label="Hiển thị nổi bật" checked={article.is_featured} onChange={(value) => onArticleChange({ ...article, is_featured: value })} />
              <SwitchField id="content-active" label="Đang bật" checked={article.is_active} onChange={(value) => onArticleChange({ ...article, is_active: value })} />
            </>
          ) : (
            <>
              <TextField id="lawyer-name" label="Họ tên" value={lawyer.full_name} onChange={(value) => onLawyerChange({ ...lawyer, full_name: value })} />
              <TextField id="lawyer-slug" label="Slug" value={lawyer.slug} onChange={(value) => onLawyerChange({ ...lawyer, slug: value })} />
              <TextField id="lawyer-title" label="Chức danh" value={lawyer.title} onChange={(value) => onLawyerChange({ ...lawyer, title: value })} />
              <TextField id="lawyer-location" label="Địa điểm" value={lawyer.location} onChange={(value) => onLawyerChange({ ...lawyer, location: value })} />
              <TextField id="lawyer-specialties" label="Chuyên môn" value={lawyer.specialties} onChange={(value) => onLawyerChange({ ...lawyer, specialties: value })} />
              <TextField id="lawyer-experience" label="Số năm kinh nghiệm" type="number" value={String(lawyer.experience_years)} onChange={(value) => onLawyerChange({ ...lawyer, experience_years: Number(value) || 0 })} />
              <TextField id="lawyer-rating" label="Rating" value={lawyer.rating ?? ""} onChange={(value) => onLawyerChange({ ...lawyer, rating: value || null })} />
              <TextField id="lawyer-avatar" label="Avatar URL" value={lawyer.avatar_url ?? ""} onChange={(value) => onLawyerChange({ ...lawyer, avatar_url: value || null })} />
              <TextAreaField id="lawyer-bio" label="Giới thiệu" value={lawyer.bio ?? ""} onChange={(value) => onLawyerChange({ ...lawyer, bio: value || null })} />
              <SwitchField id="lawyer-featured" label="Hiển thị nổi bật" checked={lawyer.is_featured} onChange={(value) => onLawyerChange({ ...lawyer, is_featured: value })} />
              <SwitchField id="lawyer-active" label="Đang bật" checked={lawyer.is_active} onChange={(value) => onLawyerChange({ ...lawyer, is_active: value })} />
            </>
          )}
        </div>

        <div className="admin-modal-actions">
          <button className="ghost-button" onClick={onClose} type="button">Hủy</button>
          <button className="primary-button" disabled={savingAdmin || (isArticle ? !article.title.trim() || !article.slug.trim() || !article.excerpt.trim() : !lawyer.full_name.trim() || !lawyer.slug.trim())} onClick={onSubmit} type="button">
            {savingAdmin ? "Đang lưu" : "Lưu"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TextField({ id, label, type = "text", value, onChange }: { id: string; label: string; type?: string; value: string; onChange: (value: string) => void }) {
  return <div className="admin-form-field"><label className="composer-label" htmlFor={id}>{label}</label><input id={id} type={type} value={value} onChange={(event) => onChange(event.target.value)} /></div>;
}

function TextAreaField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return <div className="admin-form-field admin-form-field-wide"><label className="composer-label" htmlFor={id}>{label}</label><textarea id={id} rows={4} value={value} onChange={(event) => onChange(event.target.value)} /></div>;
}

function SwitchField({ id, label, checked, onChange }: { id: string; label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="admin-switch-row" htmlFor={id}><input id={id} type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>{label}</span></label>;
}
