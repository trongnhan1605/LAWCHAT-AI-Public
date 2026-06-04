from __future__ import annotations

from decimal import Decimal
import json
import re
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.exceptions import AuthorizationException, NotFoundException
from src.core.logging import logger
from src.models.case_fact import CaseFact
from src.models.chat import ChatMessage, ChatSession
from src.models.citation import Citation
from src.models.legal_case import LegalCase
from src.models.ticket import Ticket
from src.orchestration.input_understanding import (
    CATEGORY_DISPLAY_NAMES,
    CATEGORY_RETRIEVAL_HINTS,
    legal_input_understanding,
    normalize_legal_text,
)
from src.orchestration.case_state import legal_case_state_updater
from src.orchestration.planner_lifecycle import planner_run_lifecycle
from src.orchestration.reasoning_lifecycle import reasoning_run_lifecycle
from src.orchestration.tool_execution import legal_tool_executor
from src.orchestration.validation_lifecycle import validation_run_lifecycle
from src.services.knowledge_service import knowledge_service
from src.tools.check_validity import evaluate_document_validity
from src.tools.search_law import SearchLawResult


class ChatService:
    def create_session(self, db: Session, *, session_type: str = "public", user_id: int | None = None) -> ChatSession:
        session = ChatSession(session_token=uuid4().hex, status="active", session_type=session_type, user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def get_or_create_latest_customer_session(self, db: Session, user_id: int) -> ChatSession:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.session_type == "customer")
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
            .first()
        )
        if session is not None:
            return session
        return self.create_session(db, session_type="customer", user_id=user_id)

    def get_session(self, db: Session, session_token: str, current_user=None) -> ChatSession:
        session = db.query(ChatSession).filter(ChatSession.session_token == session_token).first()
        if session is None:
            raise NotFoundException("Chat session not found")
        self._ensure_session_access(session, current_user)
        return session

    def list_messages(self, db: Session, session_id: int) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .all()
        )

    def ask(self, db: Session, session_token: str, content: str, current_user=None) -> tuple[ChatSession, ChatMessage, ChatMessage]:
        try:
            return self._ask_with_pipeline(db, session_token, content, current_user)
        except Exception as exc:
            logger.exception("Chat pipeline failed; returning demo-safe fallback answer")
            db.rollback()
            return self._ask_with_demo_fallback(db, session_token, content, current_user, exc)

    def _ask_with_pipeline(self, db: Session, session_token: str, content: str, current_user=None) -> tuple[ChatSession, ChatMessage, ChatMessage]:
        session = self.get_session(db, session_token, current_user)
        input_understanding = legal_input_understanding.analyze(content)
        detected_domain = input_understanding.detected_domain
        detected_intent = input_understanding.detected_intent
        complexity_level = input_understanding.complexity_level

        active_case = self._get_or_create_active_case(
            db,
            session=session,
            content=content,
            detected_domain=detected_domain,
            complexity_level=complexity_level,
        )

        planner_run = planner_run_lifecycle.create(
            db,
            legal_case=active_case,
            session=session,
            query_text=content,
            detected_intent=detected_intent,
            detected_domain=detected_domain,
            complexity_level=complexity_level,
        )

        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            message_type="question",
            content=content,
            category_slug=detected_domain,
            needs_escalation=False,
        )
        db.add(user_message)
        db.flush()
        self._capture_case_facts(db, active_case, user_message, content, detected_domain)

        preferred_terms = CATEGORY_RETRIEVAL_HINTS.get(detected_domain, [])
        tool_result = legal_tool_executor.execute(db, content=content, preferred_terms=preferred_terms, legal_domain=detected_domain)
        search_results = tool_result.search_results
        related_articles = tool_result.related_articles
        evidence_documents = tool_result.evidence_documents
        semantic_graph = tool_result.semantic_graph
        conflict_result = tool_result.conflict_result
        unresolved_conflict = tool_result.unresolved_conflict

        reasoning_run = reasoning_run_lifecycle.build_and_persist(
            db,
            case_id=active_case.id,
            planner_run_id=planner_run.id,
            session_id=session.id,
            content=content,
            domain_slug=detected_domain,
            intent=detected_intent,
            tool_result=tool_result,
        )

        validation_result = validation_run_lifecycle.evaluate(tool_result=tool_result, detected_complexity=complexity_level)

        assistant_text = self._build_answer(
            content=content,
            domain_slug=detected_domain,
            intent=detected_intent,
            complexity_level=complexity_level,
            search_results=search_results,
            evidence_documents=evidence_documents,
            related_articles=related_articles,
            conflict_result=conflict_result,
            semantic_graph=semantic_graph,
            validation_warning=validation_result.warning_text,
        )

        validation_result = validation_run_lifecycle.evaluate(
            tool_result=tool_result,
            detected_complexity=complexity_level,
            response_text=assistant_text,
        )

        validation_run = validation_run_lifecycle.persist(
            db,
            case_id=active_case.id,
            planner_run_id=planner_run.id,
            reasoning_run=reasoning_run,
            response_text=assistant_text,
            validation_result=validation_result,
        )

        top_citation = search_results[0] if search_results else None
        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            message_type="answer",
            content=assistant_text,
            category_slug=detected_domain,
            confidence_score=Decimal(str(validation_result.confidence_score)),
            warning_text=validation_result.warning_text,
            citation_title=top_citation.document_title if top_citation else None,
            citation_source=self._build_primary_citation_source(top_citation),
            needs_escalation=validation_result.escalation_recommended,
        )
        db.add(assistant_message)
        db.flush()

        for result in search_results:
            db.add(
                Citation(
                    planner_run_id=planner_run.id,
                    reasoning_run_id=reasoning_run.id,
                    validation_run_id=validation_run.id,
                    chat_message_id=assistant_message.id,
                    document_id=result.document_id,
                    chunk_id=result.chunk_id,
                    citation_type="legal_basis",
                    document_title=result.document_title,
                    citation_label=result.citation_label,
                    hierarchy_path=result.hierarchy_path,
                    source_reference=result.source_reference,
                    excerpt=result.excerpt,
                    metadata_json=json.dumps({"score": result.score}, ensure_ascii=False),
                )
            )

        planner_run_lifecycle.complete(
            planner_run,
            case_id=active_case.id,
            detected_intent=detected_intent,
            detected_domain=detected_domain,
            complexity_level=complexity_level,
            search_result_count=len(search_results),
            has_related_articles=bool(related_articles),
            authoritative_result_count=validation_result.authoritative_result_count,
            citation_coverage_score=validation_result.citation_coverage_score,
            related_article_count=validation_result.related_article_count,
            semantic_match_count=len(semantic_graph.get("matched_concepts", [])),
            semantic_edge_count=len(semantic_graph.get("edges", [])),
            semantic_validation_matches=validation_result.semantic_match_count,
            unresolved_conflict=unresolved_conflict,
            validation_status=validation_result.validation_status,
            escalation_recommended=validation_result.escalation_recommended,
        )

        legal_case_state_updater.apply_answer_outcome(
            session=session,
            legal_case=active_case,
            detected_domain=detected_domain,
            complexity_level=complexity_level,
            case_summary=self._build_case_summary(content, detected_domain, detected_intent, search_results),
            structured_facts=self._snapshot_case_facts(db, active_case.id),
            validation_result=validation_result,
        )

        db.commit()
        db.refresh(session)
        db.refresh(user_message)
        db.refresh(assistant_message)
        return session, user_message, assistant_message

    def _ask_with_demo_fallback(self, db: Session, session_token: str, content: str, current_user=None, exc: Exception | None = None) -> tuple[ChatSession, ChatMessage, ChatMessage]:
        session = self.get_session(db, session_token, current_user)
        input_understanding = legal_input_understanding.analyze(content)
        detected_domain = input_understanding.detected_domain

        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            message_type="question",
            content=content,
            category_slug=detected_domain,
            needs_escalation=False,
        )
        db.add(user_message)
        db.flush()

        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            message_type="answer",
            content=self._build_demo_answer(content, detected_domain),
            category_slug=detected_domain,
            confidence_score=Decimal("0.42"),
            warning_text="Demo fallback: kho tri thức hoặc pipeline xử lý chính chưa sẵn sàng trong môi trường hiện tại.",
            citation_title=None,
            citation_source=None,
            needs_escalation=True,
        )
        db.add(assistant_message)

        session.topic_guess = detected_domain
        session.last_confidence_score = Decimal("0.42")
        session.status = "active"
        db.commit()
        db.refresh(session)
        db.refresh(user_message)
        db.refresh(assistant_message)
        return session, user_message, assistant_message

    def escalate(self, db: Session, session_token: str, reason: str, current_user=None) -> Ticket:
        session = self.get_session(db, session_token, current_user)
        if session.escalated_ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == session.escalated_ticket_id).first()
            if ticket is not None:
                return ticket

        ticket = Ticket(
            session_id=session.id,
            case_id=self._get_active_case_id(db, session.id),
            title=f"Tư vấn viên hỗ trợ phiên {session.session_token[:8]}",
            topic=session.topic_guess,
            escalation_reason=reason,
            confidence_score=session.last_confidence_score,
            status="new",
            priority="high" if session.last_confidence_score and float(session.last_confidence_score) < 0.5 else "normal",
        )
        db.add(ticket)
        db.flush()

        session.escalated_ticket_id = ticket.id
        session.status = "escalated"
        db.commit()
        db.refresh(ticket)
        return ticket

    def _ensure_session_access(self, session: ChatSession, current_user) -> None:
        if (session.session_type or "public") == "public":
            return
        if current_user is None:
            raise AuthorizationException("Authentication is required to access this chat session")
        if session.user_id is not None and session.user_id != current_user.id:
            raise AuthorizationException("You do not have permission to access this chat session")

    def _classify_category(self, normalized_content: str) -> str:
        return legal_input_understanding.classify_category(normalized_content)

    def _detect_intent(self, normalized_content: str) -> str:
        return legal_input_understanding.detect_intent(normalized_content)

    def _score_complexity(self, normalized_content: str) -> str:
        return legal_input_understanding.score_complexity(normalized_content)

    def _get_active_case_id(self, db: Session, session_id: int) -> int | None:
        active_case = (
            db.query(LegalCase)
            .filter(LegalCase.session_id == session_id)
            .order_by(LegalCase.updated_at.desc(), LegalCase.id.desc())
            .first()
        )
        return active_case.id if active_case is not None else None

    def _get_or_create_active_case(
        self,
        db: Session,
        *,
        session: ChatSession,
        content: str,
        detected_domain: str,
        complexity_level: str,
    ) -> LegalCase:
        active_case = (
            db.query(LegalCase)
            .filter(LegalCase.session_id == session.id)
            .order_by(LegalCase.updated_at.desc(), LegalCase.id.desc())
            .first()
        )
        if active_case is None:
            active_case = LegalCase(
                session_id=session.id,
                user_id=session.user_id,
                title=self._build_case_title(content, detected_domain),
                legal_domain=detected_domain,
                status="intake",
                risk_level=complexity_level,
                summary=self._summarize_text(content, 500),
                desired_outcome=self._detect_desired_outcome(content, detected_domain),
                intake_snapshot_json=json.dumps(
                    {
                        "initial_question": content,
                        "detected_domain": detected_domain,
                        "risk_level": complexity_level,
                    },
                    ensure_ascii=False,
                ),
            )
            db.add(active_case)
            db.flush()
            return active_case

        active_case.legal_domain = detected_domain
        active_case.risk_level = complexity_level
        active_case.title = self._build_case_title(content, detected_domain)
        active_case.desired_outcome = self._detect_desired_outcome(content, detected_domain)
        if not active_case.summary:
            active_case.summary = self._summarize_text(content, 500)
        active_case.intake_snapshot_json = json.dumps(
            {
                "latest_question": content,
                "detected_domain": detected_domain,
                "risk_level": complexity_level,
            },
            ensure_ascii=False,
        )
        return active_case

    def _capture_case_facts(self, db: Session, legal_case: LegalCase, source_message: ChatMessage, content: str, detected_domain: str) -> None:
        extracted_facts = self._extract_case_facts(content, detected_domain)
        if not extracted_facts:
            extracted_facts = [
                {
                    "fact_type": "user_statement",
                    "fact_key": "intake_summary",
                    "fact_value": self._summarize_text(content, 700),
                    "is_disputed": "tranh chap" in self._normalize_text(content),
                    "confidence_score": 0.55,
                }
            ]

        existing_pairs = {
            (item.fact_type, item.fact_key, item.fact_value.strip().lower())
            for item in db.query(CaseFact).filter(CaseFact.case_id == legal_case.id).all()
        }
        for fact in extracted_facts:
            dedupe_key = (fact["fact_type"], fact["fact_key"], fact["fact_value"].strip().lower())
            if dedupe_key in existing_pairs:
                continue
            db.add(
                CaseFact(
                    case_id=legal_case.id,
                    source_message_id=source_message.id,
                    fact_type=fact["fact_type"],
                    fact_key=fact["fact_key"],
                    fact_value=fact["fact_value"],
                    is_disputed=fact["is_disputed"],
                    confidence_score=Decimal(str(fact["confidence_score"])),
                )
            )
            existing_pairs.add(dedupe_key)

    def _extract_case_facts(self, content: str, detected_domain: str) -> list[dict[str, object]]:
        sentences = [segment.strip() for segment in re.split(r"[;\n]+", content) if segment.strip()]
        normalized = self._normalize_text(content)
        facts: list[dict[str, object]] = []

        for sentence in sentences:
            normalized_sentence = self._normalize_text(sentence)
            if len(normalized_sentence) < 8:
                continue
            if detected_domain == "hon-nhan-va-gia-dinh":
                if any(term in normalized_sentence for term in {"ly hon", "ket hon", "nuoi con", "cap duong", "tai san chung"}):
                    facts.append(
                        {
                            "fact_type": "family_issue",
                            "fact_key": "family_context",
                            "fact_value": sentence[:1000],
                            "is_disputed": "tranh chap" in normalized_sentence,
                            "confidence_score": 0.78,
                        }
                    )
            if detected_domain == "dat-dai":
                if any(term in normalized_sentence for term in {"so do", "thu hoi dat", "boi thuong", "quyen su dung dat", "tranh chap dat"}):
                    facts.append(
                        {
                            "fact_type": "land_issue",
                            "fact_key": "land_context",
                            "fact_value": sentence[:1000],
                            "is_disputed": "tranh chap" in normalized_sentence,
                            "confidence_score": 0.8,
                        }
                    )
            if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", sentence):
                facts.append(
                    {
                        "fact_type": "timeline",
                        "fact_key": "mentioned_date",
                        "fact_value": sentence[:1000],
                        "is_disputed": False,
                        "confidence_score": 0.72,
                    }
                )
            if any(term in normalized_sentence for term in {"toa an", "uy ban", "van phong dang ky", "co quan"}):
                facts.append(
                    {
                        "fact_type": "authority_interaction",
                        "fact_key": "authority_contact",
                        "fact_value": sentence[:1000],
                        "is_disputed": False,
                        "confidence_score": 0.68,
                    }
                )

        if not facts and normalized:
            facts.append(
                {
                    "fact_type": "user_statement",
                    "fact_key": "raw_problem",
                    "fact_value": content[:1000],
                    "is_disputed": "tranh chap" in normalized,
                    "confidence_score": 0.6,
                }
            )
        return facts[:8]

    def _snapshot_case_facts(self, db: Session, case_id: int) -> list[dict[str, object]]:
        case_facts = (
            db.query(CaseFact)
            .filter(CaseFact.case_id == case_id)
            .order_by(CaseFact.created_at.asc(), CaseFact.id.asc())
            .all()
        )
        return [
            {
                "id": item.id,
                "fact_type": item.fact_type,
                "fact_key": item.fact_key,
                "fact_value": item.fact_value,
                "is_disputed": item.is_disputed,
                "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
            }
            for item in case_facts
        ]

    def _build_case_title(self, content: str, detected_domain: str) -> str:
        domain_name = CATEGORY_DISPLAY_NAMES.get(detected_domain, detected_domain)
        summary = self._summarize_text(content, 120)
        return f"{domain_name}: {summary}"[:255]

    def _build_case_summary(self, content: str, detected_domain: str, intent: str, search_results: list[SearchLawResult]) -> str:
        domain_name = CATEGORY_DISPLAY_NAMES.get(detected_domain, detected_domain)
        evidence_count = len(search_results)
        return f"{domain_name} | {intent} | {self._summarize_text(content, 360)} | evidence={evidence_count}"[:2000]

    def _detect_desired_outcome(self, content: str, detected_domain: str) -> str:
        normalized = self._normalize_text(content)
        if detected_domain == "hon-nhan-va-gia-dinh":
            if "ly hon" in normalized:
                return "Làm rõ căn cứ, thủ tục hoặc hệ quả pháp lý liên quan đến ly hôn."
            if "nuoi con" in normalized:
                return "Làm rõ khả năng giành quyền nuôi con hoặc nghĩa vụ cấp dưỡng."
        if detected_domain == "dat-dai":
            if "thu hoi dat" in normalized or "boi thuong" in normalized:
                return "Làm rõ căn cứ thu hồi đất, bồi thường, hỗ trợ hoặc tái định cư."
            if "so do" in normalized:
                return "Làm rõ điều kiện, hồ sơ hoặc tranh chấp liên quan đến giấy chứng nhận."
        return "Xác định căn cứ pháp lý, mức độ rủi ro và hướng xử lý cho yêu cầu hiện tại."

    def _summarize_text(self, content: str, limit: int) -> str:
        compact = " ".join(content.split())
        return compact[:limit].strip()

    def _load_evidence_documents(self, db: Session, search_results: list[SearchLawResult]):
        return legal_tool_executor.load_evidence_documents(db, search_results)

    def _build_issue_summary(self, content: str, domain_slug: str, intent: str) -> str:
        domain_name = CATEGORY_DISPLAY_NAMES.get(domain_slug, domain_slug)
        return f"Yêu cầu thuộc nhóm {domain_name}, intent {intent}: {content.strip()}"

    def _build_reasoning_graph(
        self,
        domain_slug: str,
        intent: str,
        search_results: list[SearchLawResult],
        conflict_result,
    ) -> dict:
        graph = {
            "domain": domain_slug,
            "intent": intent,
            "nodes": [
                {"type": "issue", "label": domain_slug},
                *[
                    {"type": "evidence", "label": result.citation_label or result.document_title, "document_id": result.document_id}
                    for result in search_results[:3]
                ],
            ],
            "edges": [
                *[
                    {"from": "issue", "to": result.document_id, "type": "SUPPORTED_BY"}
                    for result in search_results[:3]
                ]
            ],
        }
        if conflict_result is not None:
            graph["conflict_resolution"] = conflict_result.to_dict()
        return graph

    def _build_evidence_summary(self, search_results: list[SearchLawResult], evidence_documents: dict[int, Document]) -> list[dict]:
        summary: list[dict] = []
        for result in search_results:
            document = evidence_documents.get(result.document_id)
            validity = evaluate_document_validity(document) if document is not None else None
            summary.append(
                {
                    "document_id": result.document_id,
                    "document_title": result.document_title,
                    "citation_label": result.citation_label,
                    "score": result.score,
                    "legal_status": result.legal_status,
                    "validity": validity.to_dict() if validity else None,
                }
            )
        return summary

    def _build_answer(
        self,
        *,
        content: str,
        domain_slug: str,
        intent: str,
        complexity_level: str,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        related_articles,
        conflict_result,
        semantic_graph,
        validation_warning: str | None,
    ) -> str:
        domain_name = CATEGORY_DISPLAY_NAMES.get(domain_slug, domain_slug)
        practical_answer = self._build_practical_checklist_answer(content, domain_slug, search_results, evidence_documents, validation_warning)
        if practical_answer:
            return practical_answer

        if not search_results:
            return (
                f"Kết luận: Chưa đủ căn cứ để kết luận chắc chắn cho vấn đề thuộc nhóm {domain_name}.\n\n"
                "Phân tích: Hệ thống chưa tìm được điều khoản hoặc văn bản đủ gần với câu hỏi hiện tại trong kho tri thức.\n\n"
                "Căn cứ: Chưa có citation phù hợp.\n\n"
                "Khuyến nghị: Cần bổ sung tình tiết cụ thể hoặc chuyển cho tư vấn viên rà soát."
            )

        top_results = search_results[:3]
        basis_lines: list[str] = []
        analysis_lines: list[str] = []
        semantic_lines = self._build_semantic_reasoning_lines(semantic_graph)
        semantic_basis_lines = self._build_semantic_anchor_lines(semantic_graph)

        for result in top_results:
            document = evidence_documents.get(result.document_id)
            validity = evaluate_document_validity(document) if document is not None else None
            status_note = ""
            if validity and not validity.is_authoritative:
                status_note = f" [{'; '.join(validity.reasons)}]"
            basis_lines.append(
                f"- {result.citation_label or 'Đoạn liên quan'} - {result.document_title}{status_note}"
            )
            analysis_lines.append(
                f"- Độ khớp {result.score}/100, trích yếu: {result.excerpt}"
            )

        recommendation = "Tiếp tục tra cứu nội bộ." if complexity_level == "low" else "Nên đối chiếu thêm hồ sơ, tình tiết và tài liệu liên quan."
        if related_articles:
            recommendation += f" Đã tìm thấy {len(related_articles)} điều khoản hoặc ngữ cảnh liên quan để đối chiếu thêm."
        if semantic_lines:
            recommendation += f" Đã dựng được {len(semantic_lines)} bước suy luận ngữ nghĩa để nối chủ thể, thủ tục và quyền pháp lý liên quan."
        if conflict_result and conflict_result.winner_document_id is not None:
            recommendation += f" Quy tắc xung đột hiện nghiêng về văn bản ID {conflict_result.winner_document_id} theo {conflict_result.resolution_basis}."
        elif conflict_result and conflict_result.winner_document_id is None:
            recommendation += " Có dấu hiệu xung đột căn cứ, cần người xử lý pháp lý kiểm tra thêm."

        if validation_warning:
            recommendation += f" {validation_warning}"

        return (
            f"Kết luận: Yêu cầu hiện được phân tích theo nhóm {domain_name} với intent {intent}.\n\n"
            "Phân tích:\n"
            + "\n".join(analysis_lines)
            + (
                "\n\nĐường suy luận ngữ nghĩa:\n" + "\n".join(semantic_lines)
                if semantic_lines
                else ""
            )
            + "\n\nCăn cứ:\n"
            + "\n".join(basis_lines)
            + (
                "\n\nCăn cứ cho đường suy luận:\n" + "\n".join(semantic_basis_lines)
                if semantic_basis_lines
                else ""
            )
            + f"\n\nKhuyến nghị: {recommendation}"
        )

    def _build_practical_checklist_answer(
        self,
        content: str,
        domain_slug: str,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        validation_warning: str | None,
    ) -> str | None:
        normalized = self._normalize_text(content)
        asks_for_documents = any(term in normalized for term in {"ho so", "giay to", "can chuan bi", "chuan bi gi", "thu tuc"})
        asks_resignation = any(term in normalized for term in {"nghi viec", "thoi viec", "don phuong cham dut", "bao truoc"})
        asks_divorce = any(term in normalized for term in {"ly hon", "khong thuan", "vo chong"})

        if domain_slug == "lao-dong" and (asks_resignation or asks_for_documents):
            answer = (
                "Kết luận sơ bộ: Với hồ sơ xin nghỉ việc, bạn nên chuẩn bị theo 2 nhóm: giấy tờ để nộp cho công ty và giấy tờ để tự bảo vệ quyền lợi.\n\n"
                "Hồ sơ nộp cho công ty:\n"
                "- Đơn xin nghỉ việc hoặc thông báo chấm dứt hợp đồng lao động, ghi rõ ngày dự kiến nghỉ.\n"
                "- Biên bản bàn giao công việc, tài sản, tài khoản, thiết bị và tài liệu nội bộ.\n"
                "- Đề nghị xác nhận ngày làm việc cuối cùng và các khoản công ty còn phải thanh toán.\n\n"
                "Giấy tờ nên giữ lại:\n"
                "- Hợp đồng lao động, phụ lục hợp đồng, quyết định bổ nhiệm hoặc phân công công việc.\n"
                "- Bảng lương, sao kê nhận lương, thông tin phép năm chưa nghỉ, bảo hiểm xã hội.\n"
                "- Email, tin nhắn, thông báo liên quan đến việc nghỉ, bàn giao, lương, kỷ luật hoặc tranh chấp nếu có.\n\n"
                "Lưu ý: Trước khi nộp đơn, cần kiểm tra loại hợp đồng và thời hạn báo trước trong hợp đồng/Bộ luật Lao động. "
                "Nếu công ty còn nợ lương, bảo hiểm hoặc đang có tranh chấp, nên lưu chứng cứ trước khi bàn giao toàn bộ."
            )
            return self._append_retrieval_context(answer, search_results, evidence_documents, validation_warning)

        if domain_slug == "hon-nhan-va-gia-dinh" and asks_divorce and asks_for_documents:
            answer = (
                "Kết luận sơ bộ: Nếu muốn ly hôn, hồ sơ thường gồm giấy tờ nhân thân, giấy tờ hôn nhân, giấy tờ về con và tài sản nếu có tranh chấp.\n\n"
                "Hồ sơ cơ bản:\n"
                "- Đơn yêu cầu ly hôn thuận tình hoặc đơn khởi kiện ly hôn đơn phương.\n"
                "- Bản chính giấy chứng nhận kết hôn. Nếu mất bản chính, cần xin trích lục tại cơ quan hộ tịch.\n"
                "- Căn cước công dân/hộ chiếu và giấy tờ cư trú của vợ chồng.\n"
                "- Giấy khai sinh của con chung nếu có con.\n"
                "- Tài liệu về tài sản chung, nợ chung, thu nhập, chỗ ở, điều kiện nuôi con nếu có yêu cầu phân chia hoặc tranh chấp quyền nuôi con.\n\n"
                "Lưu ý: Nếu hai bên thống nhất ly hôn, tài sản và con chung thì đi theo hướng thuận tình. "
                "Nếu một bên không đồng ý hoặc có tranh chấp, hồ sơ thường nộp theo thủ tục ly hôn đơn phương tại tòa án có thẩm quyền."
            )
            return self._append_retrieval_context(answer, search_results, evidence_documents, validation_warning)

        return None

    def _append_retrieval_context(
        self,
        answer: str,
        search_results: list[SearchLawResult],
        evidence_documents: dict[int, Document],
        validation_warning: str | None,
    ) -> str:
        if not search_results:
            return (
                answer
                + "\n\nCăn cứ trong kho tri thức: Chưa tìm được điều khoản đủ gần cho câu hỏi này, nên phần trên là checklist định hướng để demo. Cần tư vấn viên đối chiếu hồ sơ thực tế."
            )

        basis_lines: list[str] = []
        for result in search_results[:3]:
            document = evidence_documents.get(result.document_id)
            validity = evaluate_document_validity(document) if document is not None else None
            status_note = ""
            if validity and not validity.is_authoritative:
                status_note = f" [{'; '.join(validity.reasons)}]"
            basis_lines.append(f"- {result.citation_label or 'Đoạn liên quan'} - {result.document_title}{status_note}")

        warning = f"\n\nCảnh báo: {validation_warning}" if validation_warning else ""
        return answer + "\n\nCăn cứ tìm thấy để đối chiếu thêm:\n" + "\n".join(basis_lines) + warning

    def _build_demo_answer(self, content: str, domain_slug: str) -> str:
        domain_name = CATEGORY_DISPLAY_NAMES.get(domain_slug, "pháp lý")
        normalized = self._normalize_text(content)

        if any(term in normalized for term in {"nghi viec", "thoi viec", "don phuong cham dut", "bao truoc"}):
            return (
                "Kết luận sơ bộ: Nếu bạn muốn nghỉ việc, cần chuẩn bị hồ sơ và kiểm tra thời hạn báo trước theo loại hợp đồng lao động.\n\n"
                "Hồ sơ nên chuẩn bị:\n"
                "- Đơn xin nghỉ việc hoặc thông báo chấm dứt hợp đồng lao động.\n"
                "- Bản sao hợp đồng lao động, phụ lục hợp đồng nếu có.\n"
                "- Bảng lương, quyết định bổ nhiệm, email hoặc tài liệu liên quan đến công việc.\n"
                "- Biên bản bàn giao công việc, tài sản, tài khoản, thiết bị.\n"
                "- Yêu cầu thanh toán lương, phép năm chưa nghỉ, bảo hiểm và các khoản còn lại.\n\n"
                "Lưu ý: Cần đối chiếu Bộ luật Lao động và hợp đồng thực tế để xác định số ngày báo trước. "
                "Nếu đang có tranh chấp lương, bảo hiểm hoặc kỷ luật lao động, nên lưu bằng chứng trước khi nộp đơn.\n\n"
                "Trạng thái demo: Câu trả lời này là fallback để phục vụ trình diễn khi kho tri thức hoặc AI pipeline chưa sẵn sàng."
            )

        return (
            f"Kết luận sơ bộ: Câu hỏi của bạn được nhận diện thuộc nhóm {domain_name}.\n\n"
            "Hướng xử lý đề xuất:\n"
            "- Tóm tắt sự việc theo mốc thời gian.\n"
            "- Chuẩn bị hợp đồng, giấy tờ, thông báo, email hoặc chứng cứ liên quan.\n"
            "- Xác định cơ quan hoặc bên liên quan cần làm việc.\n"
            "- Đối chiếu văn bản pháp luật trước khi ra quyết định.\n\n"
            "Trạng thái demo: Câu trả lời này là fallback để phục vụ trình diễn khi kho tri thức hoặc AI pipeline chưa sẵn sàng."
        )

    def _build_semantic_reasoning_lines(self, semantic_graph: dict[str, object] | None) -> list[str]:
        if not semantic_graph:
            return []

        nodes = semantic_graph.get("nodes", [])
        edges = semantic_graph.get("edges", [])
        if not isinstance(nodes, list) or not isinstance(edges, list):
            return []

        node_labels = {
            str(node.get("id")): str(node.get("label"))
            for node in nodes
            if isinstance(node, dict) and node.get("id") and node.get("label")
        }
        lines: list[str] = []
        for edge in edges[:4]:
            if not isinstance(edge, dict):
                continue
            source = node_labels.get(str(edge.get("source")))
            target = node_labels.get(str(edge.get("target")))
            edge_label = edge.get("label") or edge.get("edge_type")
            if not source or not target or not edge_label:
                continue
            lines.append(f"- {source} -> {edge_label} -> {target}")
        return lines

    def _build_semantic_anchor_lines(self, semantic_graph: dict[str, object] | None) -> list[str]:
        if not semantic_graph:
            return []

        anchors = semantic_graph.get("anchors", [])
        if not isinstance(anchors, list):
            return []

        lines: list[str] = []
        for anchor in anchors[:4]:
            if not isinstance(anchor, dict):
                continue
            document_title = anchor.get("document_title")
            relation_role = anchor.get("relation_role")
            citation_label = anchor.get("citation_label")
            source_excerpt = anchor.get("source_excerpt")
            if not document_title or not relation_role:
                continue
            citation_suffix = f" - {citation_label}" if citation_label else ""
            excerpt_suffix = f": {source_excerpt}" if source_excerpt else ""
            lines.append(f"- {relation_role}{citation_suffix} - {document_title}{excerpt_suffix}")
        return lines

    def _build_primary_citation_source(self, top_citation: SearchLawResult | None) -> str | None:
        if top_citation is None:
            return None
        parts = [top_citation.source_reference, top_citation.citation_label, top_citation.hierarchy_path]
        filtered = [part for part in parts if part]
        return " | ".join(filtered) if filtered else None

    def _build_plan_steps(self, intent: str, domain_slug: str, complexity_level: str, has_results: bool) -> list[dict]:
        steps = [
            {"step": "classify_intent", "intent": intent, "domain": domain_slug},
            {"step": "score_complexity", "complexity": complexity_level},
            {"step": "retrieve_legal_evidence", "status": "completed" if has_results else "empty"},
            {"step": "check_validity", "status": "completed"},
            {"step": "resolve_conflict", "status": "completed"},
            {"step": "validate_response", "status": "completed"},
        ]
        return steps

    def _normalize_text(self, text: str) -> str:
        return normalize_legal_text(text)


chat_service = ChatService()
