from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.schemas.annotation_schema import (
    AnnotationDocumentPayload,
    AnnotationEntityPayload,
    AnnotationRelationPayload,
)


SUPPORTED_LABEL_RESULT_TYPES = {"labels", "hypertextlabels", "taxonomy"}


class AnnotationVendorAdapter(Protocol):
    vendor: str

    def to_document_payload(self, raw_item: dict[str, Any]) -> AnnotationDocumentPayload: ...


class UnsupportedAnnotationVendorError(ValueError):
    pass


@dataclass(slots=True)
class LabelStudioAnnotationAdapter:
    vendor: str = "label_studio"

    def to_document_payload(self, raw_item: dict[str, Any]) -> AnnotationDocumentPayload:
        data = raw_item.get("data") or {}
        result_items = self._pick_result_items(raw_item)
        entities = [*self._build_metadata_entities(data), *self._build_entities(result_items)]
        relations = self._build_relations(result_items)

        return AnnotationDocumentPayload(
            document_id=self._coerce_int(data.get("document_id")),
            vendor=self.vendor,
            source_file_name=self._pick_source_file_name(data),
            source_text=self._pick_source_text(data),
            language=str(data.get("language") or "vi"),
            review_status=self._pick_review_status(raw_item),
            entities=entities,
            relations=relations,
        )

    def _pick_result_items(self, raw_item: dict[str, Any]) -> list[dict[str, Any]]:
        for key, review_status in (("annotations", "reviewed"), ("predictions", "predicted")):
            items = raw_item.get(key)
            if isinstance(items, list) and items:
                first = items[0] or {}
                raw_item.setdefault("_derived_review_status", review_status)
                return list(first.get("result") or [])
        raw_item.setdefault("_derived_review_status", "draft")
        return []

    def _pick_review_status(self, raw_item: dict[str, Any]) -> str:
        return str(raw_item.get("_derived_review_status") or "draft")

    def _pick_source_file_name(self, data: dict[str, Any]) -> str | None:
        for key in ("source_file_name", "file_name", "document_name", "title"):
            value = data.get(key)
            if value:
                return str(value)
        for key in ("pdf", "text", "document_url"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value.rsplit("/", 1)[-1][:255]
        return None

    def _pick_source_text(self, data: dict[str, Any]) -> str | None:
        for key in ("text", "content", "body"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _build_metadata_entities(self, data: dict[str, Any]) -> list[AnnotationEntityPayload]:
        raw_items = data.get("metadata_prelabels") or []
        if not isinstance(raw_items, list):
            return []

        entities: list[AnnotationEntityPayload] = []
        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                continue
            label = str(raw_item.get("label") or "").strip()
            text = str(raw_item.get("text") or raw_item.get("normalized_value") or "").strip()
            if not label or not text:
                continue
            attributes = raw_item.get("attributes") if isinstance(raw_item.get("attributes"), dict) else {}
            entities.append(
                AnnotationEntityPayload(
                    id=str(raw_item.get("id") or f"metadata-{index + 1}"),
                    label=label,
                    text=text,
                    normalized_value=self._coerce_str(raw_item.get("normalized_value")) or text,
                    attributes=attributes,
                )
            )
        return entities

    def _build_entities(self, result_items: list[dict[str, Any]]) -> list[AnnotationEntityPayload]:
        entities: list[AnnotationEntityPayload] = []

        for item in result_items:
            item_type = str(item.get("type") or "").lower()
            if item_type not in SUPPORTED_LABEL_RESULT_TYPES:
                continue

            value = item.get("value") or {}
            labels = value.get("labels") or item.get("labels") or []
            if not labels:
                continue
            label = str(labels[0]).strip()
            if not label:
                continue

            attributes = {
                key: val
                for key, val in value.items()
                if key not in {"start", "end", "text", "labels"}
            }
            if item.get("score") is not None:
                attributes["prediction_score"] = item["score"]

            entities.append(
                AnnotationEntityPayload(
                    id=str(item.get("id") or ""),
                    label=label,
                    text=str(value.get("text") or ""),
                    start=self._coerce_int(value.get("start")),
                    end=self._coerce_int(value.get("end")),
                    normalized_value=self._coerce_str(attributes.get("normalized_value")),
                    attributes=attributes,
                )
            )

        return entities

    def _build_relations(self, result_items: list[dict[str, Any]]) -> list[AnnotationRelationPayload]:
        relations: list[AnnotationRelationPayload] = []

        for item in result_items:
            if str(item.get("type") or "").lower() != "relation":
                continue
            relation_labels = item.get("labels") or item.get("value", {}).get("labels") or []
            if not relation_labels:
                relation_type = "RELATED_TO"
            else:
                relation_type = str(relation_labels[0]).strip() or "RELATED_TO"
            confidence_score = item.get("score")

            attributes = {
                key: val
                for key, val in item.items()
                if key not in {"id", "type", "from_id", "to_id", "labels", "score", "value"}
            }
            value = item.get("value")
            if isinstance(value, dict):
                for key, val in value.items():
                    if key != "labels":
                        attributes[key] = val

            relations.append(
                AnnotationRelationPayload(
                    id=str(item.get("id") or f"{item.get('from_id')}->{item.get('to_id')}"),
                    relation_type=relation_type,
                    source_entity_id=str(item.get("from_id") or ""),
                    target_entity_id=str(item.get("to_id") or ""),
                    confidence_score=float(confidence_score) if confidence_score is not None else None,
                    attributes=attributes,
                )
            )

        return relations

    def _coerce_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _coerce_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class AnnotationVendorAdapterService:
    def __init__(self) -> None:
        self._adapters: dict[str, AnnotationVendorAdapter] = {
            "label_studio": LabelStudioAnnotationAdapter(),
        }

    def register(self, adapter: AnnotationVendorAdapter) -> None:
        self._adapters[adapter.vendor] = adapter

    def to_document_payload(self, vendor: str, raw_item: dict[str, Any]) -> AnnotationDocumentPayload:
        adapter = self._adapters.get(vendor)
        if adapter is None:
            supported = ", ".join(sorted(self._adapters))
            raise UnsupportedAnnotationVendorError(
                f"Unsupported annotation vendor '{vendor}'. Supported vendors: {supported}"
            )
        return adapter.to_document_payload(raw_item)

    @property
    def supported_vendors(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


annotation_vendor_adapter_service = AnnotationVendorAdapterService()
