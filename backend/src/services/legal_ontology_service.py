from __future__ import annotations

from dataclasses import asdict, dataclass

from src.services.legal_metadata_parser_service import legal_metadata_parser_service


@dataclass(frozen=True, slots=True)
class LegalRelationDefinition:
    relation_type: str
    label: str
    category: str
    legal_effect: str
    directional: bool
    code_match_confidence: float
    alias_match_confidence: float
    keywords: tuple[str, ...]


RELATION_DEFINITIONS: dict[str, LegalRelationDefinition] = {
    "repeals": LegalRelationDefinition(
        relation_type="repeals",
        label="Bãi bỏ / chấm dứt hiệu lực",
        category="effect",
        legal_effect="source document removes legal effect of target document or target provisions.",
        directional=True,
        code_match_confidence=0.97,
        alias_match_confidence=0.82,
        keywords=("bai bo", "huy bo", "het hieu luc", "ngung hieu luc", "cham dut hieu luc"),
    ),
    "replaces": LegalRelationDefinition(
        relation_type="replaces",
        label="Thay thế",
        category="effect",
        legal_effect="source document replaces the target document or cited provisions.",
        directional=True,
        code_match_confidence=0.96,
        alias_match_confidence=0.8,
        keywords=("thay the", "duoc thay the boi"),
    ),
    "amends": LegalRelationDefinition(
        relation_type="amends",
        label="Sửa đổi",
        category="modification",
        legal_effect="source document amends the target document or cited provisions.",
        directional=True,
        code_match_confidence=0.95,
        alias_match_confidence=0.78,
        keywords=("sua doi", "duoc sua doi", "sua doi mot so dieu"),
    ),
    "supplements": LegalRelationDefinition(
        relation_type="supplements",
        label="Bổ sung",
        category="modification",
        legal_effect="source document supplements the target document or cited provisions.",
        directional=True,
        code_match_confidence=0.93,
        alias_match_confidence=0.74,
        keywords=("bo sung", "duoc bo sung"),
    ),
    "consolidates": LegalRelationDefinition(
        relation_type="consolidates",
        label="Hợp nhất",
        category="consolidation",
        legal_effect="source VBHN consolidates the target legal instrument and its amendments into a unified text.",
        directional=True,
        code_match_confidence=0.98,
        alias_match_confidence=0.85,
        keywords=("van ban hop nhat", "hop nhat"),
    ),
    "guides_implementation": LegalRelationDefinition(
        relation_type="guides_implementation",
        label="Hướng dẫn thi hành",
        category="implementation",
        legal_effect="source document details or guides the implementation of the target document.",
        directional=True,
        code_match_confidence=0.94,
        alias_match_confidence=0.76,
        keywords=("huong dan", "quy dinh chi tiet", "quy dinh huong dan", "huong dan thi hanh"),
    ),
    "legal_basis": LegalRelationDefinition(
        relation_type="legal_basis",
        label="Căn cứ pháp lý",
        category="reference",
        legal_effect="source document cites target document as legal basis for promulgation or reasoning.",
        directional=True,
        code_match_confidence=0.9,
        alias_match_confidence=0.7,
        keywords=("can cu", "can cu vao", "co so phap ly"),
    ),
    "general_reference": LegalRelationDefinition(
        relation_type="general_reference",
        label="Dẫn chiếu chung",
        category="reference",
        legal_effect="source document references target document without establishing direct modifying effect.",
        directional=True,
        code_match_confidence=0.68,
        alias_match_confidence=0.52,
        keywords=("chieu theo", "theo quy dinh tai", "vien dan", "tham chieu", "doi chieu", "theo quy dinh cua"),
    ),
}


class LegalOntologyService:
    def get_relation_definition(self, relation_type: str) -> LegalRelationDefinition:
        definition = RELATION_DEFINITIONS.get(relation_type)
        if definition is None:
            raise KeyError(f"Unknown legal relation type: {relation_type}")
        return definition

    def relation_label(self, relation_type: str) -> str:
        return self.get_relation_definition(relation_type).label

    def classify_relation(
        self,
        *,
        context: str,
        source_document_type: str | None,
        source_document_code: str | None,
        matched_by_code: bool,
    ) -> tuple[str, str, float]:
        normalized_context = legal_metadata_parser_service.normalize_search_text(context)
        relation_type = self._classify_relation_type(
            normalized_context=normalized_context,
            source_document_type=source_document_type,
            source_document_code=source_document_code,
        )
        definition = self.get_relation_definition(relation_type)
        confidence = definition.code_match_confidence if matched_by_code else definition.alias_match_confidence
        return relation_type, definition.label, confidence

    def build_relation_metadata(self, relation_type: str) -> dict[str, object]:
        definition = self.get_relation_definition(relation_type)
        payload = asdict(definition)
        payload.pop("keywords", None)
        return payload

    def get_taxonomy_snapshot(self) -> list[dict[str, object]]:
        return [self.build_relation_metadata(relation_type) for relation_type in RELATION_DEFINITIONS]

    def _classify_relation_type(
        self,
        *,
        normalized_context: str,
        source_document_type: str | None,
        source_document_code: str | None,
    ) -> str:
        if self._is_vbhn(source_document_type=source_document_type, source_document_code=source_document_code):
            return "consolidates"

        for relation_type in ("repeals", "replaces", "amends", "supplements", "legal_basis", "guides_implementation", "general_reference"):
            definition = self.get_relation_definition(relation_type)
            if any(keyword in normalized_context for keyword in definition.keywords):
                return relation_type
        return "general_reference"

    def _is_vbhn(self, *, source_document_type: str | None, source_document_code: str | None) -> bool:
        normalized_type = (source_document_type or "").strip().lower()
        normalized_code = legal_metadata_parser_service.normalize_code(source_document_code or "")
        return normalized_type == "van-ban-hop-nhat" or "VBHN-" in normalized_code


legal_ontology_service = LegalOntologyService()
