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


EXPORT_ROOT = BACKEND_ROOT / "exports" / "neo4j_import"


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

    documents_rows = [
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
    ]
    write_csv(
        export_dir / "documents.csv",
        [
            "document_id:ID(Document)",
            "title",
            "document_code",
            "document_type",
            "issuing_authority",
            "legal_status",
            "legal_domain",
            "effective_date",
            "expiry_date",
            ":LABEL",
        ],
        documents_rows,
    )

    provisions_rows = [
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
    ]
    write_csv(
        export_dir / "provisions.csv",
        [
            "provision_id:ID(Provision)",
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
            ":LABEL",
        ],
        provisions_rows,
    )

    has_provision_rows = [[item.document_id, item.id, "HAS_PROVISION"] for item in provisions]
    write_csv(
        export_dir / "document_has_provision.csv",
        [
            ":START_ID(Document)",
            ":END_ID(Provision)",
            ":TYPE",
        ],
        has_provision_rows,
    )

    child_provision_rows = [
        [item.parent_provision_id, item.id, "HAS_CHILD_PROVISION"]
        for item in provisions
        if item.parent_provision_id is not None
    ]
    write_csv(
        export_dir / "provision_has_child.csv",
        [
            ":START_ID(Provision)",
            ":END_ID(Provision)",
            ":TYPE",
        ],
        child_provision_rows,
    )

    document_relation_rows = [
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
    ]
    write_csv(
        export_dir / "document_relations.csv",
        [
            ":START_ID(Document)",
            ":END_ID(Document)",
            "relation_id",
            "relation_type",
            "relation_label",
            "legal_basis",
            "confidence_score:float",
            ":TYPE",
        ],
        document_relation_rows,
    )

    provision_relation_rows = [
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
    ]
    write_csv(
        export_dir / "provision_relations.csv",
        [
            ":START_ID(Provision)",
            ":END_ID(Provision)",
            "relation_id",
            "relation_type",
            "relation_label",
            "confidence_score:float",
            "extraction_method",
            ":TYPE",
        ],
        provision_relation_rows,
    )

    manifest = {
        "generated_at": timestamp,
        "documents": len(documents_rows),
        "provisions": len(provisions_rows),
        "document_has_provision": len(has_provision_rows),
        "provision_has_child": len(child_provision_rows),
        "document_relations": len(document_relation_rows),
        "provision_relations": len(provision_relation_rows),
        "files": [
            "documents.csv",
            "provisions.csv",
            "document_has_provision.csv",
            "provision_has_child.csv",
            "document_relations.csv",
            "provision_relations.csv",
        ],
    }
    (export_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = """Neo4j import package for LawChat-AI

Files:
- documents.csv
- provisions.csv
- document_has_provision.csv
- provision_has_child.csv
- document_relations.csv
- provision_relations.csv

Recommended import path:
1. Open Neo4j Data Importer or Aura import UI.
2. Upload all CSV files in this folder.
3. Map nodes:
   - documents.csv -> Document
   - provisions.csv -> Provision
4. Map relationships:
   - document_has_provision.csv -> HAS_PROVISION
   - provision_has_child.csv -> HAS_CHILD_PROVISION
   - document_relations.csv -> RELATES_TO
   - provision_relations.csv -> PROVISION_RELATES_TO
5. Import.

Notes:
- This package is exported from PostgreSQL source-of-truth.
- IDs are stable database IDs from LawChat-AI.
"""
    (export_dir / "README.txt").write_text(readme, encoding="utf-8")

    print(export_dir)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
