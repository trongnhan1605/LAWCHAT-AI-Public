from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from src.models.document import Document
from src.tools.check_validity import evaluate_document_validity
from src.tools.get_related_articles import RelatedArticleResult
from src.tools.search_law import SearchLawResult
from src.validation.legal_response_validator import validate_legal_response


@dataclass(frozen=True)
class CoordinatedValidationResult:
    validation_status: str
    confidence_score: float
    escalation_recommended: bool
    warning_text: str | None
    findings: list[str]
    authoritative_result_count: int
    citation_coverage_score: float
    related_article_count: int
    semantic_match_count: int
    semantic_edge_count: int
    legal_claim_count: int = 0
    claim_citation_support_score: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


class LegalValidationCoordinator:
    def evaluate(
        self,
        *,
        retrieved_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        unresolved_conflict: bool,
        detected_complexity: str,
        related_articles: list[RelatedArticleResult],
        semantic_graph: dict[str, object] | None = None,
        response_text: str | None = None,
    ) -> CoordinatedValidationResult:
        authoritative_result_count = 0
        citation_integrity_findings: list[str] = []
        legal_status_findings: list[str] = []

        for result in retrieved_results:
            document = evidence_documents.get(result.document_id)
            if document is None:
                citation_integrity_findings.append(f"Citation references missing document id {result.document_id}.")
                continue
            validity = evaluate_document_validity(document)
            if validity.is_authoritative:
                authoritative_result_count += 1
            if not result.chunk_id:
                citation_integrity_findings.append(f"Citation for document id {result.document_id} is missing chunk/provision reference.")
            if not result.citation_label:
                citation_integrity_findings.append(f"Citation for document id {result.document_id} is missing citation label.")
            if not result.source_reference:
                citation_integrity_findings.append(f"Citation for document id {result.document_id} is missing source reference.")
            status = (document.legal_status or "").strip().lower()
            if not status:
                legal_status_findings.append(f"Document id {document.id} is missing legal_status metadata.")
            elif status in {"unknown", "draft"}:
                legal_status_findings.append(f"Document id {document.id} has non-authoritative legal_status={status}.")
            elif not validity.is_authoritative:
                legal_status_findings.append(f"Document id {document.id} is not authoritative: {'; '.join(validity.reasons)}")
            if document.effective_date is None:
                legal_status_findings.append(f"Document id {document.id} is missing effective_date metadata.")

        base = validate_legal_response(
            retrieved_results=retrieved_results,
            authoritative_result_count=authoritative_result_count,
            unresolved_conflict=unresolved_conflict,
            detected_complexity=detected_complexity,
        )

        citation_ready_count = sum(
            1
            for item in retrieved_results
            if item.document_id in evidence_documents and item.chunk_id and item.citation_label and item.source_reference
        )
        citation_coverage_score = 1.0 if not retrieved_results else round(citation_ready_count / len(retrieved_results), 4)
        findings = list(base.findings)
        confidence_score = base.confidence_score
        semantic_match_count = len(semantic_graph.get("matched_concepts", [])) if semantic_graph else 0
        semantic_edge_count = len(semantic_graph.get("edges", [])) if semantic_graph else 0

        if retrieved_results and citation_coverage_score < 1.0:
            findings.append("Some retrieved evidence is missing complete citation integrity metadata.")
            findings.extend(citation_integrity_findings[:6])
            confidence_score = max(0.28, round(confidence_score - 0.08, 4))

        if legal_status_findings:
            findings.extend(legal_status_findings[:6])
            confidence_score = max(0.28, round(confidence_score - 0.06, 4))

        if semantic_match_count >= 2 and semantic_edge_count > 0:
            findings.append("Semantic concept path was found to support multi-hop legal reasoning.")
            confidence_score = min(0.94, round(confidence_score + 0.04, 4))
        elif detected_complexity == "high" and semantic_match_count == 0:
            findings.append("High-complexity case has no semantic path support yet.")
            confidence_score = max(0.28, round(confidence_score - 0.05, 4))

        response_consistency_findings = self._check_response_consistency(
            response_text=response_text,
            retrieved_results=retrieved_results,
            evidence_documents=evidence_documents,
            unresolved_conflict=unresolved_conflict,
        )
        if response_consistency_findings:
            findings.extend(response_consistency_findings)
            confidence_score = max(0.28, round(confidence_score - (0.07 * len(response_consistency_findings)), 4))

        legal_claims = self._extract_legal_claims(response_text)
        claim_support_score, unsupported_claims = self._score_claim_citation_support(
            legal_claims=legal_claims,
            retrieved_results=retrieved_results,
        )
        if legal_claims and claim_support_score < 1.0:
            findings.append(
                f"Claim-citation-excerpt support is incomplete: {round(claim_support_score * 100)}% of detected legal claims have direct citation/excerpt support."
            )
            findings.extend([f"Unsupported legal claim excerpt: {claim}" for claim in unsupported_claims[:3]])
            confidence_score = max(0.28, round(confidence_score - 0.08, 4))

        warning_text = base.warning_text
        validation_status = base.validation_status
        escalation_recommended = base.escalation_recommended
        if (confidence_score < 0.62 or (legal_claims and claim_support_score < 0.75)) and not escalation_recommended:
            escalation_recommended = True
            validation_status = "needs_review"
            warning_text = "Kết quả hiện cần được tư vấn viên hoặc bộ phận pháp lý rà soát thêm trước khi dùng để ra quyết định."

        return CoordinatedValidationResult(
            validation_status=validation_status,
            confidence_score=confidence_score,
            escalation_recommended=escalation_recommended,
            warning_text=warning_text,
            findings=findings,
            authoritative_result_count=authoritative_result_count,
            citation_coverage_score=citation_coverage_score,
            related_article_count=len(related_articles),
            semantic_match_count=semantic_match_count,
            semantic_edge_count=semantic_edge_count,
            legal_claim_count=len(legal_claims),
            claim_citation_support_score=claim_support_score,
        )

    def _check_response_consistency(
        self,
        *,
        response_text: str | None,
        retrieved_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        unresolved_conflict: bool,
    ) -> list[str]:
        if response_text is None:
            return []

        normalized_response = response_text.lower()
        findings: list[str] = []

        if retrieved_results and "căn cứ" not in normalized_response and "can cu" not in normalized_response:
            findings.append("Response text does not expose a legal basis section despite retrieved evidence.")

        missing_citation_labels = [
            result.citation_label
            for result in retrieved_results[:3]
            if result.citation_label and result.citation_label.lower() not in normalized_response
        ]
        if missing_citation_labels:
            findings.append("Response text omits top citation labels: " + ", ".join(missing_citation_labels[:3]) + ".")

        non_authoritative_documents = []
        for result in retrieved_results:
            document = evidence_documents.get(result.document_id)
            if document is None:
                continue
            validity = evaluate_document_validity(document)
            if not validity.is_authoritative:
                non_authoritative_documents.append(document.id)
        if non_authoritative_documents and not any(term in normalized_response for term in {"hết hiệu lực", "het hieu luc", "không còn", "khong con", "cảnh báo", "canh bao"}):
            findings.append("Response uses non-authoritative evidence without an explicit legal-status warning.")

        if unresolved_conflict and not any(term in normalized_response for term in {"xung đột", "xung dot", "mâu thuẫn", "mau thuan"}):
            findings.append("Response does not disclose unresolved conflict detected by deterministic tools.")

        return findings

    def _extract_legal_claims(self, response_text: str | None) -> list[str]:
        if not response_text:
            return []
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?。])\s+|\n+", response_text) if sentence.strip()]
        citation_cues = {
            "điều",
            "dieu",
            "khoản",
            "khoan",
            "luật",
            "luat",
            "nghị định",
            "nghi dinh",
            "thông tư",
            "thong tu",
            "quy định",
            "quy dinh",
            "căn cứ",
            "can cu",
        }
        normative_cues = {
            "nghĩa vụ",
            "nghia vu",
            "trách nhiệm",
            "trach nhiem",
            "quyền",
            "quyen",
            "bị cấm",
            "bi cam",
            "không được",
            "khong duoc",
            "cấp giấy",
            "cap giay",
            "thu hồi",
            "thu hoi",
            "bồi thường",
            "boi thuong",
        }
        claims: list[str] = []
        for sentence in sentences:
            normalized = sentence.lower()
            if self._is_non_claim_sentence(normalized):
                continue
            if any(cue in normalized for cue in citation_cues) or any(cue in normalized for cue in normative_cues):
                claims.append(sentence[:280])
        return claims

    def _is_non_claim_sentence(self, normalized_sentence: str) -> bool:
        value = normalized_sentence.strip().strip(":")
        if value in {"căn cứ", "can cu", "phân tích", "phan tich", "kết luận", "ket luan", "khuyến nghị", "khuyen nghi"}:
            return True
        if value.startswith(("kết quả có căn cứ", "ket qua co can cu")):
            return True
        return False

    def _score_claim_citation_support(
        self,
        *,
        legal_claims: list[str],
        retrieved_results: list[SearchLawResult],
    ) -> tuple[float, list[str]]:
        if not legal_claims:
            return 1.0, []
        if not retrieved_results:
            return 0.0, legal_claims

        evidence_texts = [
            " ".join(
                part
                for part in (
                    result.citation_label,
                    result.hierarchy_path,
                    result.document_title,
                    result.excerpt,
                )
                if part
            )
            for result in retrieved_results
        ]
        supported = 0
        unsupported: list[str] = []
        for claim in legal_claims:
            if any(self._claim_supported_by_evidence(claim, evidence_text) for evidence_text in evidence_texts):
                supported += 1
            else:
                unsupported.append(claim)
        return round(supported / len(legal_claims), 4), unsupported

    def _claim_supported_by_evidence(self, claim: str, evidence_text: str) -> bool:
        claim_tokens = self._significant_tokens(claim)
        evidence_tokens = self._significant_tokens(evidence_text)
        if not claim_tokens or not evidence_tokens:
            return False
        if claim_tokens & evidence_tokens and self._citation_label_overlap(claim, evidence_text):
            return True
        overlap = claim_tokens & evidence_tokens
        return len(overlap) >= min(4, max(2, len(claim_tokens) // 3))

    def _citation_label_overlap(self, claim: str, evidence_text: str) -> bool:
        claim_refs = set(re.findall(r"(?:điều|dieu|khoản|khoan)\s+\d+[a-z]?", claim.lower()))
        if not claim_refs:
            return False
        evidence = evidence_text.lower()
        return any(ref in evidence for ref in claim_refs)

    def _significant_tokens(self, value: str) -> set[str]:
        stop_words = {
            "cua",
            "của",
            "theo",
            "duoc",
            "được",
            "phai",
            "phải",
            "khong",
            "không",
            "trong",
            "cho",
            "voi",
            "với",
            "cac",
            "các",
            "mot",
            "một",
            "nhung",
            "những",
            "quy",
            "dinh",
            "định",
        }
        tokens = set(re.findall(r"[0-9a-zA-ZÀ-ỹ]{3,}", value.lower()))
        return {token for token in tokens if token not in stop_words}


legal_validation_coordinator = LegalValidationCoordinator()
