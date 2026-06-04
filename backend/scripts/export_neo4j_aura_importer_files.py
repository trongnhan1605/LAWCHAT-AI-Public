from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.database import SessionLocal
from src.models.document import Document
from src.models.document_relation import DocumentRelation
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation


EXPORT_ROOT = BACKEND_ROOT / "exports" / "neo4j_aura_importer"


def write_csv(path: Path, header: list[str], rows: list[list[object | None]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = EXPORT_ROOT / timestamp
    export_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        documents = db.query(Document).filter(Document.is_active.is_(True)).order_by(Document.id.asc()).all()
        provisions = db.query(LegalProvision).filter(LegalProvision.is_active.is_(True)).order_by(LegalProvision.id.asc()).all()
        document_relations = db.query(DocumentRelation).filter(DocumentRelation.is_active.is_(True)).order_by(DocumentRelation.id.asc()).all()
        provision_relations = db.query(ProvisionRelation).filter(ProvisionRelation.is_active.is_(True)).order_by(ProvisionRelation.id.asc()).all()
    finally:
        db.close()

    write_csv(
        export_dir / "documents_aura.csv",
        [
            "document_id",
            "title",
            "document_code",
            "document_type",
            "issuing_authority",
            "legal_status",
            "legal_domain",
            "effective_date",
            "expiry_date",
            "node_label",
        ],
        [
            [
                item.id,
                item.title,
                item.document_code,
                item.document_type,
                item.issuing_authority,
                item.legal_status,
                item.legal_domain,
                item.effective_date.isoformat() if item.effective_date else None,
                item.expiry_date.isoformat() if item.expiry_date else None,
                "Document",
            ]
            for item in documents
        ],
    )

    write_csv(
        export_dir / "provisions_aura.csv",
        [
            "provision_id",
            "document_id",
            "parent_provision_id",
            "provision_level",
            "article_number",
            "clause_number",
            "point_code",
            "heading",
            "citation_label",
            "legal_status",
            "sort_key",
            "node_label",
        ],
        [
            [
                item.id,
                item.document_id,
                item.parent_provision_id,
                item.provision_level,
                item.article_number,
                item.clause_number,
                item.point_code,
                item.heading,
                item.citation_label,
                item.legal_status,
                item.sort_key,
                "Provision",
            ]
            for item in provisions
        ],
    )

    write_csv(
        export_dir / "document_has_provision_aura.csv",
        ["start_document_id", "end_provision_id", "type"],
        [[item.document_id, item.id, "HAS_PROVISION"] for item in provisions],
    )

    write_csv(
        export_dir / "provision_has_child_aura.csv",
        ["start_provision_id", "end_provision_id", "type"],
        [
            [item.parent_provision_id, item.id, "HAS_CHILD_PROVISION"]
            for item in provisions
            if item.parent_provision_id is not None
        ],
    )

    write_csv(
        export_dir / "document_relations_aura.csv",
        [
            "start_document_id",
            "end_document_id",
            "relation_id",
            "relation_type",
            "relation_label",
            "legal_basis",
            "confidence_score",
            "type",
        ],
        [
            [
                item.source_document_id,
                item.target_document_id,
                item.id,
                item.relation_type,
                item.relation_label,
                item.legal_basis,
                float(item.confidence_score) if item.confidence_score is not None else None,
                "RELATES_TO",
            ]
            for item in document_relations
        ],
    )

    write_csv(
        export_dir / "provision_relations_aura.csv",
        [
            "start_provision_id",
            "end_provision_id",
            "relation_id",
            "relation_type",
            "relation_label",
            "confidence_score",
            "extraction_method",
            "type",
        ],
        [
            [
                item.source_provision_id,
                item.target_provision_id,
                item.id,
                item.relation_type,
                item.relation_label,
                float(item.confidence_score) if item.confidence_score is not None else None,
                item.extraction_method,
                "PROVISION_RELATES_TO",
            ]
            for item in provision_relations
        ],
    )

    manifest = {
        "generated_at": timestamp,
        "documents": len(documents),
        "provisions": len(provisions),
        "document_relations": len(document_relations),
        "provision_relations": len(provision_relations),
        "files": [
            "documents_aura.csv",
            "provisions_aura.csv",
            "document_has_provision_aura.csv",
            "provision_has_child_aura.csv",
            "document_relations_aura.csv",
            "provision_relations_aura.csv",
        ],
    }
    (export_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = """Neo4j Aura Data Importer package for LawChat-AI

Recommended mapping in Aura Data Importer:

Nodes
1. documents_aura.csv -> label Document
   - ID field: document_id
2. provisions_aura.csv -> label Provision
   - ID field: provision_id

Relationships
1. document_has_provision_aura.csv
   - Document(document_id) -> Provision(provision_id)
   - type column: HAS_PROVISION
2. provision_has_child_aura.csv
   - Provision(provision_id) -> Provision(provision_id)
   - type column: HAS_CHILD_PROVISION
3. document_relations_aura.csv
   - Document(document_id) -> Document(document_id)
   - type column: RELATES_TO
4. provision_relations_aura.csv
   - Provision(provision_id) -> Provision(provision_id)
   - type column: PROVISION_RELATES_TO

Important:
- Do not use the old files with :ID(...) headers in Aura Data Importer.
- Use these *_aura.csv files instead.
"""
    (export_dir / "README.txt").write_text(readme, encoding="utf-8")

    print(export_dir)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
