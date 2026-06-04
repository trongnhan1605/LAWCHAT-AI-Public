from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Package an annotation trial batch for legal reviewer handoff.")
    parser.add_argument("--manifest", type=Path, required=True, help="Annotation trial manifest JSON.")
    parser.add_argument("--tasks", type=Path, required=True, help="Label Studio tasks JSON generated from the manifest.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output package directory.")
    parser.add_argument("--chunk-size", type=int, default=5, help="Number of Label Studio tasks per split file.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    generated_at = datetime.now().isoformat(timespec="seconds")
    package_dir = args.output_dir or settings.legal_sources_dir / f"annotation_trial_package_{datetime.now().strftime('%Y%m%d')}"
    package_dir.mkdir(parents=True, exist_ok=True)

    documents = list(manifest.get("documents", []))
    _write_documents_csv(package_dir / "selected_documents.csv", documents)
    _write_review_tracker(package_dir / "review_tracker.csv", documents)
    split_files = _write_split_tasks(package_dir, tasks, chunk_size=args.chunk_size)
    _write_readme(package_dir / "README.md", manifest=manifest, split_files=split_files, generated_at=generated_at)
    _write_package_manifest(
        package_dir / "package_manifest.json",
        source_manifest=args.manifest,
        source_tasks=args.tasks,
        generated_at=generated_at,
        documents=documents,
        split_files=split_files,
    )

    print(
        json.dumps(
            {
                "status": "generated",
                "package_dir": str(package_dir),
                "document_count": len(documents),
                "task_count": len(tasks),
                "split_file_count": len(split_files),
                "chunk_size": args.chunk_size,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _write_documents_csv(path: Path, documents: list[dict[str, Any]]) -> None:
    fieldnames = [
        "document_id",
        "file_name",
        "title",
        "legal_domain",
        "document_type",
        "document_code",
        "issuing_authority",
        "effective_date",
        "legal_status",
        "risk_level",
        "selection_reason",
        "selection_score",
        "issue_codes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for document in documents:
            row = {field: document.get(field) for field in fieldnames}
            row["issue_codes"] = ";".join(document.get("issue_codes") or [])
            writer.writerow(row)


def _write_review_tracker(path: Path, documents: list[dict[str, Any]]) -> None:
    fieldnames = [
        "document_id",
        "file_name",
        "reviewer",
        "metadata_status",
        "structure_status",
        "relation_status",
        "overall_status",
        "needs_manual_cleanup",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for document in documents:
            writer.writerow(
                {
                    "document_id": document.get("document_id"),
                    "file_name": document.get("file_name"),
                    "reviewer": "",
                    "metadata_status": "pending",
                    "structure_status": "pending",
                    "relation_status": "pending",
                    "overall_status": "pending",
                    "needs_manual_cleanup": "false",
                    "review_notes": "",
                }
            )


def _write_split_tasks(package_dir: Path, tasks: list[dict[str, Any]], *, chunk_size: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk-size must be positive")

    split_files: list[str] = []
    for index in range(0, len(tasks), chunk_size):
        part = tasks[index : index + chunk_size]
        part_number = (index // chunk_size) + 1
        file_name = f"label_studio_tasks_part_{part_number:02d}.json"
        (package_dir / file_name).write_text(json.dumps(part, ensure_ascii=False, indent=2), encoding="utf-8")
        split_files.append(file_name)
    return split_files


def _write_package_manifest(
    path: Path,
    *,
    source_manifest: Path,
    source_tasks: Path,
    generated_at: str,
    documents: list[dict[str, Any]],
    split_files: list[str],
) -> None:
    payload = {
        "schema_version": "annotation_trial_package.v1",
        "generated_at": generated_at,
        "source_manifest": str(source_manifest),
        "source_tasks": str(source_tasks),
        "document_count": len(documents),
        "split_files": split_files,
        "documents": [
            {
                "document_id": document.get("document_id"),
                "file_name": document.get("file_name"),
                "legal_domain": document.get("legal_domain"),
                "issue_codes": document.get("issue_codes"),
            }
            for document in documents
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_readme(path: Path, *, manifest: dict[str, Any], split_files: list[str], generated_at: str) -> None:
    summary = manifest.get("summary", {})
    lines = [
        "# LawChat-AI Annotation Trial Reviewer Package",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Contents",
        "",
        "- `selected_documents.csv`: selected document list with quality issues and selection scores.",
        "- `review_tracker.csv`: reviewer progress tracker. Fill this during legal review.",
        "- `package_manifest.json`: package metadata.",
        "- `label_studio_tasks_part_*.json`: split Label Studio import files.",
        "",
        "## Batch Summary",
        "",
        f"- Selected documents: `{summary.get('selected_count', 0)}`",
        f"- By domain: `{json.dumps(summary.get('by_domain', {}), ensure_ascii=False)}`",
        f"- Issue counts: `{json.dumps(summary.get('issue_counts', {}), ensure_ascii=False)}`",
        "",
        "## Import Order",
        "",
    ]
    lines.extend([f"{index}. Import `{file_name}` into the Label Studio project." for index, file_name in enumerate(split_files, start=1)])
    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- Verify metadata: title, document code, document type, issuing authority, effective date, legal status, and domain.",
            "- Verify structure labels: ARTICLE, CLAUSE, POINT, hierarchy path, citation label, and source excerpt.",
            "- Verify relation labels: source, target, relation type, and evidence excerpt.",
            "- Mark weak parser/OCR cases in `review_tracker.csv` with `needs_manual_cleanup=true`.",
            "- Export reviewed tasks from Label Studio after the first full pass.",
            "",
            "## Status Values",
            "",
            "Use `pending`, `verified`, `rejected`, or `needs_more_evidence` for metadata/structure/relation status columns.",
            "",
            "## After Review",
            "",
            "Return the Label Studio export JSON and the filled `review_tracker.csv` so LawChat can run import preview, save ground truth, and generate the post-review quality report.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
