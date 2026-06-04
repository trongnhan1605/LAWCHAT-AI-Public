from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.database import SessionLocal
from src.models.document import Document


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep an annotation trial batch unreviewed until legal reviewer review is available.")
    parser.add_argument("--manifest", type=Path, required=True, help="Annotation trial manifest JSON.")
    parser.add_argument("--reason", default="Legal review deferred until lawyer review session.", help="Reason appended to metadata review notes.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    document_ids = [int(item["document_id"]) for item in manifest.get("documents", [])]
    updated = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with SessionLocal() as db:
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        for document in documents:
            old_status = document.metadata_review_status
            old_visibility = document.retrieval_visibility
            document.metadata_review_status = "pending_review"
            document.metadata_last_reviewed_at = None
            document.ingestion_quality_status = "review_required" if document.ingestion_quality_status != "blocked" else "blocked"
            if document.retrieval_visibility != "blocked":
                document.retrieval_visibility = "indexed_unreviewed"
            note = f"{now}: {args.reason}"
            document.metadata_review_notes = f"{document.metadata_review_notes}\n{note}".strip() if document.metadata_review_notes else note
            if old_status != document.metadata_review_status or old_visibility != document.retrieval_visibility:
                updated += 1
            else:
                skipped += 1
        db.commit()

    print(json.dumps({"status": "deferred", "documents": len(document_ids), "updated": updated, "already_deferred": skipped}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
