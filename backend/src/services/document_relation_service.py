import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from src.core.logging import logger
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_relation import DocumentRelation
from src.services.legal_metadata_parser_service import legal_metadata_parser_service
from src.services.legal_ontology_service import legal_ontology_service


@dataclass(slots=True)
class RelationSyncSummary:
    document_id: int
    created_relations: int
    relation_types: dict[str, int]
    status: str


class DocumentRelationService:
    def sync_document_relations(self, db: Session, document_id: int) -> RelationSyncSummary:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError("Document not found for relation sync")

        db.query(DocumentRelation).filter(DocumentRelation.source_document_id == document_id).delete(synchronize_session=False)
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        raw_haystack = "\n".join(
            filter(
                None,
                [
                    legal_metadata_parser_service.clean_document_title(document.title) or document.title,
                    document.summary,
                    *(chunk.content for chunk in chunks[:40]),
                ],
            )
        )
        haystack, index_map = self._normalize_text_with_index_map(raw_haystack)
        cited_code_mentions = legal_metadata_parser_service.extract_citation_code_mentions(raw_haystack)
        candidates = (
            db.query(Document)
            .filter(Document.id != document_id)
            .filter(Document.is_active == True)
            .all()
        )

        relation_types: dict[str, int] = {}
        created_relations = 0
        seen_pairs: set[tuple[int, str]] = set()

        for candidate in candidates:
            relation = self._detect_relation(haystack, raw_haystack, index_map, document, candidate, cited_code_mentions)
            if relation is None:
                continue

            key = (candidate.id, relation[0])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            relation_type, relation_label, legal_basis, confidence = relation
            relation_metadata = self._build_relation_metadata(
                db=db,
                source_document=document,
                target_document=candidate,
                relation_type=relation_type,
                source_excerpt=legal_basis,
            )
            db.add(
                DocumentRelation(
                    source_document_id=document_id,
                    target_document_id=candidate.id,
                    relation_type=relation_type,
                    relation_label=relation_label,
                    legal_basis=legal_basis,
                    confidence_score=confidence,
                    is_active=True,
                    metadata_json=json.dumps(
                        relation_metadata,
                        ensure_ascii=True,
                    ),
                )
            )
            created_relations += 1
            relation_types[relation_type] = relation_types.get(relation_type, 0) + 1

        status = "synced" if created_relations > 0 else "no_matches"
        document.relation_sync_status = status
        document.relation_sync_details = json.dumps({"created_relations": created_relations, "relation_types": relation_types}, ensure_ascii=True)
        db.flush()
        logger.info("Document %s relation sync finished with status=%s created=%s", document_id, status, created_relations)
        return RelationSyncSummary(document_id=document_id, created_relations=created_relations, relation_types=relation_types, status=status)

    def mark_relation_sync_failed(self, db: Session, document_id: int, reason: str) -> None:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            return
        document.relation_sync_status = "failed"
        document.relation_sync_details = json.dumps({"error": reason}, ensure_ascii=True)

    def _detect_relation(
        self,
        haystack: str,
        raw_haystack: str,
        index_map: list[int],
        source_document: Document,
        candidate: Document,
        cited_code_mentions: list[dict[str, int | str]],
    ) -> tuple[str, str, str, float] | None:
        candidate_code_aliases = legal_metadata_parser_service.code_aliases_for_document(
            file_name=candidate.file_name,
            document_code=candidate.document_code,
        )
        candidate_code_set = {legal_metadata_parser_service.normalize_code(code) for code in candidate_code_aliases if code}
        for mention in cited_code_mentions:
            mention_code = str(mention["code"])
            if mention_code not in candidate_code_set:
                continue
            normalized_match_text = self._normalize_text(mention_code)
            match_start = haystack.find(normalized_match_text)
            if match_start < 0:
                normalized_match_text = self._normalize_text(str(mention["raw"]))
                match_start = haystack.find(normalized_match_text)
            if match_start >= 0:
                return self._classify_relation_from_context(
                    haystack,
                    raw_haystack,
                    index_map,
                    source_document,
                    match_start,
                    normalized_match_text,
                    matched_by_code=True,
                )

        aliases = self._candidate_aliases(candidate)
        aliases = [alias for alias in aliases if alias]
        if not aliases:
            return None

        match_start = -1
        match_text = ""
        for alias in aliases:
            position = haystack.find(alias)
            if position >= 0 and (match_start < 0 or position < match_start):
                match_start = position
                match_text = alias
        if match_start < 0:
            return None

        return self._classify_relation_from_context(
            haystack,
            raw_haystack,
            index_map,
            source_document,
            match_start,
            match_text,
            matched_by_code=False,
        )

    def _classify_relation_from_context(
        self,
        haystack: str,
        raw_haystack: str,
        index_map: list[int],
        source_document: Document,
        match_start: int,
        match_text: str,
        *,
        matched_by_code: bool,
    ) -> tuple[str, str, str, float]:
        context = haystack[max(0, match_start - 160): match_start + len(match_text) + 160]
        raw_context = self._extract_raw_context(
            raw_haystack=raw_haystack,
            index_map=index_map,
            normalized_start=max(0, match_start - 160),
            normalized_end=match_start + len(match_text) + 160,
        )
        relation_type, relation_label, confidence = legal_ontology_service.classify_relation(
            context=context,
            source_document_type=source_document.document_type,
            source_document_code=source_document.document_code,
            matched_by_code=matched_by_code,
        )
        return relation_type, relation_label, raw_context[:280], confidence

    def _build_relation_metadata(
        self,
        *,
        db: Session,
        source_document: Document,
        target_document: Document,
        relation_type: str,
        source_excerpt: str,
    ) -> dict[str, object]:
        return {
            "target_document_code": target_document.document_code,
            "target_title": target_document.title,
            "ontology": legal_ontology_service.build_relation_metadata(relation_type),
            "evidence": {
                "source_excerpt": source_excerpt,
                "target_anchor": self._build_target_anchor(target_document),
                "target_excerpt": self._find_target_excerpt(db, source_document, target_document),
            },
        }

    def _build_target_anchor(self, target_document: Document) -> str:
        parts = [
            target_document.title.strip() if target_document.title else None,
            target_document.document_code.strip() if target_document.document_code else None,
        ]
        return " | ".join(part for part in parts if part)

    def _find_target_excerpt(self, db: Session, source_document: Document, target_document: Document) -> str | None:
        aliases = self._candidate_aliases(source_document)
        if not aliases:
            return None

        target_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == target_document.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(40)
            .all()
        )
        raw_haystack = "\n".join(
            filter(
                None,
                [
                    legal_metadata_parser_service.clean_document_title(target_document.title) or target_document.title,
                    target_document.summary,
                    *(chunk.content for chunk in target_chunks),
                ],
            )
        )
        if not raw_haystack:
            return None

        normalized_haystack, index_map = self._normalize_text_with_index_map(raw_haystack)
        earliest_match_start = -1
        earliest_match_text = ""
        for alias in aliases:
            position = normalized_haystack.find(alias)
            if position >= 0 and (earliest_match_start < 0 or position < earliest_match_start):
                earliest_match_start = position
                earliest_match_text = alias
        if earliest_match_start < 0:
            return None

        return self._extract_raw_context(
            raw_haystack=raw_haystack,
            index_map=index_map,
            normalized_start=max(0, earliest_match_start - 120),
            normalized_end=earliest_match_start + len(earliest_match_text) + 120,
        )[:280]

    def _candidate_aliases(self, candidate: Document) -> list[str]:
        aliases: list[str] = []
        clean_title = legal_metadata_parser_service.clean_document_title(candidate.title)
        for item in [candidate.title, clean_title]:
            normalized = self._normalize_text(item or "")
            if normalized:
                aliases.append(normalized)
        for code in legal_metadata_parser_service.code_aliases_for_document(
            file_name=candidate.file_name,
            document_code=candidate.document_code,
        ):
            normalized = self._normalize_text(code)
            if normalized:
                aliases.append(normalized)
        file_stem = Path(candidate.file_name).stem if candidate.file_name else ""
        normalized_stem = self._normalize_text(file_stem)
        if normalized_stem:
            aliases.append(normalized_stem)

        deduped: list[str] = []
        for alias in aliases:
            if alias not in deduped:
                deduped.append(alias)
        return deduped

    def _normalize_text(self, value: str) -> str:
        normalized, _ = self._normalize_text_with_index_map(value)
        return normalized

    def _normalize_text_with_index_map(self, value: str) -> tuple[str, list[int]]:
        normalized_parts: list[str] = []
        index_map: list[int] = []
        last_was_space = False
        for index, character in enumerate(value):
            normalized_character = self._normalize_character(character)
            if normalized_character == " ":
                if not normalized_parts or last_was_space:
                    continue
                normalized_parts.append(" ")
                index_map.append(index)
                last_was_space = True
                continue
            for item in normalized_character:
                normalized_parts.append(item)
                index_map.append(index)
            last_was_space = False

        while normalized_parts and normalized_parts[0] == " ":
            normalized_parts.pop(0)
            index_map.pop(0)
        while normalized_parts and normalized_parts[-1] == " ":
            normalized_parts.pop()
            index_map.pop()
        return "".join(normalized_parts), index_map

    def _normalize_character(self, character: str) -> str:
        normalized = legal_metadata_parser_service.normalize_search_text(character.replace("Đ", "D").replace("đ", "d"))
        if not normalized:
            return " "
        if normalized in "abcdefghijklmnopqrstuvwxyz0123456789/":
            return normalized
        return " "

    def _extract_raw_context(
        self,
        *,
        raw_haystack: str,
        index_map: list[int],
        normalized_start: int,
        normalized_end: int,
    ) -> str:
        if not raw_haystack or not index_map:
            return raw_haystack.strip()
        safe_start = max(0, min(normalized_start, len(index_map) - 1))
        safe_end = max(0, min(normalized_end - 1, len(index_map) - 1))
        raw_start = max(0, index_map[safe_start] - 60)
        raw_end = min(len(raw_haystack), index_map[safe_end] + 60)
        excerpt = raw_haystack[raw_start:raw_end]
        return re.sub(r"\s+", " ", excerpt).strip()


document_relation_service = DocumentRelationService()
