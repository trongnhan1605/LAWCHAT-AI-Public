from __future__ import annotations

import argparse
from collections import Counter
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.services.annotation_import_service import annotation_import_service
from src.services.annotation_vendor_adapter_service import annotation_vendor_adapter_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Label Studio pre-label tasks can roundtrip into LawChat annotation import bundles without DB promotion.")
    parser.add_argument("--package-dir", type=Path, required=True, help="Reviewer package directory containing label_studio_tasks_part_*.json.")
    parser.add_argument("--output", type=Path, default=None, help="Output report JSON path.")
    parser.add_argument("--save-bundles", action="store_true", help="Save per-document import bundles for development inspection.")
    args = parser.parse_args()

    package_dir = args.package_dir
    output_path = args.output or settings.legal_sources_dir / f"annotation_trial_roundtrip_report_{datetime.now().strftime('%Y%m%d')}.json"
    bundle_dir = output_path.with_suffix("").parent / f"{output_path.with_suffix('').name}_bundles"

    tasks = _load_tasks(package_dir)
    items: list[dict[str, Any]] = []
    review_status_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    totals = Counter()

    if args.save_bundles:
        bundle_dir.mkdir(parents=True, exist_ok=True)

    for index, task in enumerate(tasks):
        payload = annotation_vendor_adapter_service.to_document_payload("label_studio", task)
        bundle = annotation_import_service.build_import_bundle(payload)
        summary = annotation_import_service.summarize(payload)
        review_status_counts[payload.review_status] += 1
        for entity in payload.entities:
            label_counts[entity.label] += 1
        for relation in payload.relations:
            relation_counts[relation.relation_type] += 1
        for warning in summary.warnings:
            warning_counts[warning] += 1
        totals["entities"] += summary.entity_count
        totals["relations"] += summary.relation_count
        totals["metadata_fields"] += len(summary.metadata_fields)
        totals["provisions"] += summary.provision_count
        totals["provision_relations"] += summary.provision_relation_count
        totals["semantic_entities"] += summary.semantic_entity_count
        totals["concept_candidates"] += len(bundle.concept_candidates)
        totals["norm_statements"] += len(bundle.norm_statements)

        item = {
            "index": index,
            "document_id": payload.document_id,
            "source_file_name": payload.source_file_name,
            "review_status": payload.review_status,
            "entity_count": summary.entity_count,
            "relation_count": summary.relation_count,
            "metadata_field_count": len(summary.metadata_fields),
            "metadata_fields": summary.metadata_fields,
            "provision_count": summary.provision_count,
            "provision_relation_count": summary.provision_relation_count,
            "semantic_entity_count": summary.semantic_entity_count,
            "concept_candidate_count": len(bundle.concept_candidates),
            "norm_statement_count": len(bundle.norm_statements),
            "warnings": summary.warnings,
            "dev_only": True,
            "trusted_ground_truth": False,
        }
        items.append(item)

        if args.save_bundles:
            bundle_path = bundle_dir / f"document_{payload.document_id or index}_import_bundle.json"
            bundle_path.write_text(
                json.dumps(
                    {
                        "document_id": payload.document_id,
                        "source_file_name": payload.source_file_name,
                        "review_status": payload.review_status,
                        "trusted_ground_truth": False,
                        "import_bundle": {
                            "metadata_fields": bundle.metadata_fields,
                            "provisions": bundle.provisions,
                            "provision_relations": bundle.provision_relations,
                            "semantic_entities": bundle.semantic_entities,
                            "concept_candidates": bundle.concept_candidates,
                            "norm_statements": bundle.norm_statements,
                            "warnings": bundle.warnings,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    report = {
        "schema_version": "annotation_trial_roundtrip_report.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "package_dir": str(package_dir),
        "dev_only": True,
        "trusted_ground_truth": False,
        "policy": [
            "This report validates machine pre-label roundtrip only.",
            "Do not mark documents reviewed or promote retrieval_visibility from this report.",
            "Legal reviewer approval is still required before using labels as ground truth.",
        ],
        "summary": {
            "task_count": len(tasks),
            "document_count": len({item.get("document_id") for item in items}),
            "review_status_counts": dict(sorted(review_status_counts.items())),
            "totals": dict(sorted(totals.items())),
            "label_counts": dict(sorted(label_counts.items())),
            "relation_counts": dict(sorted(relation_counts.items())),
            "warning_counts": dict(sorted(warning_counts.items())),
            "bundle_dir": str(bundle_dir) if args.save_bundles else None,
        },
        "items": items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "generated", "report": str(output_path), **report["summary"]}, ensure_ascii=False, indent=2))


def _load_tasks(package_dir: Path) -> list[dict[str, Any]]:
    task_files = sorted(package_dir.glob("label_studio_tasks_part_*.json"))
    if not task_files:
        raise FileNotFoundError(f"No label_studio_tasks_part_*.json files found in {package_dir}")

    tasks: list[dict[str, Any]] = []
    for task_file in task_files:
        raw = json.loads(task_file.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"Expected list in {task_file}")
        tasks.extend(raw)
    return tasks


if __name__ == "__main__":
    main()
