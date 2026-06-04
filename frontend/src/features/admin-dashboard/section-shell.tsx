import type { ReactNode } from "react";

export function SimpleSearchSection({ toolbar, children }: { toolbar: ReactNode; children: ReactNode }) {
  return (
    <div className="admin-table-section">
      <div className="admin-table-toolbar">{toolbar}</div>
      <div className="admin-table-wrap">{children}</div>
    </div>
  );
}
