from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.schemas.annotation_schema import AnnotationDocumentPayload


METADATA_LABEL_TO_DOCUMENT_FIELD = {
    "DOCUMENT_TYPE": "document_type",
    "DOCUMENT_CODE": "document_code",
    "ISSUING_AUTHORITY": "issuing_authority",
    "SIGNED_DATE": "signed_date",
    "EFFECTIVE_DATE": "effective_date",
    "EXPIRY_DATE": "expiry_date",
    "LEGAL_STATUS": "legal_status",
    "LEGAL_DOMAIN": "legal_domain",
}

PROVISION_LABELS = {"ARTICLE", "CLAUSE", "POINT"}
CONCEPT_CANDIDATE_LABELS = {
    "SUBJECT",
    "LEGAL_OBJECT",
    "AUTHORITY",
    "PROCEDURE",
    "RIGHT",
    "OBLIGATION",
    "PROHIBITION",
    "PERMISSION",
}
SEMANTIC_LABELS = {"SUBJECT", "ACTION", "LEGAL_OBJECT", "CONDITION", "EXCEPTION", "CONSEQUENCE"}
RELATION_LABEL_TO_PROVISION_RELATION = {
    "LEGAL_BASIS": "LEGAL_BASIS_PROVISION",
    "AMENDS": "AMENDS_PROVISION",
    "SUPPLEMENTS": "SUPPLEMENTS_PROVISION",
    "GENERAL_REFERENCE": "CITES_PROVISION",
    "GUIDES": "GUIDES_PROVISION",
    "CONSOLIDATES": "CONSOLIDATES_PROVISION",
}
SEMANTIC_RELATION_LABELS = {
    "SUBJECT_OF",
    "ACTS_ON",
    "APPLIES_TO",
    "TRIGGERS",
    "HAS_CONDITION",
    "HAS_EXCEPTION",
    "HAS_CONSEQUENCE",
    "HAS_TIME",
    "HAS_LOCATION",
    "HAS_AMOUNT",
}
REVIEW_LABELS = {"UNCERTAIN_PARSE", "NEEDS_REVIEW", "AMBIGUOUS_REFERENCE", "LOW_OCR_QUALITY"}


@dataclass(slots=True)
class AnnotationImportSummary:
    vendor: str
    document_id: int | None
    source_file_name: str | None
    entity_count: int
    relation_count: int
    metadata_fields: dict[str, str]
    provision_count: int
    provision_relation_count: int
    semantic_entity_count: int
    warnings: list[str]


@dataclass(slots=True)
class AnnotationImportBundle:
    metadata_fields: dict[str, str]
    provisions: list[dict[str, object | None]]
    provision_relations: list[dict[str, object | None]]
    semantic_entities: list[dict[str, object | None]]
    concept_candidates: list[dict[str, object | None]]
    norm_statements: list[dict[str, object | None]]
    warnings: list[str]


class AnnotationImportService:
    def summarize(self, payload: AnnotationDocumentPayload) -> AnnotationImportSummary:
        bundle = self.build_import_bundle(payload)
        semantic_entity_count = sum(1 for item in payload.entities if item.label in SEMANTIC_LABELS)

        return AnnotationImportSummary(
            vendor=payload.vendor,
            document_id=payload.document_id,
            source_file_name=payload.source_file_name,
            entity_count=len(payload.entities),
            relation_count=len(payload.relations),
            metadata_fields=bundle.metadata_fields,
            provision_count=len(bundle.provisions),
            provision_relation_count=len(bundle.provision_relations),
            semantic_entity_count=semantic_entity_count,
            warnings=bundle.warnings,
        )

    def build_import_bundle(self, payload: AnnotationDocumentPayload) -> AnnotationImportBundle:
        warnings = self.collect_warnings(payload)
        provisions = self.build_provision_payloads(payload)
        return AnnotationImportBundle(
            metadata_fields=self.extract_document_metadata(payload),
            provisions=provisions,
            provision_relations=self.build_provision_relation_payloads(payload),
            semantic_entities=self.build_semantic_entity_payloads(payload),
            concept_candidates=self.build_concept_candidate_payloads(payload),
            norm_statements=self.build_norm_statement_payloads(payload),
            warnings=warnings,
        )

    def extract_document_metadata(self, payload: AnnotationDocumentPayload) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for entity in payload.entities:
            field_name = METADATA_LABEL_TO_DOCUMENT_FIELD.get(entity.label)
            if field_name is None:
                continue
            value = (entity.normalized_value or entity.text or "").strip()
            if value:
                metadata[field_name] = value
        return metadata

    def build_provision_payloads(self, payload: AnnotationDocumentPayload) -> list[dict[str, object | None]]:
        provisions: list[dict[str, object | None]] = []
        sorted_entities = sorted(
            (item for item in payload.entities if item.label in PROVISION_LABELS),
            key=lambda item: (item.start if item.start is not None else 10**9, item.id),
        )
        provision_id_by_entity: dict[str, int] = {}
        current_article_index: int | None = None
        current_clause_index: int | None = None

        for entity in sorted_entities:
            provision_level = entity.label.lower()
            attributes = entity.attributes or {}
            heading = str(attributes.get("heading") or entity.normalized_value or entity.text).strip() or None
            content = str(attributes.get("content") or entity.text).strip()
            article_number = self._string_or_none(attributes.get("article_number"))
            clause_number = self._string_or_none(attributes.get("clause_number"))
            point_code = self._string_or_none(attributes.get("point_code"))

            parent_index: int | None = None
            if provision_level == "article":
                current_article_index = len(provisions) + 1
                current_clause_index = None
            elif provision_level == "clause":
                parent_index = current_article_index
                current_clause_index = len(provisions) + 1
            elif provision_level == "point":
                parent_index = current_clause_index or current_article_index

            citation_parts = []
            if article_number:
                citation_parts.append(f"Điều {article_number}")
            if clause_number:
                citation_parts.insert(0, f"Khoản {clause_number}")
            if point_code:
                citation_parts.insert(0, f"Điểm {point_code}")
            citation_label = " ".join(citation_parts) or heading or entity.text[:255]

            payload_item = {
                "parent_provision_id": parent_index,
                "provision_level": provision_level,
                "article_number": article_number,
                "clause_number": clause_number,
                "point_code": point_code,
                "heading": heading[:500] if heading else None,
                "content": content,
                "citation_label": citation_label[:255],
                "sort_key": self._build_sort_key(article_number, clause_number, point_code, len(provisions) + 1),
                "metadata_json": (
                    '{"annotation_vendor":"%s","annotation_entity_id":"%s"}' % (payload.vendor, entity.id)
                ),
            }
            provisions.append(payload_item)
            provision_id_by_entity[entity.id] = len(provisions)

        return provisions

    def build_provision_relation_payloads(self, payload: AnnotationDocumentPayload) -> list[dict[str, object | None]]:
        provision_entity_ids = {item.id for item in payload.entities if item.label in PROVISION_LABELS}
        relation_payloads: list[dict[str, object | None]] = []

        for relation in payload.relations:
            mapped_relation_type = RELATION_LABEL_TO_PROVISION_RELATION.get(relation.relation_type)
            if mapped_relation_type is None:
                continue
            if relation.source_entity_id not in provision_entity_ids or relation.target_entity_id not in provision_entity_ids:
                continue
            relation_payloads.append(
                {
                    "relation_type": mapped_relation_type,
                    "source_entity_id": relation.source_entity_id,
                    "target_entity_id": relation.target_entity_id,
                    "confidence_score": relation.confidence_score,
                    "attributes": relation.attributes,
                }
            )

        return relation_payloads

    def build_semantic_entity_payloads(self, payload: AnnotationDocumentPayload) -> list[dict[str, object | None]]:
        semantic_entities: list[dict[str, object | None]] = []
        for entity in payload.entities:
            if entity.label not in SEMANTIC_LABELS and entity.label not in CONCEPT_CANDIDATE_LABELS:
                continue
            semantic_entities.append(
                {
                    "annotation_entity_id": entity.id,
                    "label": entity.label,
                    "text": entity.text.strip(),
                    "normalized_value": self._string_or_none(entity.normalized_value) or entity.text.strip(),
                    "start": entity.start,
                    "end": entity.end,
                    "attributes": entity.attributes,
                }
            )
        return semantic_entities

    def build_concept_candidate_payloads(self, payload: AnnotationDocumentPayload) -> list[dict[str, object | None]]:
        concept_candidates: list[dict[str, object | None]] = []
        for entity in payload.entities:
            if entity.label not in CONCEPT_CANDIDATE_LABELS:
                continue
            concept_candidates.append(
                {
                    "annotation_entity_id": entity.id,
                    "candidate_name": self._string_or_none(entity.normalized_value) or entity.text.strip(),
                    "source_label": entity.label,
                    "concept_type_hint": self._map_label_to_concept_type(entity.label),
                    "attributes": entity.attributes,
                }
            )
        return concept_candidates

    def build_norm_statement_payloads(self, payload: AnnotationDocumentPayload) -> list[dict[str, object | None]]:
        entity_by_id = {item.id: item for item in payload.entities}
        norm_statements: list[dict[str, object | None]] = []

        for relation in payload.relations:
            if relation.relation_type not in SEMANTIC_RELATION_LABELS:
                continue
            source = entity_by_id.get(relation.source_entity_id)
            target = entity_by_id.get(relation.target_entity_id)
            if source is None or target is None:
                continue
            norm_statements.append(
                {
                    "annotation_relation_id": relation.id,
                    "relation_type": relation.relation_type,
                    "source_entity_id": source.id,
                    "source_label": source.label,
                    "source_text": source.text.strip(),
                    "target_entity_id": target.id,
                    "target_label": target.label,
                    "target_text": target.text.strip(),
                    "confidence_score": relation.confidence_score,
                    "attributes": relation.attributes,
                }
            )
        return norm_statements

    def collect_warnings(self, payload: AnnotationDocumentPayload) -> list[str]:
        warnings: list[str] = []
        entity_ids = {item.id for item in payload.entities}
        dangling_relations = [
            relation.id
            for relation in payload.relations
            if relation.source_entity_id not in entity_ids or relation.target_entity_id not in entity_ids
        ]
        if dangling_relations:
            warnings.append(f"Dangling relations detected: {', '.join(dangling_relations[:10])}")

        review_entities = [entity.id for entity in payload.entities if entity.label in REVIEW_LABELS]
        if review_entities:
            warnings.append(f"Review-required labels detected: {', '.join(review_entities[:10])}")

        if not any(entity.label in PROVISION_LABELS for entity in payload.entities):
            warnings.append("No ARTICLE/CLAUSE/POINT labels found in annotation payload")

        return warnings

    def _build_sort_key(
        self,
        article_number: str | None,
        clause_number: str | None,
        point_code: str | None,
        sequence_index: int,
    ) -> str:
        return "|".join(
            [
                article_number or "0000",
                clause_number or "0000",
                point_code or "00",
                f"{sequence_index:06d}",
            ]
        )

    def _string_or_none(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _map_label_to_concept_type(self, label: str) -> str:
        return {
            "SUBJECT": "entity_type",
            "LEGAL_OBJECT": "asset",
            "AUTHORITY": "authority",
            "PROCEDURE": "procedure",
            "RIGHT": "right",
            "OBLIGATION": "obligation",
            "PROHIBITION": "prohibition",
            "PERMISSION": "permission",
        }.get(label, "concept")


annotation_import_service = AnnotationImportService()
