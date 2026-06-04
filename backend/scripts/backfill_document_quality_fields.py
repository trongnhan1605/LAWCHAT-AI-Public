from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.database import SessionLocal, engine
from src.core.schema_bootstrap import ensure_optional_schema_columns
from src.ingestion.document_identity import document_identity_service
from src.models.document import Document


def main() -> int:
    ensure_optional_schema_columns(engine)
    updated = 0
    with SessionLocal() as db:
        documents = db.query(Document).order_by(Document.id.asc()).all()
        for document in documents:
            content_sha256 = document_identity_service.compute_content_sha256(document.storage_path)
            source_identity = document_identity_service.build_source_identity(
                source_reference=document.source_reference,
                storage_path=document.storage_path,
                content_sha256=content_sha256,
            )
            document.content_sha256 = content_sha256
            document.source_identity = source_identity
            ocr_quality_score = float(document.ocr_quality_score) if document.ocr_quality_score is not None else None
            if ocr_quality_score is not None and ocr_quality_score < 75:
                document.ingestion_quality_status = "blocked"
                document.ingestion_quality_notes = "ocr_quality_below_blocking_threshold"
                document.retrieval_visibility = "blocked"
            elif document.metadata_review_status != "reviewed":
                document.ingestion_quality_status = "review_required"
                document.ingestion_quality_notes = document.ingestion_quality_notes or "metadata_pending_review"
                document.retrieval_visibility = "indexed_unreviewed"
            else:
                document.ingestion_quality_status = "passed"
                document.ingestion_quality_notes = document.ingestion_quality_notes or "Backfilled from existing reviewed document."
                document.retrieval_visibility = "indexed_verified"
            updated += 1
        db.commit()
    print(f"Backfilled document quality fields for {updated} document(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
