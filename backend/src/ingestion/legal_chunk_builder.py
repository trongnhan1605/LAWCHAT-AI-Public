from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from src.ingestion.text_extraction import document_text_extractor
from src.models.document import Document


LEGAL_TITLE_MAX_CHARS = 220
FALLBACK_TARGET_WORDS = 220
FALLBACK_MAX_WORDS = 320
FALLBACK_OVERLAP_SEGMENTS = 1
PART_PATTERN = re.compile(r"^(PHẦN|Phan|han)\s+(.+)$", flags=re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^(Chương|Chuong|huong)\s+(.+)$", flags=re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(Mục|Muc|uc)\s+(.+)$", flags=re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^(Điều|Dieu|ieu)\s+(\d+[A-Za-z]*)\s*[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
CLAUSE_PATTERN = re.compile(r"^((?:Khoản|Khoan|hoan)\s+)?(\d+)(?!\.\d)[\.:\-]?\s*(.*)$", flags=re.IGNORECASE)
POINT_PATTERN = re.compile(r"^((?:Điểm|Diem|iem)\s+)?([a-zđ])([\)\.:\-])?\s*(.*)$")
ROMAN_ARTICLE_PATTERN = re.compile(r"^([IVXLC]+)\.\s*(.*)$", flags=re.IGNORECASE)
OUTLINE_ARTICLE_PATTERN = re.compile(r"^(\d+)[\.\-:]\s*(.*)$")
DECIMAL_CLAUSE_PATTERN = re.compile(r"^(\d+\.\d+)[\.\-:]?\s*(.*)$")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[\.;:!?])\s+")


@dataclass(frozen=True)
class LegalChunkBuilderCallbacks:
    build_legal_chunks: Callable[[list[str]], list[tuple[str | None, str]]] | None = None
    build_fallback_chunks: Callable[[list[str]], list[tuple[str | None, str]]] | None = None
    build_chunk_metadata: Callable[[Document, str | None, str], dict[str, str | None]] | None = None


class LegalChunkBuilder:
    def build_chunk_payloads(
        self,
        segments: list[str],
        *,
        callbacks: LegalChunkBuilderCallbacks | None = None,
    ) -> list[tuple[str | None, str]]:
        legal_chunks = callbacks.build_legal_chunks(segments) if callbacks and callbacks.build_legal_chunks else self.build_legal_chunks(segments)
        if legal_chunks:
            return legal_chunks
        return callbacks.build_fallback_chunks(segments) if callbacks and callbacks.build_fallback_chunks else self.build_fallback_chunks(segments)

    def build_chunk_metadata(
        self,
        document: Document,
        section_title: str | None,
        content: str,
        *,
        callbacks: LegalChunkBuilderCallbacks | None = None,
    ) -> dict[str, str | None]:
        if callbacks and callbacks.build_chunk_metadata:
            return callbacks.build_chunk_metadata(document, section_title, content)
        return self.build_chunk_metadata_payload(document, section_title, content)

    def build_legal_chunks(self, segments: list[str]) -> list[tuple[str | None, str]]:
        chunks: list[tuple[str | None, str]] = []
        context = {"part": None, "chapter": None, "section": None}
        preamble_segments: list[str] = []
        current_article: str | None = None
        current_article_kind: str | None = None
        article_body_segments: list[str] = []
        article_has_structure = False
        detected_legal_structure = False

        index = 0
        while index < len(segments):
            segment = segments[index]

            heading_kind, _ = self.match_heading(segment)
            if heading_kind is not None:
                if current_article is not None:
                    chunks.extend(self.emit_article_chunks(context, current_article, article_body_segments, article_has_structure))
                    current_article = None
                    current_article_kind = None
                    article_body_segments = []
                    article_has_structure = False
                elif preamble_segments:
                    chunks.extend(self.emit_preamble_chunks(context, preamble_segments))
                    preamble_segments = []

                heading_text, consumed = self.consume_heading_with_optional_title(segment, segments, index)
                context[heading_kind] = heading_text
                detected_legal_structure = True
                index += consumed
                continue

            if self.is_article_heading(segment) or self.is_roman_article_heading(segment) or (current_article is None and self.is_outline_article_heading(segment)):
                if current_article is not None:
                    chunks.extend(self.emit_article_chunks(context, current_article, article_body_segments, article_has_structure))
                elif preamble_segments:
                    chunks.extend(self.emit_preamble_chunks(context, preamble_segments))
                    preamble_segments = []

                current_article, current_article_kind, consumed = self.consume_article_heading(segment, segments, index)
                article_body_segments = []
                article_has_structure = False
                detected_legal_structure = True
                index += consumed
                continue

            if current_article_kind == "outline" and self.is_outline_article_heading(segment):
                chunks.extend(self.emit_article_chunks(context, current_article or "", article_body_segments, article_has_structure))
                current_article, current_article_kind, consumed = self.consume_article_heading(segment, segments, index)
                article_body_segments = []
                article_has_structure = False
                detected_legal_structure = True
                index += consumed
                continue

            if current_article is None:
                preamble_segments.append(segment)
            else:
                if self.is_clause_heading(segment) or self.is_point_heading(segment):
                    article_has_structure = True
                article_body_segments.append(segment)

            index += 1

        if current_article is not None:
            chunks.extend(self.emit_article_chunks(context, current_article, article_body_segments, article_has_structure))
        elif preamble_segments:
            chunks.extend(self.emit_preamble_chunks(context, preamble_segments))

        return chunks if detected_legal_structure else []

    def emit_preamble_chunks(self, context: dict[str, str | None], preamble_segments: list[str]) -> list[tuple[str | None, str]]:
        title = self.truncate_title(" | ".join(part for part in [context["part"], context["chapter"], context["section"]] if part) or (preamble_segments[0] if preamble_segments else "Preamble"))
        return self.materialize_unit(title, self.context_prefix_lines(context), preamble_segments)

    def emit_article_chunks(self, context: dict[str, str | None], article_heading: str, body_segments: list[str], article_has_structure: bool) -> list[tuple[str | None, str]]:
        if not body_segments:
            return self.materialize_unit(self.truncate_title(article_heading), self.context_prefix_lines(context), [article_heading])

        clause_groups: list[tuple[str, list[str]]] = []
        article_intro: list[str] = []
        current_clause_heading: str | None = None
        current_clause_body: list[str] = []

        for segment in body_segments:
            if self.is_clause_heading(segment):
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

        chunk_payloads: list[tuple[str | None, str]] = []
        article_prefix = self.context_prefix_lines(context)

        if article_intro:
            chunk_payloads.extend(self.materialize_unit(self.truncate_title(article_heading), article_prefix, [article_heading, *article_intro]))

        if not clause_groups:
            return self.materialize_unit(self.truncate_title(article_heading), article_prefix, [article_heading, *body_segments])

        for clause_heading, clause_body in clause_groups:
            chunk_payloads.extend(self.emit_clause_chunks(article_prefix, article_heading, clause_heading, clause_body))

        if not chunk_payloads and article_has_structure:
            return self.materialize_unit(self.truncate_title(article_heading), article_prefix, [article_heading, *body_segments])
        return chunk_payloads

    def emit_clause_chunks(self, article_prefix: list[str], article_heading: str, clause_heading: str, clause_body: list[str]) -> list[tuple[str | None, str]]:
        point_groups: list[tuple[str, list[str]]] = []
        clause_intro: list[str] = []
        current_point_heading: str | None = None
        current_point_body: list[str] = []

        for segment in clause_body:
            if self.is_point_heading(segment):
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

        prefix_lines = [*article_prefix, article_heading]
        clause_title = self.truncate_title(f"{self.article_reference(article_heading)} | Khoản {self.extract_clause_number(clause_heading) or '?'}")
        chunk_payloads: list[tuple[str | None, str]] = []

        if clause_intro:
            chunk_payloads.extend(self.materialize_unit(clause_title, prefix_lines, [clause_heading, *clause_intro]))

        if not point_groups:
            return self.materialize_unit(clause_title, prefix_lines, [clause_heading, *clause_body])

        for point_heading, point_body in point_groups:
            point_title = self.truncate_title(f"{clause_title} | Điểm {self.extract_point_label(point_heading) or '?'}")
            chunk_payloads.extend(self.materialize_unit(point_title, [*prefix_lines, clause_heading], [point_heading, *point_body]))

        return chunk_payloads

    def materialize_unit(self, section_title: str | None, prefix_lines: list[str], body_segments: list[str]) -> list[tuple[str | None, str]]:
        clean_body_segments = [self.normalize_segment(segment) for segment in body_segments if self.normalize_segment(segment)]
        if not clean_body_segments:
            return []

        prefix_text = "\n".join(line for line in prefix_lines if line)
        body_text = "\n".join(clean_body_segments)
        combined = "\n".join(part for part in [prefix_text, body_text] if part)
        return [(section_title, combined)]

    def context_prefix_lines(self, context: dict[str, str | None]) -> list[str]:
        return [value for value in [context["part"], context["chapter"], context["section"]] if value]

    def match_heading(self, segment: str) -> tuple[str | None, str | None]:
        for kind, pattern in (("part", PART_PATTERN), ("chapter", CHAPTER_PATTERN), ("section", SECTION_PATTERN)):
            match = pattern.match(segment)
            if match:
                captured = match.group(0).strip() if len(match.groups()) > 1 else match.group(1).strip()
                return kind, captured
        return None, None

    def consume_heading_with_optional_title(self, segment: str, segments: list[str], index: int) -> tuple[str, int]:
        heading_kind, _ = self.match_heading(segment)
        if heading_kind is None:
            return segment, 1

        if index + 1 < len(segments) and self.is_heading_title_candidate(segments[index + 1]):
            return f"{segment} {segments[index + 1]}", 2
        return segment, 1

    def consume_article_heading(self, segment: str, segments: list[str], index: int) -> tuple[str, str, int]:
        match = ARTICLE_PATTERN.match(segment)
        if match is not None:
            _, article_number, article_title = match.groups()
            article_title = article_title.strip()
            if article_title:
                return f"Điều {article_number}. {article_title}", "standard", 1
            if index + 1 < len(segments) and self.is_heading_title_candidate(segments[index + 1]):
                return f"Điều {article_number}. {segments[index + 1]}", "standard", 2
            return f"Điều {article_number}", "standard", 1

        roman_match = ROMAN_ARTICLE_PATTERN.match(segment)
        if roman_match is not None:
            article_number, article_title = roman_match.groups()
            article_title = article_title.strip()
            normalized_heading = f"{article_number.upper()}."
            if article_title:
                normalized_heading = f"{normalized_heading} {article_title}"
            elif index + 1 < len(segments) and self.is_heading_title_candidate(segments[index + 1]):
                normalized_heading = f"{normalized_heading} {segments[index + 1]}"
                return normalized_heading, "roman", 2
            return normalized_heading, "roman", 1

        outline_match = OUTLINE_ARTICLE_PATTERN.match(segment)
        if outline_match is not None:
            article_number, article_title = outline_match.groups()
            return f"{article_number}. {article_title.strip()}".strip(), "outline", 1

        return segment, "standard", 1

    def is_heading_title_candidate(self, segment: str) -> bool:
        if len(segment) > LEGAL_TITLE_MAX_CHARS:
            return False
        if self.match_heading(segment)[0] is not None:
            return False
        return not self.is_article_heading(segment) and not self.is_clause_heading(segment) and not self.is_point_heading(segment)

    def is_article_heading(self, segment: str) -> bool:
        return ARTICLE_PATTERN.match(segment) is not None

    def is_roman_article_heading(self, segment: str) -> bool:
        return ROMAN_ARTICLE_PATTERN.match(segment) is not None

    def is_outline_article_heading(self, segment: str) -> bool:
        match = OUTLINE_ARTICLE_PATTERN.match(segment)
        return match is not None and len(match.group(1)) <= 3

    def is_clause_heading(self, segment: str) -> bool:
        clause_match = CLAUSE_PATTERN.match(segment)
        if clause_match is not None and len(clause_match.group(2)) <= 3:
            return True
        return DECIMAL_CLAUSE_PATTERN.match(segment) is not None

    def is_point_heading(self, segment: str) -> bool:
        return POINT_PATTERN.match(segment) is not None

    def article_reference(self, article_heading: str) -> str:
        match = ARTICLE_PATTERN.match(article_heading)
        if match:
            return f"Điều {match.group(2)}"
        roman_match = ROMAN_ARTICLE_PATTERN.match(article_heading)
        if roman_match:
            return f"{roman_match.group(1).upper()}."
        outline_match = OUTLINE_ARTICLE_PATTERN.match(article_heading)
        if outline_match:
            return f"{outline_match.group(1)}."
        return article_heading.split(".", maxsplit=1)[0].strip()

    def extract_clause_number(self, clause_heading: str) -> str | None:
        match = CLAUSE_PATTERN.match(clause_heading)
        if match:
            return match.group(2)
        decimal_match = DECIMAL_CLAUSE_PATTERN.match(clause_heading)
        return decimal_match.group(1) if decimal_match else None

    def extract_point_label(self, point_heading: str) -> str | None:
        match = POINT_PATTERN.match(point_heading)
        return match.group(2) if match else None

    def truncate_title(self, value: str | None) -> str | None:
        if not value:
            return None
        return value[:255]

    def build_fallback_chunks(self, segments: list[str]) -> list[tuple[str | None, str]]:
        prepared_segments: list[str] = []
        for segment in segments:
            prepared_segments.extend(self.split_segment_for_fallback(segment))

        if not prepared_segments:
            return []

        chunks: list[str] = []
        current_segments: list[str] = []

        for segment in prepared_segments:
            current_word_count = self.joined_word_count(current_segments)
            segment_word_count = self.word_count(segment)
            should_flush = bool(current_segments) and (
                current_word_count + segment_word_count > FALLBACK_MAX_WORDS
                or (current_word_count >= FALLBACK_TARGET_WORDS and self.is_fallback_boundary(segment))
            )

            if should_flush:
                chunks.append("\n".join(current_segments))
                current_segments = current_segments[-FALLBACK_OVERLAP_SEGMENTS:] if current_segments else []

            current_segments.append(segment)

        if current_segments:
            chunks.append("\n".join(current_segments))

        return [(self.detect_section_title(chunk), chunk) for chunk in chunks]

    def split_segment_for_fallback(self, segment: str) -> list[str]:
        normalized = self.normalize_segment(segment)
        if not normalized:
            return []
        if self.word_count(normalized) <= FALLBACK_MAX_WORDS:
            return [normalized]

        sentence_like_segments = [
            self.normalize_segment(part)
            for part in SENTENCE_BOUNDARY_PATTERN.split(normalized)
            if self.normalize_segment(part)
        ]
        if len(sentence_like_segments) > 1:
            expanded_segments: list[str] = []
            for sentence in sentence_like_segments:
                expanded_segments.extend(self.split_segment_for_fallback(sentence))
            return expanded_segments

        words = normalized.split()
        fallback_segments: list[str] = []
        current_words: list[str] = []
        for word in words:
            candidate = " ".join([*current_words, word])
            if current_words and self.word_count(candidate) > FALLBACK_MAX_WORDS:
                fallback_segments.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)
        if current_words:
            fallback_segments.append(" ".join(current_words))
        return fallback_segments

    def joined_word_count(self, segments: list[str]) -> int:
        return sum(self.word_count(segment) for segment in segments)

    def word_count(self, text: str) -> int:
        return len([token for token in text.split() if token])

    def is_fallback_boundary(self, segment: str) -> bool:
        if self.match_heading(segment)[0] is not None:
            return True
        if self.is_article_heading(segment) or self.is_clause_heading(segment) or self.is_point_heading(segment):
            return True
        if len(segment) <= LEGAL_TITLE_MAX_CHARS and segment.isupper():
            return True
        return segment.endswith(":")

    def detect_section_title(self, chunk: str) -> str | None:
        first_sentence = chunk.split(".", maxsplit=1)[0].strip()
        if len(first_sentence) < 12:
            return None
        return first_sentence[:120]

    def build_chunk_metadata_payload(self, document: Document, section_title: str | None, content: str) -> dict[str, str | None]:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        headings = [line for line in lines if self.match_heading(line)[0] is not None]
        article_heading = next((line for line in lines if self.is_article_heading(line)), None)
        clause_heading = next((line for line in lines if self.is_clause_heading(line)), None)
        point_heading = next((line for line in lines if self.is_point_heading(line)), None)

        article_number = self.extract_article_number(article_heading)
        clause_number = self.extract_clause_number(clause_heading) if clause_heading else None
        point_number = self.extract_point_label(point_heading) if point_heading else None

        if point_number:
            chunk_type = "point"
        elif clause_number:
            chunk_type = "clause"
        elif article_number:
            chunk_type = "article"
        else:
            chunk_type = "preamble"

        citation_parts: list[str] = []
        if article_number:
            citation_parts.append(f"Điều {article_number}")
        if clause_number:
            citation_parts.append(f"Khoản {clause_number}")
        if point_number:
            citation_parts.append(f"Điểm {point_number}")
        citation_label = " ".join(citation_parts) or section_title or "Preamble"
        article_ref = f"Điều {article_number}" if article_number else None

        path_parts = [self.slugify_path_component(heading) for heading in headings if heading]
        if article_number:
            path_parts.append(f"dieu-{article_number.lower()}")
        if clause_number:
            path_parts.append(f"khoan-{clause_number.lower()}")
        if point_number:
            path_parts.append(f"diem-{point_number.lower()}")
        hierarchy_path = "/".join(part for part in path_parts if part) or self.slugify_path_component(section_title or "preamble")

        parent_context = {
            "document_title": document.title,
            "part": next((line for line in headings if PART_PATTERN.match(line)), None),
            "chapter": next((line for line in headings if CHAPTER_PATTERN.match(line)), None),
            "section": next((line for line in headings if SECTION_PATTERN.match(line)), None),
            "article_heading": article_heading,
            "clause_heading": clause_heading,
            "point_heading": point_heading,
        }
        structured_section = parent_context["section"] or parent_context["chapter"] or parent_context["part"] or article_heading
        structured_subsection = point_heading or clause_heading
        metadata_chunk_id = self.build_chunk_identifier(document, article_number, clause_number, point_number, chunk_type)
        token_count = self.word_count(content)

        retrieval_text = " ".join(part for part in [
            document.title,
            document.document_code,
            parent_context["part"],
            parent_context["chapter"],
            parent_context["section"],
            article_heading,
            clause_heading,
            point_heading,
            section_title,
            citation_label,
            " ".join(lines),
        ] if part)
        metadata_json = json.dumps(
            {
                "chunk_id": metadata_chunk_id,
                "document_code": document.document_code,
                "title": document.title,
                "section": structured_section,
                "subsection": structured_subsection,
                "article_ref": article_ref,
                "token_count": token_count,
                "heading_path": headings,
                "parent_context": parent_context,
                "legal_domain": document.legal_domain,
                "document_type": document.document_type,
                "legal_status": document.legal_status,
                "document_title": document.title,
            },
            ensure_ascii=False,
        )
        return {
            "chunk_type": chunk_type,
            "citation_label": citation_label[:255],
            "hierarchy_path": hierarchy_path[:1000],
            "article_number": article_number,
            "clause_number": clause_number,
            "point_number": point_number,
            "retrieval_text": retrieval_text,
            "metadata_json": metadata_json,
        }

    def build_chunk_identifier(self, document: Document, article_number: str | None, clause_number: str | None, point_number: str | None, chunk_type: str) -> str:
        document_key = self.slugify_path_component(document.document_code or document.file_name or document.title or str(document.id)) or str(document.id)
        path_parts = [document_key]
        if article_number:
            path_parts.append(f"dieu-{article_number}")
        if clause_number:
            path_parts.append(f"khoan-{clause_number}")
        if point_number:
            path_parts.append(f"diem-{point_number}")
        if len(path_parts) == 1:
            path_parts.append(chunk_type)
        return "_".join(path_parts)

    def extract_article_number(self, article_heading: str | None) -> str | None:
        if not article_heading:
            return None
        match = ARTICLE_PATTERN.match(article_heading)
        return match.group(2) if match else None

    def slugify_path_component(self, value: str) -> str:
        normalized = self.normalize_text(value)
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        return normalized.strip("-")[:120]

    def normalize_segment(self, value: str) -> str:
        return document_text_extractor.normalize_segment(value)

    def normalize_text(self, text: str) -> str:
        lowered = text.lower().replace("đ", "d")
        decomposed = unicodedata.normalize("NFD", lowered)
        stripped = "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
        return re.sub(r"\s+", " ", stripped).strip()


legal_chunk_builder = LegalChunkBuilder()
