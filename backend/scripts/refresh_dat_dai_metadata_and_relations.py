from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.database import SessionLocal
from src.models.document import Document
from src.services.knowledge_service import knowledge_service


def main() -> int:
    db = SessionLocal()
    refreshed = 0
    failed = 0
    failures: list[str] = []
    try:
        documents = (
            db.query(Document)
            .filter(Document.legal_domain == "dat-dai")
            .filter(Document.is_active == True)
            .order_by(Document.id.asc())
            .all()
        )
        print(f"Refreshing {len(documents)} dat-dai documents")
        for index, document in enumerate(documents, start=1):
            try:
                updated = knowledge_service.refresh_document_metadata_and_relations(db, document.id)
                refreshed += 1
                print(
                    f"[{index}/{len(documents)}] OK doc={updated.id} code={updated.document_code} "
                    f"type={updated.document_type} relation_status={updated.relation_sync_status}"
                )
            except Exception as exc:
                db.rollback()
                failed += 1
                failures.append(f"doc={document.id} title={document.title}: {exc}")
                print(f"[{index}/{len(documents)}] FAIL doc={document.id} error={exc}")
    finally:
        db.close()

    print("")
    print("REFRESH SUMMARY")
    print(f"refreshed={refreshed}")
    print(f"failed={failed}")
    if failures:
        print("FAILURES")
        for item in failures[:50]:
            print(item)
        if len(failures) > 50:
            print(f"... and {len(failures) - 50} more")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
