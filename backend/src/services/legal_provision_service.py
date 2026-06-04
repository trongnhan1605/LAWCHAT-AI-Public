from __future__ import annotations

from sqlalchemy import delete, update
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.services.legal_provision_parser_service import legal_provision_parser_service


class LegalProvisionService:
    def sync_document_provisions(self, db: Session, document: Document, extracted_text: str) -> int:
        payloads = legal_provision_parser_service.build_document_payloads(document_id=document.id, text=extracted_text)
        return self.sync_document_provisions_from_payloads(db, document, payloads)

    def sync_document_provisions_from_payloads(self, db: Session, document: Document, payloads: list[dict[str, object | None]]) -> int:
        self.clear_document_provisions(db, document.id)
        if not payloads:
            return 0

        temp_id_to_created_id: dict[int, int] = {}
        created_count = 0

        for index, payload in enumerate(payloads, start=1):
            parent_index = payload.pop("parent_provision_id", None)
            provision = LegalProvision(
                document_id=document.id,
                parent_provision_id=temp_id_to_created_id.get(parent_index) if isinstance(parent_index, int) else None,
                provision_level=payload["provision_level"],
                article_number=payload["article_number"],
                clause_number=payload["clause_number"],
                point_code=payload["point_code"],
                heading=payload["heading"],
                content=payload["content"],
                citation_label=payload["citation_label"],
                sort_key=payload["sort_key"],
                effective_from=document.effective_date,
                effective_to=document.expiry_date,
                legal_status=document.legal_status,
                metadata_json=payload["metadata_json"],
            )
            db.add(provision)
            db.flush()
            temp_id_to_created_id[index] = provision.id
            created_count += 1

        return created_count

    def clear_document_provisions(self, db: Session, document_id: int) -> None:
        provision_ids = [
            provision_id
            for (provision_id,) in db.query(LegalProvision.id).filter(LegalProvision.document_id == document_id).all()
        ]
        if provision_ids:
            db.execute(
                delete(ProvisionRelation).where(
                    (ProvisionRelation.source_provision_id.in_(provision_ids))
                    | (ProvisionRelation.target_provision_id.in_(provision_ids))
                    | (ProvisionRelation.source_document_id == document_id)
                    | (ProvisionRelation.target_document_id == document_id)
                )
            )
            db.flush()
        db.execute(
            update(LegalProvision)
            .where(LegalProvision.document_id == document_id)
            .values(parent_provision_id=None)
        )
        db.flush()
        provisions = (
            db.query(LegalProvision)
            .filter(LegalProvision.document_id == document_id)
            .order_by(desc(LegalProvision.sort_key), desc(LegalProvision.id))
            .all()
        )
        for provision in provisions:
            db.delete(provision)
        db.flush()


legal_provision_service = LegalProvisionService()
