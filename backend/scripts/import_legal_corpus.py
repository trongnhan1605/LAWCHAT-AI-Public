from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config import settings
from src.core.database import SessionLocal, engine
from src.core.schema_bootstrap import ensure_optional_schema_columns
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.services.admin_service import admin_service
from src.services.admin_upload_service import SUPPORTED_UPLOAD_EXTENSIONS, admin_upload_service
from src.services.embedding_service import embedding_service
from src.services.knowledge_service import knowledge_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset and import legal document folders into LawChat-AI knowledge base.")
    parser.add_argument("--source-dir", action="append", required=True, help="Folder containing PDF/TXT/DOCX legal documents. Can be passed multiple times.")
    parser.add_argument("--max-files-per-dir", type=int, default=None, help="Limit imported files from each source folder.")
    parser.add_argument("--reset-existing", action="store_true", help="Delete existing documents and dependent knowledge rows before importing.")
    parser.add_argument("--dry-run", action="store_true", help="Only list files and planned actions; do not mutate database or storage.")
    parser.add_argument("--enable-metadata-ai", action="store_true", help="Enable AI-assisted metadata prelabel for this run.")
    parser.add_argument("--enable-web-search", action="store_true", help="Enable metadata web search for this run. Requires provider support.")
    parser.add_argument("--enable-ai-fallback-parser", action="store_true", help="Enable AI fallback provision parser for low-quality deterministic parses.")
    parser.add_argument("--enable-embeddings", action="store_true", help="Enable embedding indexing for this run.")
    parser.add_argument("--duplicate-action", choices=["overwrite", "create_new"], default="overwrite")
    return parser.parse_args()


def collect_files(source_dirs: list[str], max_files_per_dir: int | None) -> list[Path]:
    files: list[Path] = []
    supported_suffixes = set(SUPPORTED_UPLOAD_EXTENSIONS)
    for raw_dir in source_dirs:
        source_dir = Path(raw_dir).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise SystemExit(f"Source directory not found: {source_dir}")
        candidates = sorted(
            [path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in supported_suffixes],
            key=lambda path: str(path).lower(),
        )
        files.extend(candidates[:max_files_per_dir] if max_files_per_dir else candidates)
    return files


def apply_runtime_ai_flags(args: argparse.Namespace) -> None:
    settings.document_metadata_ai_enabled = bool(args.enable_metadata_ai)
    settings.document_metadata_web_search_enabled = bool(args.enable_web_search)
    settings.legal_structure_ai_fallback_enabled = bool(args.enable_ai_fallback_parser)
    settings.ai_embedding_enabled = bool(args.enable_embeddings)


def reset_documents(db) -> dict[str, int]:
    documents = db.query(Document).order_by(Document.id.asc()).all()
    deleted = 0
    for document in documents:
        admin_service.delete_document(db, document.id)
        deleted += 1
    return {"deleted_documents": deleted}


def ingest_file(db, source_path: Path, duplicate_action: str) -> dict[str, object]:
    started = perf_counter()
    uploaded = admin_upload_service.store_local_document_file(source_path, db, import_subdir="imports")
    document = admin_service.create_document(
        db,
        uploaded.title,
        uploaded.file_name,
        uploaded.source_type,
        uploaded.legal_domain or "unknown",
        uploaded.authority_level,
        uploaded.issuing_authority,
        uploaded.document_code,
        uploaded.document_type,
        uploaded.normative_level,
        uploaded.signed_date,
        uploaded.source_reference,
        uploaded.storage_path,
        uploaded.summary,
        uploaded.effective_date,
        uploaded.expiry_date,
        uploaded.legal_status,
        True,
        duplicate_action,
        metadata_review_status="pending_review",
    )
    ingested_document, extracted_characters, chunk_count = knowledge_service.ingest_document(db, document.id)
    provision_count = db.query(LegalProvision).filter(LegalProvision.document_id == ingested_document.id).count()
    relation_count = db.query(ProvisionRelation).filter(ProvisionRelation.source_document_id == ingested_document.id).count()
    document_relation_count = db.query(DocumentRelation).filter(DocumentRelation.source_document_id == ingested_document.id).count()
    embedded_chunk_count = (
        db.query(DocumentChunkVector)
        .join(DocumentChunk, DocumentChunk.id == DocumentChunkVector.chunk_id)
        .filter(DocumentChunk.document_id == ingested_document.id)
        .filter(DocumentChunkVector.embedding_status == "indexed")
        .count()
    )
    return {
        "source_path": str(source_path),
        "document_id": ingested_document.id,
        "title": ingested_document.title,
        "document_code": ingested_document.document_code,
        "document_type": ingested_document.document_type,
        "legal_status": ingested_document.legal_status,
        "metadata_review_status": ingested_document.metadata_review_status,
        "ocr_quality_label": ingested_document.ocr_quality_label,
        "ocr_quality_score": float(ingested_document.ocr_quality_score) if ingested_document.ocr_quality_score is not None else None,
        "extracted_characters": extracted_characters,
        "chunk_count": chunk_count,
        "provision_count": provision_count,
        "provision_relation_count": relation_count,
        "document_relation_count": document_relation_count,
        "embedded_chunk_count": embedded_chunk_count,
        "elapsed_ms": round((perf_counter() - started) * 1000, 2),
    }


def main() -> int:
    args = parse_args()
    files = collect_files(args.source_dir, args.max_files_per_dir)
    summary: dict[str, object] = {
        "source_dirs": [str(Path(item).expanduser().resolve()) for item in args.source_dir],
        "file_count": len(files),
        "files": [str(path) for path in files],
        "ai": {
            "metadata_ai_enabled": bool(args.enable_metadata_ai),
            "web_search_enabled": bool(args.enable_web_search),
            "ai_fallback_parser_enabled": bool(args.enable_ai_fallback_parser),
            "embeddings_enabled": bool(args.enable_embeddings),
            "embedding_provider": embedding_service.active_provider(),
            "openai_base_url": settings.openai_base_url,
            "metadata_model": settings.openai_metadata_model,
            "embedding_model": embedding_service.active_model(),
        },
    }
    if args.dry_run:
        print(json.dumps({"status": "dry_run", **summary}, ensure_ascii=False, indent=2))
        return 0

    apply_runtime_ai_flags(args)
    ensure_optional_schema_columns(engine)
    imported: list[dict[str, object]] = []
    failed: list[dict[str, str]] = []
    reset_summary: dict[str, int] | None = None
    started = perf_counter()

    with SessionLocal() as db:
        if args.reset_existing:
            reset_summary = reset_documents(db)
        for path in files:
            try:
                imported.append(ingest_file(db, path, args.duplicate_action))
            except Exception as exc:
                failed.append({"source_path": str(path), "error": str(exc)})
                db.rollback()

    print(
        json.dumps(
            {
                "status": "completed" if not failed else "completed_with_failures",
                **summary,
                "reset": reset_summary,
                "imported_count": len(imported),
                "failed_count": len(failed),
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                "imported": imported,
                "failed": failed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
