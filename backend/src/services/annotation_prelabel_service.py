from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.schemas.annotation_schema import (
    AnnotationDocumentPayload,
    AnnotationEntityPayload,
    AnnotationRelationPayload,
)


METADATA_FIELD_TO_LABEL = {
    "document_type": ("DOCUMENT_TYPE", "Loai van ban"),
    "document_code": ("DOCUMENT_CODE", "So ky hieu"),
    "issuing_authority": ("ISSUING_AUTHORITY", "Co quan ban hanh"),
    "signed_date": ("SIGNED_DATE", "Ngay ky"),
    "effective_date": ("EFFECTIVE_DATE", "Ngay hieu luc"),
    "expiry_date": ("EXPIRY_DATE", "Ngay het hieu luc"),
    "legal_status": ("LEGAL_STATUS", "Tinh trang hieu luc"),
    "legal_domain": ("LEGAL_DOMAIN", "Linh vuc"),
}
PROVISION_LEVEL_TO_LABEL = {
    "article": "ARTICLE",
    "clause": "CLAUSE",
    "point": "POINT",
}
PROVISION_RELATION_TYPE_TO_LABEL = {
    "LEGAL_BASIS_PROVISION": "LEGAL_BASIS",
    "AMENDS_PROVISION": "AMENDS",
    "SUPPLEMENTS_PROVISION": "SUPPLEMENTS",
    "CITES_PROVISION": "GENERAL_REFERENCE",
    "GUIDES_PROVISION": "GUIDES",
    "CONSOLIDATES_PROVISION": "CONSOLIDATES",
}
SUBJECT_PATTERNS = (
    re.compile(
        r"(?P<match>\b(?:Cơ quan|Co quan|Tổ chức|To chuc|Cá nhân|Ca nhan|Người\s+[A-ZÀ-Ỵa-zà-ỹ][^,.;:\n]{0,120}|Nguoi\s+[A-ZA-Za-z][^,.;:\n]{0,120}|Nhà đầu tư[^,.;:\n]{0,120}|Nha dau tu[^,.;:\n]{0,120}|Doanh nghiệp[^,.;:\n]{0,120}|Doanh nghiep[^,.;:\n]{0,120}|Ủy ban nhân dân[^,.;:\n]{0,120}|Uy ban nhan dan[^,.;:\n]{0,120}|Bộ trưởng[^,.;:\n]{0,120}|Bo truong[^,.;:\n]{0,120}|Chủ đầu tư[^,.;:\n]{0,120}|Chu dau tu[^,.;:\n]{0,120})\b)",
        re.UNICODE,
    ),
)
ACTION_PATTERNS = (
    re.compile(r"(?P<match>\bkhông được\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhong duoc\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bđược quyền\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bduoc quyen\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bcó quyền\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bco quyen\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bcó trách nhiệm\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bco trach nhiem\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bphải\b)", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bphai\b)", re.IGNORECASE | re.UNICODE),
    re.compile(
        r"(?P<match>\b(?:thực hiện|thuc hien|nộp|nop|đăng ký|dang ky|cấp|cap|thu hồi|thu hoi|sử dụng|su dung|quản lý|quan ly|thanh toán|thanh toan|bồi thường|boi thuong|chấm dứt|cham dut|chuyển nhượng|chuyen nhuong|giao|cho thuê|cho thue)\b)",
        re.IGNORECASE | re.UNICODE,
    ),
)
CONDITION_PATTERNS = (
    re.compile(r"(?P<match>\btrường hợp\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\btruong hop\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bnếu\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bneu\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
)
EXCEPTION_PATTERNS = (
    re.compile(r"(?P<match>\btrừ trường hợp\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\btru truong hop\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\btrừ khi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\btru khi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhông áp dụng đối với\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhong ap dung doi voi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
)
CONSEQUENCE_PATTERNS = (
    re.compile(r"(?P<match>\bsẽ bị\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bse bi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bbị\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bbi\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhông có giá trị\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
    re.compile(r"(?P<match>\bkhong co gia tri\b[^.;:\n]{0,180})", re.IGNORECASE | re.UNICODE),
)
LEGAL_OBJECT_PATTERNS = (
    re.compile(
        r"(?:phải|phai|được|duoc|không được|khong duoc|có quyền|co quyen|được quyền|duoc quyen|thực hiện|thuc hien|nộp|nop|đăng ký|dang ky|cấp|cap|thu hồi|thu hoi|sử dụng|su dung|quản lý|quan ly|thanh toán|thanh toan|bồi thường|boi thuong)\s+(?P<match>[^.;:\n]{5,180})",
        re.IGNORECASE | re.UNICODE,
    ),
)


@dataclass(slots=True)
class _TextAssembler:
    chunks: list[str]
    cursor: int = 0

    def add_line(self, text: str = "") -> tuple[int, int]:
        start = self.cursor
        self.chunks.append(text)
        self.chunks.append("\n")
        self.cursor += len(text) + 1
        return start, start + len(text)

    def build(self) -> str:
        return "".join(self.chunks).rstrip("\n")


@dataclass(slots=True)
class _ChunkTextSpan:
    chunk_id: int
    article_number: str | None
    clause_number: str | None
    point_number: str | None
    start: int
    end: int
    text: str


@dataclass(slots=True)
class _SemanticMatch:
    label: str
    text: str
    start: int
    end: int
    provenance: str


class AnnotationPrelabelService:
    def build_document_payload(self, db: Session, document_id: int) -> AnnotationDocumentPayload:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        provisions = (
            db.query(LegalProvision)
            .filter(LegalProvision.document_id == document_id, LegalProvision.is_active.is_(True))
            .order_by(LegalProvision.sort_key.asc(), LegalProvision.id.asc())
            .all()
        )
        relations = (
            db.query(ProvisionRelation)
            .filter(ProvisionRelation.source_document_id == document_id, ProvisionRelation.is_active.is_(True))
            .order_by(ProvisionRelation.id.asc())
            .all()
        )
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
            .all()
        )
        return self._build_payload_from_records(document, chunks, provisions, relations)

    def build_label_studio_task(self, payload: AnnotationDocumentPayload) -> dict[str, object]:
        results: list[dict[str, object]] = []
        exportable_entity_ids: set[str] = set()
        for entity in payload.entities:
            if entity.start is None or entity.end is None:
                continue
            result_item = {
                "id": entity.id,
                "type": "labels",
                "from_name": "label",
                "to_name": "text",
                "value": {
                    "start": entity.start or 0,
                    "end": entity.end or 0,
                    "text": entity.text,
                    "labels": [entity.label],
                },
            }
            for key, value in (entity.attributes or {}).items():
                if key != "prediction_score":
                    result_item["value"][key] = value
            prediction_score = (entity.attributes or {}).get("prediction_score")
            if prediction_score is not None:
                result_item["score"] = prediction_score
            results.append(result_item)
            exportable_entity_ids.add(entity.id)

        for relation in payload.relations:
            if relation.source_entity_id not in exportable_entity_ids or relation.target_entity_id not in exportable_entity_ids:
                continue
            result_item = {
                "id": relation.id,
                "type": "relation",
                "from_id": relation.source_entity_id,
                "to_id": relation.target_entity_id,
                "labels": [relation.relation_type],
            }
            if relation.confidence_score is not None:
                result_item["score"] = relation.confidence_score
            if relation.attributes:
                result_item["value"] = relation.attributes
            results.append(result_item)

        text_value = self._extract_text_from_payload(payload)
        return {
            "data": {
                "document_id": payload.document_id,
                "source_file_name": payload.source_file_name,
                "language": payload.language,
                "text": text_value,
                "metadata_prelabels": self._build_metadata_prelabels(payload),
            },
            "predictions": [
                {
                    "model_version": "LawChat-structure-prelabel-v2",
                    "result": results,
                }
            ],
        }

    def _build_metadata_prelabels(self, payload: AnnotationDocumentPayload) -> list[dict[str, object]]:
        metadata_labels = {label for label, _display_name in METADATA_FIELD_TO_LABEL.values()}
        prelabels: list[dict[str, object]] = []
        for entity in payload.entities:
            if entity.label not in metadata_labels:
                continue
            prelabels.append(
                {
                    "id": entity.id,
                    "label": entity.label,
                    "text": entity.text,
                    "normalized_value": entity.normalized_value or entity.text,
                    "attributes": entity.attributes,
                }
            )
        return prelabels

    def _build_payload_from_records(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        provisions: list[LegalProvision],
        relations: list[ProvisionRelation],
    ) -> AnnotationDocumentPayload:
        source_text, chunk_spans = self._build_source_text(chunks, provisions)
        entities: list[AnnotationEntityPayload] = []
        relation_payloads: list[AnnotationRelationPayload] = []

        metadata_entity_count = 0
        for field_name, (label, display_name) in METADATA_FIELD_TO_LABEL.items():
            raw_value = getattr(document, field_name, None)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if not value:
                continue
            metadata_entity_count += 1
            entities.append(
                AnnotationEntityPayload(
                    id=f"meta-{document.id}-{metadata_entity_count}",
                    label=label,
                    text=value,
                    attributes={
                        "source": "LawChat_metadata",
                        "display_name": display_name,
                        "prediction_provenance": "metadata",
                        "review_mode": "structured_field",
                    },
                )
            )

        provision_entity_ids: dict[int, str] = {}
        for provision in provisions:
            label = PROVISION_LEVEL_TO_LABEL.get((provision.provision_level or "").lower())
            if label is None:
                continue
            preferred_chunks = self._pick_candidate_chunks(chunk_spans, provision)
            anchor_start, anchor_end, span_text, anchor_attributes = self._anchor_provision_text(
                source_text=source_text,
                chunk_spans=preferred_chunks,
                provision=provision,
            )
            entity_id = f"prov-{provision.id}"
            provision_entity_ids[provision.id] = entity_id
            entities.append(
                AnnotationEntityPayload(
                    id=entity_id,
                    label=label,
                    text=span_text,
                    start=anchor_start,
                    end=anchor_end,
                    attributes={
                        "article_number": provision.article_number,
                        "clause_number": provision.clause_number,
                        "point_code": provision.point_code,
                        "heading": provision.heading,
                        "content": provision.content,
                        "citation_label": provision.citation_label,
                        "source": "LawChat_parser",
                        "prediction_provenance": "parser",
                        **anchor_attributes,
                    },
                )
            )
            semantic_entities, semantic_relations = self._build_semantic_prelabels_for_provision(
                provision=provision,
                preferred_chunks=preferred_chunks,
            )
            entities.extend(semantic_entities)
            relation_payloads.extend(semantic_relations)

        for relation in relations:
            relation_label = PROVISION_RELATION_TYPE_TO_LABEL.get(relation.relation_type)
            source_entity_id = provision_entity_ids.get(relation.source_provision_id)
            target_entity_id = provision_entity_ids.get(relation.target_provision_id)
            if relation_label is None or source_entity_id is None or target_entity_id is None:
                continue
            relation_payloads.append(
                AnnotationRelationPayload(
                    id=f"rel-{relation.id}",
                    relation_type=relation_label,
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    confidence_score=float(relation.confidence_score) if relation.confidence_score is not None else None,
                    attributes={
                        "source_excerpt": relation.source_excerpt,
                        "target_excerpt": relation.target_excerpt,
                        "relation_label": relation.relation_label,
                        "extraction_method": relation.extraction_method,
                        "source": "LawChat_relation_parser",
                        "prediction_provenance": relation.extraction_method or "relation_parser",
                    },
                )
            )

        payload = AnnotationDocumentPayload(
            document_id=document.id,
            vendor="internal_structure_prelabel",
            source_file_name=document.file_name,
            source_text=source_text,
            language="vi",
            review_status="predicted",
            entities=entities,
            relations=relation_payloads,
        )
        return payload

    def _extract_text_from_payload(self, payload: AnnotationDocumentPayload) -> str:
        if payload.source_text:
            return payload.source_text
        ordered_entities = sorted(
            (item for item in payload.entities if item.start is not None),
            key=lambda item: (item.start or 0, item.end or 0, item.id),
        )
        return "\n".join(item.text for item in ordered_entities)

    def _build_source_text(
        self,
        chunks: list[DocumentChunk],
        provisions: list[LegalProvision],
    ) -> tuple[str, list[_ChunkTextSpan]]:
        if chunks:
            assembler = _TextAssembler(chunks=[])
            chunk_spans: list[_ChunkTextSpan] = []
            for index, chunk in enumerate(chunks):
                rendered_text = self._render_chunk_text(chunk)
                if not rendered_text:
                    continue
                start, end = assembler.add_line(rendered_text)
                if index < len(chunks) - 1:
                    assembler.add_line()
                chunk_spans.append(
                    _ChunkTextSpan(
                        chunk_id=chunk.id,
                        article_number=self._normalize_number(chunk.article_number),
                        clause_number=self._normalize_number(chunk.clause_number),
                        point_number=self._normalize_number(chunk.point_number),
                        start=start,
                        end=end,
                        text=rendered_text,
                    )
                )
            return assembler.build(), chunk_spans

        assembler = _TextAssembler(chunks=[])
        fallback_spans: list[_ChunkTextSpan] = []
        for provision in provisions:
            content_text = (provision.content or "").strip().replace("\r", " ").replace("\n", " ")
            if not content_text:
                continue
            start, end = assembler.add_line(content_text)
            assembler.add_line()
            fallback_spans.append(
                _ChunkTextSpan(
                    chunk_id=-provision.id,
                    article_number=self._normalize_number(provision.article_number),
                    clause_number=self._normalize_number(provision.clause_number),
                    point_number=self._normalize_number(provision.point_code),
                    start=start,
                    end=end,
                    text=content_text,
                )
            )
        return assembler.build(), fallback_spans

    def _render_chunk_text(self, chunk: DocumentChunk) -> str:
        parts: list[str] = []
        content = (chunk.content or "").strip()
        citation_label = (chunk.citation_label or "").strip()
        section_title = (chunk.section_title or "").strip()

        for candidate in (citation_label, section_title):
            if candidate and candidate.lower() not in content.lower():
                parts.append(candidate)

        if content:
            parts.append(content)

        if not parts and chunk.retrieval_text:
            parts.append(str(chunk.retrieval_text).strip())

        return "\n".join(part for part in parts if part).strip()

    def _anchor_provision_text(
        self,
        *,
        source_text: str,
        chunk_spans: list[_ChunkTextSpan],
        provision: LegalProvision,
    ) -> tuple[int | None, int | None, str, dict[str, str | int | float | bool | None]]:
        fallback_text = (provision.citation_label or provision.heading or provision.content[:200]).strip()
        candidate_texts = self._candidate_anchor_texts(provision)
        preferred_chunks = self._pick_candidate_chunks(chunk_spans, provision)

        for chunk_span in preferred_chunks:
            relative_match = self._find_first_match(chunk_span.text, candidate_texts)
            if relative_match is None:
                continue
            relative_start, relative_end, matched_text, match_kind = relative_match
            return (
                chunk_span.start + relative_start,
                chunk_span.start + relative_end,
                matched_text,
                {
                    "anchor_chunk_id": chunk_span.chunk_id,
                    "anchor_strategy": f"chunk:{match_kind}",
                    "anchor_status": "anchored",
                },
            )

        global_match = self._find_first_match(source_text, candidate_texts)
        if global_match is not None:
            start, end, matched_text, match_kind = global_match
            return (
                start,
                end,
                matched_text,
                {
                    "anchor_strategy": f"global:{match_kind}",
                    "anchor_status": "anchored",
                },
            )

        return (
            None,
            None,
            fallback_text,
            {
                "anchor_strategy": "unresolved",
                "anchor_status": "unanchored",
            },
        )

    def _pick_candidate_chunks(self, chunk_spans: list[_ChunkTextSpan], provision: LegalProvision) -> list[_ChunkTextSpan]:
        article_number = self._normalize_number(provision.article_number)
        clause_number = self._normalize_number(provision.clause_number)
        point_code = self._normalize_number(provision.point_code)
        matches: list[_ChunkTextSpan] = []

        for chunk_span in chunk_spans:
            if article_number and chunk_span.article_number not in {None, article_number}:
                continue
            if clause_number and chunk_span.clause_number not in {None, clause_number}:
                continue
            if point_code and chunk_span.point_number not in {None, point_code}:
                continue
            matches.append(chunk_span)

        return matches or chunk_spans

    def _candidate_anchor_texts(self, provision: LegalProvision) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        for match_kind, text in (
            ("citation_label", provision.citation_label),
            ("heading", provision.heading),
            ("content", provision.content),
        ):
            normalized = (text or "").strip().replace("\r", " ").replace("\n", " ")
            if normalized:
                candidates.append((match_kind, normalized))
        return candidates

    def _find_first_match(
        self,
        haystack: str,
        candidates: list[tuple[str, str]],
    ) -> tuple[int, int, str, str] | None:
        haystack_text = haystack or ""
        for match_kind, candidate in candidates:
            start = haystack_text.find(candidate)
            if start >= 0:
                return start, start + len(candidate), candidate, match_kind
        return None

    def _normalize_number(self, value: str | None) -> str | None:
        text = str(value or "").strip()
        return text or None

    def _build_semantic_prelabels_for_provision(
        self,
        *,
        provision: LegalProvision,
        preferred_chunks: list[_ChunkTextSpan],
    ) -> tuple[list[AnnotationEntityPayload], list[AnnotationRelationPayload]]:
        if not preferred_chunks:
            return [], []

        semantic_matches: list[_SemanticMatch] = []
        seen_ranges: set[tuple[str, int, int]] = set()

        for chunk_span in preferred_chunks:
            semantic_matches.extend(self._collect_semantic_matches_from_chunk(chunk_span, seen_ranges))

        semantic_entities: list[AnnotationEntityPayload] = []
        label_to_entity_id: dict[str, str] = {}

        for index, match in enumerate(sorted(semantic_matches, key=lambda item: (item.start, item.end, item.label)), start=1):
            entity_id = f"sem-{provision.id}-{match.label.lower()}-{index}"
            semantic_entities.append(
                AnnotationEntityPayload(
                    id=entity_id,
                    label=match.label,
                    text=match.text,
                    start=match.start,
                    end=match.end,
                    attributes={
                        "source": "LawChat_semantic_rule",
                        "prediction_provenance": match.provenance,
                        "parent_provision_id": provision.id,
                    },
                )
            )
            label_to_entity_id.setdefault(match.label, entity_id)

        semantic_relations: list[AnnotationRelationPayload] = []
        action_entity_id = label_to_entity_id.get("ACTION")
        if action_entity_id:
            if subject_entity_id := label_to_entity_id.get("SUBJECT"):
                semantic_relations.append(
                    AnnotationRelationPayload(
                        id=f"sem-rel-{provision.id}-subject-of",
                        relation_type="SUBJECT_OF",
                        source_entity_id=subject_entity_id,
                        target_entity_id=action_entity_id,
                        attributes={"source": "LawChat_semantic_rule", "prediction_provenance": "rule"},
                    )
                )
            if object_entity_id := label_to_entity_id.get("LEGAL_OBJECT"):
                semantic_relations.append(
                    AnnotationRelationPayload(
                        id=f"sem-rel-{provision.id}-acts-on",
                        relation_type="ACTS_ON",
                        source_entity_id=action_entity_id,
                        target_entity_id=object_entity_id,
                        attributes={"source": "LawChat_semantic_rule", "prediction_provenance": "rule"},
                    )
                )
            if condition_entity_id := label_to_entity_id.get("CONDITION"):
                semantic_relations.append(
                    AnnotationRelationPayload(
                        id=f"sem-rel-{provision.id}-condition",
                        relation_type="HAS_CONDITION",
                        source_entity_id=action_entity_id,
                        target_entity_id=condition_entity_id,
                        attributes={"source": "LawChat_semantic_rule", "prediction_provenance": "rule"},
                    )
                )
            if exception_entity_id := label_to_entity_id.get("EXCEPTION"):
                semantic_relations.append(
                    AnnotationRelationPayload(
                        id=f"sem-rel-{provision.id}-exception",
                        relation_type="HAS_EXCEPTION",
                        source_entity_id=action_entity_id,
                        target_entity_id=exception_entity_id,
                        attributes={"source": "LawChat_semantic_rule", "prediction_provenance": "rule"},
                    )
                )
            if consequence_entity_id := label_to_entity_id.get("CONSEQUENCE"):
                semantic_relations.append(
                    AnnotationRelationPayload(
                        id=f"sem-rel-{provision.id}-consequence",
                        relation_type="HAS_CONSEQUENCE",
                        source_entity_id=action_entity_id,
                        target_entity_id=consequence_entity_id,
                        attributes={"source": "LawChat_semantic_rule", "prediction_provenance": "rule"},
                    )
                )

        return semantic_entities, semantic_relations

    def _collect_semantic_matches_from_chunk(
        self,
        chunk_span: _ChunkTextSpan,
        seen_ranges: set[tuple[str, int, int]],
    ) -> list[_SemanticMatch]:
        matches: list[_SemanticMatch] = []
        for label, patterns in (
            ("EXCEPTION", EXCEPTION_PATTERNS),
            ("CONDITION", CONDITION_PATTERNS),
            ("SUBJECT", SUBJECT_PATTERNS),
            ("ACTION", ACTION_PATTERNS),
            ("LEGAL_OBJECT", LEGAL_OBJECT_PATTERNS),
            ("CONSEQUENCE", CONSEQUENCE_PATTERNS),
        ):
            match = self._find_semantic_pattern(chunk_span, label, patterns, seen_ranges)
            if match is not None:
                matches.append(match)
        return matches

    def _find_semantic_pattern(
        self,
        chunk_span: _ChunkTextSpan,
        label: str,
        patterns: tuple[re.Pattern[str], ...],
        seen_ranges: set[tuple[str, int, int]],
    ) -> _SemanticMatch | None:
        for pattern in patterns:
            result = pattern.search(chunk_span.text)
            if result is None:
                continue
            raw_text = result.group("match").strip(" \t\n:;,")
            if len(raw_text) < 2:
                continue
            relative_start = result.start("match")
            relative_end = result.start("match") + len(raw_text)
            absolute_start = chunk_span.start + relative_start
            absolute_end = chunk_span.start + relative_end
            dedupe_key = (label, absolute_start, absolute_end)
            if dedupe_key in seen_ranges:
                continue
            seen_ranges.add(dedupe_key)
            return _SemanticMatch(
                label=label,
                text=raw_text,
                start=absolute_start,
                end=absolute_end,
                provenance="rule",
            )
        return None


annotation_prelabel_service = AnnotationPrelabelService()
