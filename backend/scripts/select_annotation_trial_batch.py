from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.core.database import SessionLocal
from src.services.annotation_import_service import annotation_import_service
from src.services.annotation_prelabel_service import annotation_prelabel_service
from src.services.corpus_quality_report_service import corpus_quality_report_service

TARGET_GROUPS = {
    "dat-dai": 10,
    "hon-nhan-va-gia-dinh": 10,
    "lao-dong": 8,
}

ISSUE_WEIGHTS = {
    "low_ocr_quality": 80,
    "ingestion_blocked": 80,
    "retrieval_blocked": 80,
    "relation_missing_evidence": 70,
    "document_code_year_mismatch_filename": 45,
    "legal_status_not_authoritative": 35,
    "missing_document_code": 30,
    "missing_document_type": 30,
    "missing_authority_level": 30,
    "missing_issuing_authority": 30,
    "missing_legal_status": 30,
    "no_structured_provisions": 25,
    "provision_chunk_ratio_high": 20,
    "metadata_pending_review": 10,
    "ingestion_review_required": 10,
    "retrieval_unreviewed": 10,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Select LawChat-AI annotation trial batch from the current corpus.")
    parser.add_argument("--size", type=int, default=30, help="Total number of documents to select.")
    parser.add_argument("--hard-cases", type=int, default=2, help="Number of extra highest-risk documents after domain quotas.")
    parser.add_argument("--output", type=Path, default=None, help="Manifest JSON output path.")
    parser.add_argument("--tasks-output", type=Path, default=None, help="Optional Label Studio tasks JSON output path.")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y%m%d")
    output_path = args.output or settings.legal_sources_dir / f"annotation_trial_batch_{today}.json"
    tasks_output_path = args.tasks_output or settings.legal_sources_dir / f"annotation_trial_batch_{today}_label_studio_tasks.json"

    with SessionLocal() as db:
        report = corpus_quality_report_service.build_report(db, include_reviewed=False)
        items = list(report["items"])
        selected = select_batch(items, size=args.size, hard_cases=args.hard_cases)
        tasks = build_label_studio_tasks(db, selected)

    manifest = {
        "schema_version": "annotation_trial_batch.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "selection_policy": {
            "total_size": args.size,
            "domain_targets": TARGET_GROUPS,
            "hard_cases": args.hard_cases,
            "score_weights": ISSUE_WEIGHTS,
            "notes": [
                "The current DB uses legal_domain values dat-dai, hon-nhan-va-gia-dinh, and lao-dong.",
                "The lao-dong quota is used as the operational proxy for the VBQPPL bucket when original source folder labels are not persisted.",
                "All selected documents remain pre-review candidates until a legal reviewer confirms metadata, provisions, and relations.",
            ],
        },
        "summary": summarize_selection(selected),
        "documents": selected,
        "label_studio_tasks_file": str(tasks_output_path),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tasks_output_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_output_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "generated", "manifest": str(output_path), "tasks": str(tasks_output_path), **manifest["summary"]}, ensure_ascii=False, indent=2))


def select_batch(items: list[dict[str, Any]], *, size: int, hard_cases: int) -> list[dict[str, Any]]:
    candidates = [_with_selection_score(item) for item in items]
    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()

    for domain, target_count in TARGET_GROUPS.items():
        domain_candidates = [item for item in candidates if item.get("legal_domain") == domain]
        for item in sorted(domain_candidates, key=_sort_key)[:target_count]:
            _append_selected(selected, selected_ids, item, f"domain_quota:{domain}")

    remaining = [item for item in candidates if int(item["document_id"]) not in selected_ids]
    for item in sorted(remaining, key=_sort_key)[:hard_cases]:
        _append_selected(selected, selected_ids, item, "hard_case")

    remaining = [item for item in candidates if int(item["document_id"]) not in selected_ids]
    for item in sorted(remaining, key=_sort_key):
        if len(selected) >= size:
            break
        _append_selected(selected, selected_ids, item, "fill")

    return selected[:size]


def build_label_studio_tasks(db, selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for item in selected:
        document_id = int(item["document_id"])
        try:
            payload = annotation_prelabel_service.build_document_payload(db, document_id)
            task = annotation_prelabel_service.build_label_studio_task(payload)
            summary = annotation_import_service.summarize(payload)
            task["data"]["selection_reason"] = item["selection_reason"]
            task["data"]["quality_issues"] = item["issue_codes"]
            task["data"]["risk_level"] = item["risk_level"]
            task["data"]["import_summary"] = {
                "entity_count": summary.entity_count,
                "relation_count": summary.relation_count,
                "provision_count": summary.provision_count,
                "provision_relation_count": summary.provision_relation_count,
                "semantic_entity_count": summary.semantic_entity_count,
                "warnings": summary.warnings,
            }
            tasks.append(task)
        except Exception as exc:
            tasks.append(
                {
                    "data": {
                        "document_id": document_id,
                        "source_file_name": item.get("file_name"),
                        "selection_reason": item["selection_reason"],
                        "quality_issues": item["issue_codes"],
                        "export_error": str(exc),
                    },
                    "predictions": [],
                }
            )
    return tasks


def summarize_selection(selected: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    issue_counts: dict[str, int] = {}
    for item in selected:
        by_domain[str(item.get("legal_domain"))] = by_domain.get(str(item.get("legal_domain")), 0) + 1
        by_reason[item["selection_reason"]] = by_reason.get(item["selection_reason"], 0) + 1
        for issue in item["issue_codes"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    return {
        "selected_count": len(selected),
        "by_domain": dict(sorted(by_domain.items())),
        "by_selection_reason": dict(sorted(by_reason.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
    }


def _with_selection_score(item: dict[str, Any]) -> dict[str, Any]:
    issue_codes = [str(issue) for issue in item.get("issue_codes", [])]
    score = sum(ISSUE_WEIGHTS.get(issue, 5) for issue in issue_codes)
    score += min(int(item.get("document_relation_count", 0) or 0), 20)
    score += min(int(item.get("provision_relation_count", 0) or 0) // 5, 25)
    score += min(int(item.get("provision_count", 0) or 0) // 200, 20)
    if item.get("risk_level") == "high":
        score += 100
    normalized = dict(item)
    normalized["selection_score"] = score
    normalized["issue_codes"] = issue_codes
    return normalized


def _sort_key(item: dict[str, Any]) -> tuple[int, int]:
    return (-int(item["selection_score"]), -int(item["document_id"]))


def _append_selected(selected: list[dict[str, Any]], selected_ids: set[int], item: dict[str, Any], reason: str) -> None:
    document_id = int(item["document_id"])
    if document_id in selected_ids:
        return
    selected_ids.add(document_id)
    output_item = {
        key: item.get(key)
        for key in (
            "document_id",
            "title",
            "file_name",
            "source_reference",
            "document_code",
            "document_type",
            "legal_domain",
            "authority_level",
            "issuing_authority",
            "signed_date",
            "effective_date",
            "legal_status",
            "metadata_review_status",
            "ingestion_quality_status",
            "retrieval_visibility",
            "ocr_quality_label",
            "ocr_quality_score",
            "chunk_count",
            "provision_count",
            "document_relation_count",
            "provision_relation_count",
            "risk_level",
            "issue_codes",
            "recommendations",
            "selection_score",
        )
    }
    output_item["selection_reason"] = reason
    selected.append(output_item)


if __name__ == "__main__":
    main()
