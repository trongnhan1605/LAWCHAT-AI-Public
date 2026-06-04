from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass


PART_PATTERN = re.compile(r"^(PHẦN|Phan|han)\s+(.+)$", flags=re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^(Chương|Chuong|huong)\s+(.+)$", flags=re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(Mục|Muc|uc)\s+(.+)$", flags=re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^(Điều|Dieu|ieu)\s+(\d+[A-Za-z]*)\s*[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
CLAUSE_PATTERN = re.compile(r"^((?:Khoản|Khoan|hoan)\s+)?(\d+)(?!\.\d)[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
POINT_PATTERN = re.compile(r"^((?:Điểm|Diem|iem)\s+)?([a-zđ])([\)\.:\-])?\s*(.*)$")
ROMAN_ARTICLE_PATTERN = re.compile(r"^([IVXLC]+)\.\s*(.*)$", flags=re.IGNORECASE)
OUTLINE_ARTICLE_PATTERN = re.compile(r"^(\d+)[\.\-:]\s*(.*)$")
DECIMAL_CLAUSE_PATTERN = re.compile(r"^(\d+\.\d+)[\.\-:]?\s*(.*)$")
LEGAL_TITLE_MAX_CHARS = 220
HEADING_MAX_CHARS = 500


@dataclass(slots=True)
class ProvisionDraft:
    temp_id: str
    parent_temp_id: str | None
    provision_level: str
    article_number: str | None
    clause_number: str | None
    point_code: str | None
    heading: str | None
    content: str
    citation_label: str
    sort_key: str
    metadata_json: str | None


class LegalProvisionParserService:
    def normalize_structure_segment(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value).strip()
        normalized = re.sub(r"^(ieu)(\s+\d+[A-Za-z]*)", r"Điều\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^(hoan)(\s+\d+)", r"Khoản\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^(iem)(\s+[a-zđ])", r"Điểm\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^(huong)(\s+[IVXLC0-9])", r"Chương\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^(uc)(\s+[IVXLC0-9A-Za-z])", r"Mục\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^(han)(\s+[IVXLC0-9A-Za-z])", r"Phần\2", normalized, flags=re.IGNORECASE)
        return normalized

    def parse_text(self, text: str) -> list[ProvisionDraft]:
        segments = [self._normalize_segment(line) for line in text.splitlines()]
        segments = [segment for segment in segments if segment]
        if not segments:
            return []

        context = {"part": None, "chapter": None, "section": None}
        provision_drafts: list[ProvisionDraft] = []
        current_article: str | None = None
        current_article_kind: str | None = None
        article_body_segments: list[str] = []
        index = 0

        while index < len(segments):
            segment = segments[index]
            heading_kind, _ = self._match_heading(segment)
            if heading_kind is not None:
                if current_article is not None:
                    provision_drafts.extend(self._emit_article_provisions(context, current_article, article_body_segments))
                    current_article = None
                    current_article_kind = None
                    article_body_segments = []
                heading_text, consumed = self._consume_heading_with_optional_title(segment, segments, index)
                context[heading_kind] = heading_text
                index += consumed
                continue

            if self._is_article_heading(segment) or self._is_roman_article_heading(segment) or (current_article is None and self._is_outline_article_heading(segment)):
                if current_article is not None:
                    provision_drafts.extend(self._emit_article_provisions(context, current_article, article_body_segments))
                current_article, current_article_kind, consumed = self._consume_article_heading(segment, segments, index)
                article_body_segments = []
                index += consumed
                continue

            if current_article_kind == "outline" and self._is_outline_article_heading(segment):
                provision_drafts.extend(self._emit_article_provisions(context, current_article or "", article_body_segments))
                current_article, current_article_kind, consumed = self._consume_article_heading(segment, segments, index)
                article_body_segments = []
                index += consumed
                continue

            if current_article is not None:
                article_body_segments.append(segment)
            index += 1

        if current_article is not None:
            provision_drafts.extend(self._emit_article_provisions(context, current_article, article_body_segments))

        return provision_drafts

    def build_document_payloads(self, *, document_id: int, text: str) -> list[dict[str, object | None]]:
        provision_drafts = self.parse_text(text)
        id_by_temp_key: dict[str, int] = {}
        payloads: list[dict[str, object | None]] = []

        for index, draft in enumerate(provision_drafts, start=1):
            id_by_temp_key[draft.temp_id] = index

        for draft in provision_drafts:
            payload = asdict(draft)
            payload["document_id"] = document_id
            payload["parent_provision_id"] = id_by_temp_key.get(draft.parent_temp_id) if draft.parent_temp_id else None
            payload.pop("temp_id", None)
            payload.pop("parent_temp_id", None)
            payloads.append(payload)
        return payloads

    def _emit_article_provisions(
        self,
        context: dict[str, str | None],
        article_heading: str,
        body_segments: list[str],
    ) -> list[ProvisionDraft]:
        article_number = self._extract_article_number(article_heading)
        article_sort = self._sort_fragment(article_number)
        article_temp_id = f"article:{article_number or article_sort}"
        article_citation = self._build_article_citation(article_heading, article_number)
        clause_groups, article_intro = self._group_clauses(body_segments)
        drafts: list[ProvisionDraft] = []

        article_inline_content = self._extract_inline_article_content(article_heading)
        article_content_segments = [*([article_inline_content] if article_inline_content else []), *(article_intro if clause_groups else body_segments)]
        if not article_content_segments and body_segments:
            article_content_segments = [*([article_inline_content] if article_inline_content else []), *body_segments]
        article_content = "\n".join(segment for segment in article_content_segments if segment).strip()
        drafts.append(
            self._make_draft(
                temp_id=article_temp_id,
                parent_temp_id=None,
                provision_level="article",
                article_number=article_number,
                clause_number=None,
                point_code=None,
                heading=article_heading,
                content=article_content,
                citation_label=article_citation,
                sort_key=f"{article_sort}.000.000",
                context=context,
            )
        )

        for clause_heading, clause_body in clause_groups:
            clause_number = self._extract_clause_number(clause_heading)
            clause_sort = self._sort_fragment(clause_number)
            clause_temp_id = f"{article_temp_id}:clause:{clause_number or clause_sort}"
            clause_citation = f"{article_citation} Khoản {clause_number}" if clause_number else article_citation
            point_groups, clause_intro = self._group_points(clause_body)
            clause_inline_content = self._extract_inline_clause_content(clause_heading)
            clause_content_segments = [*([clause_inline_content] if clause_inline_content else []), *(clause_intro if point_groups else clause_body)]
            if not clause_content_segments and clause_body:
                clause_content_segments = [*([clause_inline_content] if clause_inline_content else []), *clause_body]
            clause_content = "\n".join(segment for segment in clause_content_segments if segment).strip()
            drafts.append(
                self._make_draft(
                    temp_id=clause_temp_id,
                    parent_temp_id=article_temp_id,
                    provision_level="clause",
                    article_number=article_number,
                    clause_number=clause_number,
                    point_code=None,
                    heading=clause_heading,
                    content=clause_content,
                    citation_label=clause_citation,
                    sort_key=f"{article_sort}.{clause_sort}.000",
                    context=context,
                )
            )

            for point_heading, point_body in point_groups:
                point_code = self._extract_point_code(point_heading)
                point_sort = self._point_sort_fragment(point_code)
                point_citation = f"{clause_citation} Điểm {point_code}" if point_code else clause_citation
                point_inline_content = self._extract_inline_point_content(point_heading)
                point_content = "\n".join(segment for segment in [*([point_inline_content] if point_inline_content else []), *point_body] if segment).strip()
                drafts.append(
                    self._make_draft(
                        temp_id=f"{clause_temp_id}:point:{point_code or point_sort}",
                        parent_temp_id=clause_temp_id,
                        provision_level="point",
                        article_number=article_number,
                        clause_number=clause_number,
                        point_code=point_code,
                        heading=point_heading,
                        content=point_content,
                        citation_label=point_citation,
                        sort_key=f"{article_sort}.{clause_sort}.{point_sort}",
                        context=context,
                    )
                )

        return drafts

    def _group_clauses(self, body_segments: list[str]) -> tuple[list[tuple[str, list[str]]], list[str]]:
        clause_groups: list[tuple[str, list[str]]] = []
        article_intro: list[str] = []
        current_clause_heading: str | None = None
        current_clause_body: list[str] = []

        for segment in body_segments:
            if self._is_clause_heading(segment):
                if current_clause_heading is not None:
                    clause_groups.append((current_clause_heading, current_clause_body.copy()))
                current_clause_heading = segment
                current_clause_body = []
                continue

            if current_clause_heading is None:
                article_intro.append(segment)
            else:
                current_clause_body.append(segment)

        if current_clause_heading is not None:
            clause_groups.append((current_clause_heading, current_clause_body.copy()))

        return clause_groups, article_intro

    def _group_points(self, clause_body: list[str]) -> tuple[list[tuple[str, list[str]]], list[str]]:
        point_groups: list[tuple[str, list[str]]] = []
        clause_intro: list[str] = []
        current_point_heading: str | None = None
        current_point_body: list[str] = []

        for segment in clause_body:
            if self._is_point_heading(segment):
                if current_point_heading is not None:
                    point_groups.append((current_point_heading, current_point_body.copy()))
                current_point_heading = segment
                current_point_body = []
                continue

            if current_point_heading is None:
                clause_intro.append(segment)
            else:
                current_point_body.append(segment)

        if current_point_heading is not None:
            point_groups.append((current_point_heading, current_point_body.copy()))

        return point_groups, clause_intro

    def _make_draft(
        self,
        *,
        temp_id: str,
        parent_temp_id: str | None,
        provision_level: str,
        article_number: str | None,
        clause_number: str | None,
        point_code: str | None,
        heading: str | None,
        content: str,
        citation_label: str,
        sort_key: str,
        context: dict[str, str | None],
    ) -> ProvisionDraft:
        metadata_json = json.dumps(
            {
                "part": context["part"],
                "chapter": context["chapter"],
                "section": context["section"],
                "heading": heading,
            },
            ensure_ascii=False,
        )
        return ProvisionDraft(
            temp_id=temp_id,
            parent_temp_id=parent_temp_id,
            provision_level=provision_level,
            article_number=article_number,
            clause_number=clause_number,
            point_code=point_code,
            heading=self._truncate_heading(heading),
            content=content,
            citation_label=citation_label[:255],
            sort_key=sort_key,
            metadata_json=metadata_json,
        )

    def _normalize_segment(self, value: str) -> str:
        return self.normalize_structure_segment(value)

    def _match_heading(self, segment: str) -> tuple[str | None, str | None]:
        for kind, pattern in (("part", PART_PATTERN), ("chapter", CHAPTER_PATTERN), ("section", SECTION_PATTERN)):
            match = pattern.match(segment)
            if match:
                return kind, match.group(0).strip()
        return None, None

    def _consume_heading_with_optional_title(self, segment: str, segments: list[str], index: int) -> tuple[str, int]:
        heading_kind, _ = self._match_heading(segment)
        if heading_kind is None:
            return segment, 1
        if index + 1 < len(segments) and self._is_heading_title_candidate(segments[index + 1]):
            return f"{segment} {segments[index + 1]}", 2
        return segment, 1

    def _consume_article_heading(self, segment: str, segments: list[str], index: int) -> tuple[str, str, int]:
        match = ARTICLE_PATTERN.match(segment)
        if match is not None:
            _, article_number, article_title = match.groups()
            article_title = article_title.strip()
            if article_title:
                return f"Điều {article_number}. {article_title}", "standard", 1
            if index + 1 < len(segments) and self._is_heading_title_candidate(segments[index + 1]):
                return f"Điều {article_number}. {segments[index + 1]}", "standard", 2
            return f"Điều {article_number}", "standard", 1

        roman_match = ROMAN_ARTICLE_PATTERN.match(segment)
        if roman_match is not None:
            article_number, article_title = roman_match.groups()
            article_title = article_title.strip()
            normalized_heading = f"{article_number.upper()}."
            if article_title:
                normalized_heading = f"{normalized_heading} {article_title}"
            elif index + 1 < len(segments) and self._is_heading_title_candidate(segments[index + 1]):
                normalized_heading = f"{normalized_heading} {segments[index + 1]}"
                return normalized_heading, "roman", 2
            return normalized_heading, "roman", 1

        outline_match = OUTLINE_ARTICLE_PATTERN.match(segment)
        if outline_match is not None:
            article_number, article_title = outline_match.groups()
            return f"{article_number}. {article_title.strip()}".strip(), "outline", 1

        return segment, "standard", 1

    def _is_heading_title_candidate(self, segment: str) -> bool:
        if len(segment) > LEGAL_TITLE_MAX_CHARS:
            return False
        if self._match_heading(segment)[0] is not None:
            return False
        return not self._is_article_heading(segment) and not self._is_clause_heading(segment) and not self._is_point_heading(segment)

    def _is_article_heading(self, segment: str) -> bool:
        return ARTICLE_PATTERN.match(segment) is not None

    def _is_roman_article_heading(self, segment: str) -> bool:
        return ROMAN_ARTICLE_PATTERN.match(segment) is not None

    def _is_outline_article_heading(self, segment: str) -> bool:
        match = OUTLINE_ARTICLE_PATTERN.match(segment)
        return match is not None and len(match.group(1)) <= 3

    def _is_clause_heading(self, segment: str) -> bool:
        return CLAUSE_PATTERN.match(segment) is not None or DECIMAL_CLAUSE_PATTERN.match(segment) is not None

    def _is_point_heading(self, segment: str) -> bool:
        return POINT_PATTERN.match(segment) is not None

    def _extract_article_number(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = ARTICLE_PATTERN.match(heading)
        if match:
            return match.group(2)
        roman_match = ROMAN_ARTICLE_PATTERN.match(heading)
        if roman_match:
            return roman_match.group(1).upper()
        outline_match = OUTLINE_ARTICLE_PATTERN.match(heading)
        if outline_match:
            return outline_match.group(1)
        return None

    def _extract_inline_article_content(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = ARTICLE_PATTERN.match(heading)
        if match is not None:
            inline_content = (match.group(3) or "").strip()
            return inline_content or None
        roman_match = ROMAN_ARTICLE_PATTERN.match(heading)
        if roman_match is not None:
            inline_content = (roman_match.group(2) or "").strip()
            return inline_content or None
        outline_match = OUTLINE_ARTICLE_PATTERN.match(heading)
        if outline_match is not None:
            inline_content = (outline_match.group(2) or "").strip()
            return inline_content or None
        return None

    def _extract_clause_number(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = CLAUSE_PATTERN.match(heading)
        if match:
            return match.group(2)
        decimal_match = DECIMAL_CLAUSE_PATTERN.match(heading)
        return decimal_match.group(1) if decimal_match else None

    def _extract_inline_clause_content(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = CLAUSE_PATTERN.match(heading)
        if match is not None:
            inline_content = (match.group(3) or "").strip()
            return inline_content or None
        decimal_match = DECIMAL_CLAUSE_PATTERN.match(heading)
        if decimal_match is not None:
            inline_content = (decimal_match.group(2) or "").strip()
            return inline_content or None
        return None

    def _extract_point_code(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = POINT_PATTERN.match(heading)
        return match.group(2) if match else None

    def _extract_inline_point_content(self, heading: str | None) -> str | None:
        if not heading:
            return None
        match = POINT_PATTERN.match(heading)
        if match is None:
            return None
        inline_content = (match.group(4) or "").strip()
        return inline_content or None

    def _sort_fragment(self, value: str | None) -> str:
        if not value:
            return "000"
        digits = re.sub(r"[^0-9]", "", value)
        if digits:
            return digits.zfill(3)
        return value[:3].upper().rjust(3, "0")

    def _point_sort_fragment(self, value: str | None) -> str:
        if not value:
            return "000"
        normalized = value.lower()
        if normalized.isalpha():
            return str(ord(normalized[0]) - 96).zfill(3)
        return self._sort_fragment(value)

    def _truncate_heading(self, value: str | None) -> str | None:
        if not value:
            return None
        return value[:HEADING_MAX_CHARS]

    def _build_article_citation(self, heading: str | None, article_number: str | None) -> str:
        if not heading:
            return article_number or "Article"
        if ARTICLE_PATTERN.match(heading) is not None and article_number:
            return f"Điều {article_number}"
        return heading


legal_provision_parser_service = LegalProvisionParserService()
