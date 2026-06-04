import { useEffect } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";

type DocumentRichTextEditorProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  disabled?: boolean;
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildHtmlFromPlainText(value: string): string {
  const lines = value.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  if (lines.length === 0) {
    return "<p></p>";
  }
  return lines.map((line) => `<p>${line ? escapeHtml(line) : "<br />"}</p>`).join("");
}

function readPlainTextFromEditor(editor: NonNullable<ReturnType<typeof useEditor>>): string {
  return editor.state.doc.textBetween(0, editor.state.doc.content.size, "\n");
}

export default function DocumentRichTextEditor({
  value,
  onChange,
  placeholder,
  disabled = false,
}: DocumentRichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content: buildHtmlFromPlainText(value),
    editable: !disabled,
    onUpdate: ({ editor: activeEditor }) => {
      const nextValue = readPlainTextFromEditor(activeEditor);
      if (nextValue !== value) {
        onChange(nextValue);
      }
    },
  });

  useEffect(() => {
    if (!editor) {
      return;
    }
    editor.setEditable(!disabled);
  }, [disabled, editor]);

  useEffect(() => {
    if (!editor) {
      return;
    }
    const currentValue = readPlainTextFromEditor(editor);
    if (currentValue === value) {
      return;
    }
    editor.commands.setContent(buildHtmlFromPlainText(value), { emitUpdate: false });
  }, [editor, value]);

  if (!editor) {
    return <div className="admin-document-rich-editor admin-document-rich-editor-loading" />;
  }

  return (
    <div className="admin-document-rich-editor">
      <div className="admin-document-rich-toolbar">
        <button className={`admin-document-rich-tool ${editor.isActive("bold") ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleBold().run()} type="button">
          B
        </button>
        <button className={`admin-document-rich-tool ${editor.isActive("italic") ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleItalic().run()} type="button">
          I
        </button>
        <button className={`admin-document-rich-tool ${editor.isActive("heading", { level: 1 }) ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} type="button">
          H1
        </button>
        <button className={`admin-document-rich-tool ${editor.isActive("heading", { level: 2 }) ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} type="button">
          H2
        </button>
        <button className={`admin-document-rich-tool ${editor.isActive("bulletList") ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleBulletList().run()} type="button">
          •
        </button>
        <button className={`admin-document-rich-tool ${editor.isActive("blockquote") ? "is-active" : ""}`} onClick={() => editor.chain().focus().toggleBlockquote().run()} type="button">
          "
        </button>
        <button className="admin-document-rich-tool" onClick={() => editor.chain().focus().undo().run()} type="button">
          ↶
        </button>
        <button className="admin-document-rich-tool" onClick={() => editor.chain().focus().redo().run()} type="button">
          ↷
        </button>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
