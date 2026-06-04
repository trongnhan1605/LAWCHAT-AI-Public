from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import settings
from src.core.database import SessionLocal
from src.services.admin_service import admin_service
from src.services.knowledge_service import knowledge_service


SOURCE_ROOT = Path(
    r"<LOCAL_LEGAL_CORPUS_DIR>\DAT DAI-20260408T003138Z-3-001\DAT DAI"
)
DEST_ROOT = settings.legal_sources_dir / "uploads" / "dat-dai-import"
SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".txt"}


def build_title(relative_path: Path) -> str:
    stem = relative_path.stem.replace("_", " ").replace("-", " ").strip()
    parent = relative_path.parent.name.strip()
    if parent and parent != ".":
        return f"{stem} [{parent}]"
    return stem


def main() -> int:
    if not SOURCE_ROOT.exists():
        print(f"ERROR: source folder not found: {SOURCE_ROOT}")
        return 1

    settings.ai_embedding_enabled = False
    settings.document_metadata_ai_enabled = False
    settings.document_metadata_web_search_enabled = False
    settings.openai_api_key = None

    files = sorted(
        path for path in SOURCE_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        print("ERROR: no supported files found")
        return 1

    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    created_count = 0
    ingested_count = 0
    skipped_count = 0
    failed_count = 0
    total_chunks = 0
    failures: list[str] = []

    print(f"Found {len(files)} supported files")
    print("OpenAI usage disabled for this import run")

    try:
        for index, source_path in enumerate(files, start=1):
            relative_path = source_path.relative_to(SOURCE_ROOT)
            destination_path = DEST_ROOT / relative_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(source_path, destination_path)
                title = build_title(relative_path)
                document = admin_service.create_document(
                    db=db,
                    title=title,
                    file_name=relative_path.name,
                    source_type=source_path.suffix.lower().lstrip("."),
                    legal_domain="dat-dai",
                    authority_level=None,
                    issuing_authority=None,
                    document_code=None,
                    document_type=None,
                    normative_level=None,
                    signed_date=None,
                    source_reference=str(relative_path).replace("\\", "/"),
                    storage_path=str(destination_path),
                    summary=None,
                    effective_date=None,
                    expiry_date=None,
                    legal_status="unknown",
                    is_active=True,
                    duplicate_action="create_new",
                    metadata_review_status="pending_review",
                    metadata_review_notes="Imported in local-only mode from DAT DAI batch.",
                )
                created_count += 1

                _, _, chunk_count = knowledge_service.ingest_document(db, document.id)
                ingested_count += 1
                total_chunks += chunk_count
                print(f"[{index}/{len(files)}] OK doc={document.id} chunks={chunk_count} file={relative_path}")
            except Exception as exc:
                db.rollback()
                failed_count += 1
                failures.append(f"{relative_path}: {exc}")
                print(f"[{index}/{len(files)}] FAIL file={relative_path} error={exc}")
    finally:
        db.close()

    print("")
    print("IMPORT SUMMARY")
    print(f"created={created_count}")
    print(f"ingested={ingested_count}")
    print(f"skipped={skipped_count}")
    print(f"failed={failed_count}")
    print(f"total_chunks={total_chunks}")
    if failures:
        print("FAILURES")
        for item in failures[:50]:
            print(item)
        if len(failures) > 50:
            print(f"... and {len(failures) - 50} more")

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
