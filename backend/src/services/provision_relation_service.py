from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.services.legal_metadata_parser_service import legal_metadata_parser_service

ARTICLE_ONLY_PATTERN = re.compile(r"(?:điều|dieu|ieu)\s+(\d+[A-Za-z]*)", flags=re.IGNORECASE)
CLAUSE_ARTICLE_PATTERN = re.compile(r"(?:khoản|khoan|hoan)\s+(\d+)\s+(?:điều|dieu|ieu)\s+(\d+[A-Za-z]*)", flags=re.IGNORECASE)
POINT_CLAUSE_ARTICLE_PATTERN = re.compile(
    r"(?:điểm|diem|iem)\s+([a-zđ])\s+(?:khoản|khoan|hoan)\s+(\d+)\s+(?:điều|dieu|ieu)\s+(\d+[A-Za-z]*)",
    flags=re.IGNORECASE,
)


@dataclass(slots=True)
class ProvisionRelationSyncSummary:
    document_id: int
    created_relations: int
    relation_types: dict[str, int]


class ProvisionRelationService:
    def sync_document_relations(self, db: Session, document_id: int) -> ProvisionRelationSyncSummary:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError("Document not found for provision relation sync")

        db.query(ProvisionRelation).filter(ProvisionRelation.source_document_id == document_id).delete(synchronize_session=False)
        source_provisions = (
            db.query(LegalProvision)
            .filter(LegalProvision.document_id == document_id, LegalProvision.is_active.is_(True))
            .order_by(LegalProvision.sort_key.asc(), LegalProvision.id.asc())
            .all()
        )
        if not source_provisions:
            return ProvisionRelationSyncSummary(document_id=document_id, created_relations=0, relation_types={})

        active_documents = db.query(Document).filter(Document.is_active == True).all()
        relation_types: dict[str, int] = {}
        created_relations = 0
        seen_keys: set[tuple[int, int, str]] = set()

        for provision in source_provisions:
            target_document = self._resolve_target_document(db, provision.content, document, active_documents)
            references = self._extract_references(provision.content)
            for reference in references:
                target_provision = self._find_target_provision(
                    db=db,
                    document_id=target_document.id,
                    article_number=reference["article_number"],
                    clause_number=reference.get("clause_number"),
                    point_code=reference.get("point_code"),
                )
                if target_provision is None or target_provision.id == provision.id:
                    continue

                relation_type = self._classify_relation_type(provision.content)
                key = (provision.id, target_provision.id, relation_type)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                db.add(
                    ProvisionRelation(
                        source_document_id=document.id,
                        source_provision_id=provision.id,
                        target_document_id=target_document.id,
                        target_provision_id=target_provision.id,
                        relation_type=relation_type,
                        relation_label=self._build_relation_label(relation_type),
                        source_excerpt=self._build_provision_excerpt(provision),
                        target_excerpt=self._build_provision_excerpt(target_provision),
                        confidence_score=0.92,
                        extraction_method="rule-based",
                        metadata_json=json.dumps(
                            {
                                "source_citation_label": provision.citation_label,
                                "target_citation_label": target_provision.citation_label,
                            },
                            ensure_ascii=False,
                        ),
                        is_active=True,
                    )
                )
                created_relations += 1
                relation_types[relation_type] = relation_types.get(relation_type, 0) + 1

        db.flush()
        return ProvisionRelationSyncSummary(document_id=document_id, created_relations=created_relations, relation_types=relation_types)

    def list_document_relations(self, db: Session, document_id: int) -> list[ProvisionRelation]:
        return (
            db.query(ProvisionRelation)
            .filter(ProvisionRelation.source_document_id == document_id)
            .order_by(ProvisionRelation.source_provision_id.asc(), ProvisionRelation.id.asc())
            .all()
        )

    def clear_document_relations(self, db: Session, document_id: int) -> None:
        db.query(ProvisionRelation).filter(
            (ProvisionRelation.source_document_id == document_id) | (ProvisionRelation.target_document_id == document_id)
        ).delete(synchronize_session=False)
        db.flush()

    def _build_provision_excerpt(self, provision: LegalProvision) -> str | None:
        segments = [segment.strip() for segment in [provision.heading, provision.content] if segment and segment.strip()]
        if not segments:
            return None
        return "\n".join(segments)[:500]

    def _extract_references(self, content: str) -> list[dict[str, str | None]]:
        normalized_content = legal_metadata_parser_service.normalize_search_text(content)
        references: list[dict[str, str | None]] = []
        seen: set[tuple[str, str | None, str | None]] = set()

        for match in POINT_CLAUSE_ARTICLE_PATTERN.finditer(normalized_content):
            point_code, clause_number, article_number = match.groups()
            key = (article_number, clause_number, point_code)
            if key in seen:
                continue
            seen.add(key)
            references.append({"article_number": article_number, "clause_number": clause_number, "point_code": point_code})

        for match in CLAUSE_ARTICLE_PATTERN.finditer(normalized_content):
            clause_number, article_number = match.groups()
            key = (article_number, clause_number, None)
            if key in seen:
                continue
            if any(existing_article == article_number and existing_clause == clause_number and existing_point is not None for existing_article, existing_clause, existing_point in seen):
                continue
            seen.add(key)
            references.append({"article_number": article_number, "clause_number": clause_number, "point_code": None})

        for match in ARTICLE_ONLY_PATTERN.finditer(normalized_content):
            article_number = match.group(1)
            key = (article_number, None, None)
            if key in seen:
                continue
            if any(existing_article == article_number and (existing_clause is not None or existing_point is not None) for existing_article, existing_clause, existing_point in seen):
                continue
            seen.add(key)
            references.append({"article_number": article_number, "clause_number": None, "point_code": None})

        return references

    def _classify_relation_type(self, content: str) -> str:
        normalized = legal_metadata_parser_service.normalize_search_text(content)
        if "can cu" in normalized:
            return "LEGAL_BASIS_PROVISION"
        if "sua doi" in normalized:
            return "AMENDS_PROVISION"
        if "bo sung" in normalized:
            return "SUPPLEMENTS_PROVISION"
        return "CITES_PROVISION"

    def _build_relation_label(self, relation_type: str) -> str:
        mapping = {
            "LEGAL_BASIS_PROVISION": "Căn cứ điều khoản",
            "AMENDS_PROVISION": "Sửa đổi điều khoản",
            "SUPPLEMENTS_PROVISION": "Bổ sung điều khoản",
            "CITES_PROVISION": "Dẫn chiếu điều khoản",
        }
        return mapping.get(relation_type, relation_type)

    def _resolve_target_document(self, db: Session, content: str, source_document: Document, active_documents: list[Document]) -> Document:
        mentions = legal_metadata_parser_service.extract_citation_code_mentions(content)
        if len(mentions) != 1:
            return source_document

        mention_code = str(mentions[0]["code"])
        for candidate in active_documents:
            if candidate.id == source_document.id:
                continue
            aliases = legal_metadata_parser_service.code_aliases_for_document(file_name=candidate.file_name, document_code=candidate.document_code)
            normalized_aliases = {legal_metadata_parser_service.normalize_code(alias) for alias in aliases if alias}
            if mention_code in normalized_aliases:
                return candidate
        return source_document

    def _find_target_provision(
        self,
        *,
        db: Session,
        document_id: int,
        article_number: str,
        clause_number: str | None,
        point_code: str | None,
    ) -> LegalProvision | None:
        query = db.query(LegalProvision).filter(
            LegalProvision.document_id == document_id,
            LegalProvision.article_number == article_number,
            LegalProvision.is_active.is_(True),
        )
        if clause_number is not None:
            query = query.filter(LegalProvision.clause_number == clause_number)
        else:
            query = query.filter(LegalProvision.clause_number.is_(None))
        if point_code is not None:
            query = query.filter(LegalProvision.point_code == point_code)
        else:
            query = query.filter(LegalProvision.point_code.is_(None))
        return query.order_by(LegalProvision.sort_key.asc(), LegalProvision.id.asc()).first()


provision_relation_service = ProvisionRelationService()
