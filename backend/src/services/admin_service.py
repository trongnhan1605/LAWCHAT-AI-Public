from datetime import datetime, timezone

from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.core.security import hash_password
from src.models.authority_level_definition import AuthorityLevelDefinition
from src.models.article_concept_link import ArticleConceptLink
from src.models.category import Category
from src.models.chat import ChatMessage, ChatSession
from src.models.citation import Citation
from src.models.content_article import ContentArticle
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_vector import DocumentChunkVector
from src.models.document_relation import DocumentRelation
from src.models.document_type_definition import DocumentTypeDefinition
from src.models.case_fact import CaseFact
from src.models.lawyer_profile import LawyerProfile
from src.models.legal_case import LegalCase
from src.models.legal_provision import LegalProvision
from src.models.planner_run import PlannerRun
from src.models.provision_relation import ProvisionRelation
from src.models.reasoning_run import ReasoningRun
from src.models.ticket import Ticket
from src.models.ticket_message import TicketMessage
from src.models.user import User
from src.models.validation_run import ValidationRun
from src.repositories.user_repository import UserRepository
from src.ingestion.document_identity import document_identity_service
from src.services.ai_usage_service import ai_usage_service
from src.services.metadata_normalization_service import metadata_normalization_service


class AdminService:
    SUPPORTED_SOURCE_TYPES = {"pdf", "txt", "docx"}
    DUPLICATE_ACTIONS = {"overwrite", "create_new"}
    ALLOWED_USER_ROLES = {"user", "customer", "consultant", "admin"}

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def _normalize_slug(self, slug: str) -> str:
        return slug.strip().lower().replace(" ", "-")

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _normalize_user_role(self, role: str) -> str:
        normalized = role.strip().lower()
        if normalized not in self.ALLOWED_USER_ROLES:
            raise ValidationException("Unsupported user role")
        return normalized

    def _normalize_definition_priority(self, value: int | None, *, fallback: int) -> int:
        return int(value) if value is not None else fallback

    def _get_definition_or_raise(self, db: Session, model, item_id: int, not_found_message: str):
        item = db.query(model).filter(model.id == item_id).first()
        if item is None:
            raise NotFoundException(not_found_message)
        return item

    def _create_definition(self, db: Session, model, *, name: str, slug: str, description: str | None, priority_field: str, priority: int, conflict_message: str):
        normalized_name = name.strip()
        normalized_slug = self._normalize_slug(slug)
        existing = db.query(model).filter((model.slug == normalized_slug) | (model.name == normalized_name)).first()
        if existing is not None:
            raise ConflictException(conflict_message)

        item = model(
            name=normalized_name,
            slug=normalized_slug,
            description=self._normalize_optional_text(description),
            is_active=True,
        )
        setattr(item, priority_field, priority)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def _update_definition(self, db: Session, model, *, item_id: int, name: str, slug: str, description: str | None, is_active: bool, priority_field: str, priority: int, not_found_message: str, conflict_message: str):
        item = self._get_definition_or_raise(db, model, item_id, not_found_message)
        normalized_name = name.strip()
        normalized_slug = self._normalize_slug(slug)
        existing = (
            db.query(model)
            .filter(model.id != item_id)
            .filter((model.slug == normalized_slug) | (model.name == normalized_name))
            .first()
        )
        if existing is not None:
            raise ConflictException(conflict_message)

        item.name = normalized_name
        item.slug = normalized_slug
        item.description = self._normalize_optional_text(description)
        item.is_active = is_active
        setattr(item, priority_field, priority)
        db.commit()
        db.refresh(item)
        return item

    def _delete_definition(self, db: Session, model, *, item_id: int, not_found_message: str) -> None:
        item = self._get_definition_or_raise(db, model, item_id, not_found_message)
        db.delete(item)
        db.commit()

    def _validate_source_type(self, source_type: str) -> str:
        normalized = source_type.strip().lower()
        if normalized not in self.SUPPORTED_SOURCE_TYPES:
            raise ValidationException("Unsupported document source type")
        return normalized

    def _normalize_duplicate_action(self, duplicate_action: str | None) -> str | None:
        if duplicate_action is None:
            return None

        normalized = duplicate_action.strip().lower()
        if normalized not in self.DUPLICATE_ACTIONS:
            raise ValidationException("Unsupported duplicate action")
        return normalized

    def _find_duplicate_document(
        self,
        db: Session,
        title: str,
        file_name: str,
        content_sha256: str | None = None,
        source_identity: str | None = None,
        exclude_document_id: int | None = None,
    ) -> Document | None:
        query = db.query(Document)
        if exclude_document_id is not None:
            query = query.filter(Document.id != exclude_document_id)
        filters = [Document.file_name == file_name]
        if content_sha256:
            filters.append(Document.content_sha256 == content_sha256)
        if source_identity:
            filters.append(Document.source_identity == source_identity)
        return query.filter(or_(*filters)).first()

    def _build_unique_title(self, db: Session, title: str) -> str:
        candidate = title
        suffix = 2
        while db.query(Document.id).filter(Document.title == candidate).first() is not None:
            candidate = f"{title} ({suffix})"
            suffix += 1
        return candidate

    def _build_unique_file_name(self, db: Session, file_name: str) -> str:
        if "." in file_name:
            stem, suffix = file_name.rsplit(".", 1)
            extension = f".{suffix}"
        else:
            stem = file_name
            extension = ""

        candidate = file_name
        suffix_index = 2
        while db.query(Document.id).filter(Document.file_name == candidate).first() is not None:
            candidate = f"{stem}-{suffix_index}{extension}"
            suffix_index += 1
        return candidate

    def _build_document_duplicate_data(self, db: Session, document: Document, title: str, file_name: str, content_sha256: str | None = None, source_identity: str | None = None) -> dict:
        matching_fields: list[str] = []
        if document.title == title:
            matching_fields.append("title")
        if document.file_name == file_name:
            matching_fields.append("file_name")
        if content_sha256 and document.content_sha256 == content_sha256:
            matching_fields.append("content_sha256")
        if source_identity and document.source_identity == source_identity:
            matching_fields.append("source_identity")

        return {
            "conflict_type": "document_duplicate",
            "allowed_actions": ["overwrite", "create_new", "skip"],
            "matching_fields": matching_fields,
            "existing_document": {
                "id": document.id,
                "title": document.title,
                "file_name": document.file_name,
                "source_type": document.source_type,
                "legal_domain": document.legal_domain,
                "source_reference": document.source_reference,
                "storage_path": document.storage_path,
                "content_sha256": document.content_sha256,
                "source_identity": document.source_identity,
            },
            "suggested_title": self._build_unique_title(db, title),
            "suggested_file_name": self._build_unique_file_name(db, file_name),
        }

    def build_overview(self, db: Session) -> dict:
        total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
        total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0
        total_legal_cases = db.query(func.count(LegalCase.id)).scalar() or 0
        active_legal_cases = (
            db.query(func.count(LegalCase.id))
            .filter(LegalCase.status.not_in(["closed", "archived"]))
            .scalar()
            or 0
        )
        high_risk_legal_cases = (
            db.query(func.count(LegalCase.id))
            .filter(LegalCase.risk_level == "high")
            .scalar()
            or 0
        )
        total_case_facts = db.query(func.count(CaseFact.id)).scalar() or 0
        total_documents = db.query(func.count(Document.id)).scalar() or 0
        ingested_documents = db.query(func.count(func.distinct(DocumentChunk.document_id))).scalar() or 0
        total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0
        total_document_relations = db.query(func.count(DocumentRelation.id)).scalar() or 0
        total_citations = db.query(func.count(Citation.id)).scalar() or 0
        total_categories = db.query(func.count(Category.id)).scalar() or 0
        active_categories = db.query(func.count(Category.id)).filter(Category.is_active == True).scalar() or 0
        total_tickets = db.query(func.count(Ticket.id)).scalar() or 0
        open_tickets = (
            db.query(func.count(Ticket.id))
            .filter(Ticket.status.not_in(["closed", "cancelled"]))
            .scalar()
            or 0
        )
        answered_tickets = db.query(func.count(Ticket.id)).filter(Ticket.status.in_(["answered", "closed"])) .scalar() or 0
        total_planner_runs = db.query(func.count(PlannerRun.id)).scalar() or 0
        total_reasoning_runs = db.query(func.count(ReasoningRun.id)).scalar() or 0
        total_validation_runs = db.query(func.count(ValidationRun.id)).scalar() or 0
        validation_runs_needing_review = (
            db.query(func.count(ValidationRun.id))
            .filter(ValidationRun.validation_status.in_(["needs_review", "pass_with_warnings"]))
            .scalar()
            or 0
        )
        escalations_recommended = (
            db.query(func.count(ValidationRun.id))
            .filter(ValidationRun.escalation_recommended == True)
            .scalar()
            or 0
        )
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_legal_cases": total_legal_cases,
            "active_legal_cases": active_legal_cases,
            "high_risk_legal_cases": high_risk_legal_cases,
            "total_case_facts": total_case_facts,
            "total_documents": total_documents,
            "ingested_documents": ingested_documents,
            "total_chunks": total_chunks,
            "total_document_relations": total_document_relations,
            "total_citations": total_citations,
            "total_categories": total_categories,
            "active_categories": active_categories,
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "answered_tickets": answered_tickets,
            "total_planner_runs": total_planner_runs,
            "total_reasoning_runs": total_reasoning_runs,
            "total_validation_runs": total_validation_runs,
            "validation_runs_needing_review": validation_runs_needing_review,
            "escalations_recommended": escalations_recommended,
        }

    def list_users(self, db: Session) -> list[User]:
        return self.user_repository.list_all(db)

    def create_user(self, db: Session, full_name: str, email: str, password: str, role: str, is_active: bool) -> User:
        normalized_email = self._normalize_email(email)
        if self.user_repository.get_by_email(db, normalized_email) is not None:
            raise ConflictException("Email already exists")

        user = self.user_repository.create(
            db=db,
            full_name=full_name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
            role=self._normalize_user_role(role),
        )
        user.is_active = is_active

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictException("Email already exists") from exc

        db.refresh(user)
        return user

    def update_user(
        self,
        db: Session,
        user_id: int,
        *,
        full_name: str,
        email: str,
        role: str,
        is_active: bool,
        password: str | None,
        actor_user_id: int | None = None,
    ) -> User:
        user = self.user_repository.get_by_id(db, user_id)
        if user is None:
            raise NotFoundException("User not found")

        normalized_email = self._normalize_email(email)
        existing_user = self.user_repository.get_by_email(db, normalized_email)
        if existing_user is not None and existing_user.id != user_id:
            raise ConflictException("Email already exists")

        normalized_role = self._normalize_user_role(role)
        if actor_user_id == user_id and (normalized_role != "admin" or not is_active):
            raise ValidationException("You cannot remove your own admin access or deactivate your current account")

        user.full_name = full_name.strip()
        user.email = normalized_email
        user.role = normalized_role
        user.is_active = is_active
        if password is not None and password.strip():
            user.password_hash = hash_password(password)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictException("Email already exists") from exc

        db.refresh(user)
        return user

    def delete_user(self, db: Session, user_id: int, *, actor_user_id: int | None = None) -> None:
        user = self.user_repository.get_by_id(db, user_id)
        if user is None:
            raise NotFoundException("User not found")
        if actor_user_id == user_id:
            raise ValidationException("You cannot delete your current account")

        self.user_repository.delete(db, user)
        db.commit()

    def list_categories(self, db: Session) -> list[Category]:
        items = db.query(Category).all()
        preferred_order = {
            "lao-dong": 0,
            "hon-nhan-va-gia-dinh": 1,
            "dat-dai": 2,
        }
        return sorted(items, key=lambda item: (preferred_order.get(item.slug, 1000), item.name.lower()))

    def list_content_articles(self, db: Session) -> list[ContentArticle]:
        return db.query(ContentArticle).order_by(ContentArticle.is_featured.desc(), ContentArticle.updated_at.desc(), ContentArticle.id.desc()).all()

    def create_content_article(self, db: Session, title: str, slug: str, category: str, excerpt: str, source_url: str | None, is_featured: bool, is_active: bool) -> ContentArticle:
        normalized_slug = self._normalize_slug(slug)
        if db.query(ContentArticle).filter(ContentArticle.slug == normalized_slug).first() is not None:
            raise ConflictException("Article already exists")
        item = ContentArticle(
            title=title.strip(),
            slug=normalized_slug,
            category=category.strip(),
            excerpt=excerpt.strip(),
            source_url=self._normalize_optional_text(source_url),
            is_featured=is_featured,
            is_active=is_active,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update_content_article(self, db: Session, article_id: int, title: str, slug: str, category: str, excerpt: str, source_url: str | None, is_featured: bool, is_active: bool) -> ContentArticle:
        item = db.query(ContentArticle).filter(ContentArticle.id == article_id).first()
        if item is None:
            raise NotFoundException("Article not found")
        normalized_slug = self._normalize_slug(slug)
        existing = db.query(ContentArticle).filter(ContentArticle.id != article_id, ContentArticle.slug == normalized_slug).first()
        if existing is not None:
            raise ConflictException("Article already exists")
        item.title = title.strip()
        item.slug = normalized_slug
        item.category = category.strip()
        item.excerpt = excerpt.strip()
        item.source_url = self._normalize_optional_text(source_url)
        item.is_featured = is_featured
        item.is_active = is_active
        db.commit()
        db.refresh(item)
        return item

    def delete_content_article(self, db: Session, article_id: int) -> None:
        item = db.query(ContentArticle).filter(ContentArticle.id == article_id).first()
        if item is None:
            raise NotFoundException("Article not found")
        db.delete(item)
        db.commit()

    def list_lawyer_profiles(self, db: Session) -> list[LawyerProfile]:
        return db.query(LawyerProfile).order_by(LawyerProfile.is_featured.desc(), LawyerProfile.updated_at.desc(), LawyerProfile.id.desc()).all()

    def create_lawyer_profile(self, db: Session, full_name: str, slug: str, title: str, location: str, specialties: str, experience_years: int, rating: str | None, bio: str | None, avatar_url: str | None, is_featured: bool, is_active: bool) -> LawyerProfile:
        normalized_slug = self._normalize_slug(slug)
        if db.query(LawyerProfile).filter(LawyerProfile.slug == normalized_slug).first() is not None:
            raise ConflictException("Lawyer profile already exists")
        item = LawyerProfile(
            full_name=full_name.strip(),
            slug=normalized_slug,
            title=title.strip(),
            location=location.strip(),
            specialties=specialties.strip(),
            experience_years=max(0, int(experience_years)),
            rating=self._normalize_optional_text(rating),
            bio=self._normalize_optional_text(bio),
            avatar_url=self._normalize_optional_text(avatar_url),
            is_featured=is_featured,
            is_active=is_active,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update_lawyer_profile(self, db: Session, lawyer_id: int, full_name: str, slug: str, title: str, location: str, specialties: str, experience_years: int, rating: str | None, bio: str | None, avatar_url: str | None, is_featured: bool, is_active: bool) -> LawyerProfile:
        item = db.query(LawyerProfile).filter(LawyerProfile.id == lawyer_id).first()
        if item is None:
            raise NotFoundException("Lawyer profile not found")
        normalized_slug = self._normalize_slug(slug)
        existing = db.query(LawyerProfile).filter(LawyerProfile.id != lawyer_id, LawyerProfile.slug == normalized_slug).first()
        if existing is not None:
            raise ConflictException("Lawyer profile already exists")
        item.full_name = full_name.strip()
        item.slug = normalized_slug
        item.title = title.strip()
        item.location = location.strip()
        item.specialties = specialties.strip()
        item.experience_years = max(0, int(experience_years))
        item.rating = self._normalize_optional_text(rating)
        item.bio = self._normalize_optional_text(bio)
        item.avatar_url = self._normalize_optional_text(avatar_url)
        item.is_featured = is_featured
        item.is_active = is_active
        db.commit()
        db.refresh(item)
        return item

    def delete_lawyer_profile(self, db: Session, lawyer_id: int) -> None:
        item = db.query(LawyerProfile).filter(LawyerProfile.id == lawyer_id).first()
        if item is None:
            raise NotFoundException("Lawyer profile not found")
        db.delete(item)
        db.commit()

    def list_documents(self, db: Session) -> list[Document]:
        return db.query(Document).order_by(Document.created_at.desc()).all()

    def list_legal_cases(self, db: Session) -> list[LegalCase]:
        return db.query(LegalCase).order_by(LegalCase.updated_at.desc(), LegalCase.id.desc()).all()

    def get_legal_case(self, db: Session, case_id: int) -> LegalCase:
        legal_case = db.query(LegalCase).filter(LegalCase.id == case_id).first()
        if legal_case is None:
            raise NotFoundException("Legal case not found")
        return legal_case

    def get_legal_case_detail(self, db: Session, case_id: int) -> tuple[LegalCase, list[CaseFact], list[PlannerRun], list[ValidationRun], list[Ticket]]:
        legal_case = self.get_legal_case(db, case_id)
        case_facts = (
            db.query(CaseFact)
            .filter(CaseFact.case_id == case_id)
            .order_by(CaseFact.created_at.asc(), CaseFact.id.asc())
            .all()
        )
        planner_runs = (
            db.query(PlannerRun)
            .filter(PlannerRun.case_id == case_id)
            .order_by(PlannerRun.updated_at.desc(), PlannerRun.id.desc())
            .all()
        )
        validation_runs = (
            db.query(ValidationRun)
            .filter(ValidationRun.case_id == case_id)
            .order_by(ValidationRun.updated_at.desc(), ValidationRun.id.desc())
            .all()
        )
        tickets = (
            db.query(Ticket)
            .filter(Ticket.case_id == case_id)
            .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
            .all()
        )
        return legal_case, case_facts, planner_runs, validation_runs, tickets

    def get_document(self, db: Session, document_id: int) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise NotFoundException("Document not found")
        return document

    def list_document_types(self, db: Session) -> list[DocumentTypeDefinition]:
        return db.query(DocumentTypeDefinition).order_by(DocumentTypeDefinition.normative_level.desc(), DocumentTypeDefinition.name.asc()).all()

    def list_authority_levels(self, db: Session) -> list[AuthorityLevelDefinition]:
        return db.query(AuthorityLevelDefinition).order_by(AuthorityLevelDefinition.hierarchy_rank.asc(), AuthorityLevelDefinition.name.asc()).all()

    def get_active_document_type_slugs(self, db: Session) -> set[str]:
        return {item.slug for item in self.list_document_types(db) if item.is_active}

    def get_active_authority_level_slugs(self, db: Session) -> set[str]:
        return {item.slug for item in self.list_authority_levels(db) if item.is_active}

    def get_document_type_priority(self, db: Session, slug: str | None) -> int | None:
        if not slug:
            return None
        item = db.query(DocumentTypeDefinition).filter(DocumentTypeDefinition.slug == slug).first()
        return item.normative_level if item else None

    def create_category(self, db: Session, name: str, slug: str, description: str | None) -> Category:
        normalized_slug = self._normalize_slug(slug)
        existing = db.query(Category).filter((Category.slug == normalized_slug) | (Category.name == name.strip())).first()
        if existing is not None:
            raise ConflictException("Category already exists")

        category = Category(name=name.strip(), slug=normalized_slug, description=description, is_active=True)
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    def create_document_type(self, db: Session, name: str, slug: str, description: str | None, priority: int) -> DocumentTypeDefinition:
        return self._create_definition(
            db,
            DocumentTypeDefinition,
            name=name,
            slug=slug,
            description=description,
            priority_field="normative_level",
            priority=priority,
            conflict_message="Document type already exists",
        )

    def update_document_type(self, db: Session, item_id: int, name: str, slug: str, description: str | None, priority: int, is_active: bool) -> DocumentTypeDefinition:
        return self._update_definition(
            db,
            DocumentTypeDefinition,
            item_id=item_id,
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
            priority_field="normative_level",
            priority=priority,
            not_found_message="Document type not found",
            conflict_message="Document type already exists",
        )

    def delete_document_type(self, db: Session, item_id: int) -> None:
        item = self._get_definition_or_raise(db, DocumentTypeDefinition, item_id, "Document type not found")
        usage_count = db.query(func.count(Document.id)).filter(Document.document_type == item.slug).scalar() or 0
        if usage_count > 0:
            raise ConflictException(
                f"Cannot delete document type '{item.name}' because it is used by {usage_count} document(s)",
                data={"usage_count": usage_count, "usage_field": "document_type", "usage_slug": item.slug},
            )
        db.delete(item)
        db.commit()

    def create_authority_level(self, db: Session, name: str, slug: str, description: str | None, priority: int) -> AuthorityLevelDefinition:
        return self._create_definition(
            db,
            AuthorityLevelDefinition,
            name=name,
            slug=slug,
            description=description,
            priority_field="hierarchy_rank",
            priority=priority,
            conflict_message="Authority level already exists",
        )

    def update_authority_level(self, db: Session, item_id: int, name: str, slug: str, description: str | None, priority: int, is_active: bool) -> AuthorityLevelDefinition:
        return self._update_definition(
            db,
            AuthorityLevelDefinition,
            item_id=item_id,
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
            priority_field="hierarchy_rank",
            priority=priority,
            not_found_message="Authority level not found",
            conflict_message="Authority level already exists",
        )

    def delete_authority_level(self, db: Session, item_id: int) -> None:
        item = self._get_definition_or_raise(db, AuthorityLevelDefinition, item_id, "Authority level not found")
        usage_count = db.query(func.count(Document.id)).filter(Document.authority_level == item.slug).scalar() or 0
        if usage_count > 0:
            raise ConflictException(
                f"Cannot delete authority level '{item.name}' because it is used by {usage_count} document(s)",
                data={"usage_count": usage_count, "usage_field": "authority_level", "usage_slug": item.slug},
            )
        db.delete(item)
        db.commit()

    def create_document(
        self,
        db: Session,
        title: str,
        file_name: str,
        source_type: str,
        legal_domain: str,
        authority_level: str | None,
        issuing_authority: str | None,
        document_code: str | None,
        document_type: str | None,
        normative_level: int | None,
        signed_date,
        source_reference: str | None,
        storage_path: str,
        summary: str | None,
        effective_date,
        expiry_date,
        legal_status: str | None,
        is_active: bool,
        duplicate_action: str | None = None,
        metadata_review_status: str = "reviewed",
        metadata_review_notes: str | None = None,
    ) -> Document:
        normalized_payload = metadata_normalization_service.normalize_document_payload({
            "title": title,
            "file_name": file_name,
            "source_type": source_type,
            "legal_domain": legal_domain,
            "authority_level": authority_level,
            "issuing_authority": issuing_authority,
            "document_code": document_code,
            "document_type": document_type,
            "source_reference": source_reference,
            "storage_path": storage_path,
            "summary": summary,
            "legal_status": legal_status,
            "metadata_review_notes": metadata_review_notes,
        })
        normalized_title = str(normalized_payload["title"] or "").strip()
        normalized_file_name = str(normalized_payload["file_name"] or "").strip()
        normalized_storage_path = str(normalized_payload["storage_path"] or storage_path).strip()
        normalized_source_reference = self._normalize_optional_text(normalized_payload["source_reference"])
        content_sha256 = document_identity_service.compute_content_sha256(normalized_storage_path)
        source_identity = document_identity_service.build_source_identity(
            source_reference=normalized_source_reference,
            storage_path=normalized_storage_path,
            content_sha256=content_sha256,
        )
        resolved_duplicate_action = self._normalize_duplicate_action(duplicate_action)
        existing = self._find_duplicate_document(db, normalized_title, normalized_file_name, content_sha256, source_identity)
        if existing is not None:
            if resolved_duplicate_action is None:
                raise ConflictException("Document already exists", self._build_document_duplicate_data(db, existing, normalized_title, normalized_file_name, content_sha256, source_identity))

            if resolved_duplicate_action == "overwrite":
                existing.title = normalized_title
                existing.file_name = normalized_file_name
                existing.source_type = self._validate_source_type(str(normalized_payload["source_type"] or source_type))
                existing.legal_domain = str(normalized_payload["legal_domain"] or legal_domain).strip()
                existing.authority_level = self._normalize_optional_text(normalized_payload["authority_level"])
                existing.issuing_authority = self._normalize_optional_text(normalized_payload["issuing_authority"])
                existing.document_code = self._normalize_optional_text(normalized_payload["document_code"])
                existing.document_type = self._normalize_optional_text(normalized_payload["document_type"])
                existing.normative_level = normative_level
                existing.signed_date = signed_date
                existing.source_reference = normalized_source_reference
                existing.storage_path = normalized_storage_path
                existing.content_sha256 = content_sha256
                existing.source_identity = source_identity
                existing.summary = self._normalize_optional_text(normalized_payload["summary"])
                existing.effective_date = effective_date
                existing.expiry_date = expiry_date
                existing.legal_status = self._normalize_optional_text(normalized_payload["legal_status"]) or "unknown"
                existing.metadata_review_status = metadata_review_status
                existing.metadata_review_notes = self._normalize_optional_text(normalized_payload["metadata_review_notes"])
                existing.metadata_last_reviewed_at = datetime.now(timezone.utc) if metadata_review_status == "reviewed" else None
                existing.retrieval_visibility = "indexed_verified" if metadata_review_status == "reviewed" else "indexed_unreviewed"
                existing.is_active = is_active
                db.commit()
                db.refresh(existing)
                ai_usage_service.attach_document_usage(
                    storage_path=existing.storage_path,
                    document_id=existing.id,
                    document_title=existing.title,
                    file_name=existing.file_name,
                )
                return existing

            normalized_title = self._build_unique_title(db, normalized_title)
            normalized_file_name = self._build_unique_file_name(db, normalized_file_name)

        document = Document(
            title=normalized_title,
            file_name=normalized_file_name,
            source_type=self._validate_source_type(str(normalized_payload["source_type"] or source_type)),
            legal_domain=str(normalized_payload["legal_domain"] or legal_domain).strip(),
            authority_level=self._normalize_optional_text(normalized_payload["authority_level"]),
            issuing_authority=self._normalize_optional_text(normalized_payload["issuing_authority"]),
            document_code=self._normalize_optional_text(normalized_payload["document_code"]),
            document_type=self._normalize_optional_text(normalized_payload["document_type"]),
            normative_level=normative_level,
            signed_date=signed_date,
            source_reference=normalized_source_reference,
            storage_path=normalized_storage_path,
            content_sha256=content_sha256,
            source_identity=source_identity,
            summary=self._normalize_optional_text(normalized_payload["summary"]),
            effective_date=effective_date,
            expiry_date=expiry_date,
            legal_status=self._normalize_optional_text(normalized_payload["legal_status"]) or "unknown",
            metadata_review_status=metadata_review_status,
            metadata_review_notes=self._normalize_optional_text(normalized_payload["metadata_review_notes"]),
            metadata_last_reviewed_at=datetime.now(timezone.utc) if metadata_review_status == "reviewed" else None,
            ingestion_quality_status="pending",
            retrieval_visibility="indexed_verified" if metadata_review_status == "reviewed" else "indexed_unreviewed",
            relation_sync_status="pending",
            is_seed=False,
            is_active=is_active,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        ai_usage_service.attach_document_usage(
            storage_path=document.storage_path,
            document_id=document.id,
            document_title=document.title,
            file_name=document.file_name,
        )
        return document

    def update_document(
        self,
        db: Session,
        document_id: int,
        title: str,
        file_name: str,
        source_type: str,
        legal_domain: str,
        authority_level: str | None,
        issuing_authority: str | None,
        document_code: str | None,
        document_type: str | None,
        normative_level: int | None,
        signed_date,
        source_reference: str | None,
        storage_path: str,
        summary: str | None,
        effective_date,
        expiry_date,
        legal_status: str | None,
        is_active: bool,
    ) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise NotFoundException("Document not found")

        normalized_payload = metadata_normalization_service.normalize_document_payload({
            "title": title,
            "file_name": file_name,
            "source_type": source_type,
            "legal_domain": legal_domain,
            "authority_level": authority_level,
            "issuing_authority": issuing_authority,
            "document_code": document_code,
            "document_type": document_type,
            "source_reference": source_reference,
            "storage_path": storage_path,
            "summary": summary,
            "legal_status": legal_status,
        })
        normalized_title = str(normalized_payload["title"] or "").strip()
        normalized_file_name = str(normalized_payload["file_name"] or "").strip()
        normalized_storage_path = str(normalized_payload["storage_path"] or storage_path).strip()
        normalized_source_reference = self._normalize_optional_text(normalized_payload["source_reference"])
        content_sha256 = document_identity_service.compute_content_sha256(normalized_storage_path)
        source_identity = document_identity_service.build_source_identity(
            source_reference=normalized_source_reference,
            storage_path=normalized_storage_path,
            content_sha256=content_sha256,
        )
        existing = self._find_duplicate_document(
            db,
            normalized_title,
            normalized_file_name,
            content_sha256,
            source_identity,
            exclude_document_id=document_id,
        )
        if existing is not None:
            raise ConflictException("Document already exists")

        document.title = normalized_title
        document.file_name = normalized_file_name
        document.source_type = self._validate_source_type(str(normalized_payload["source_type"] or source_type))
        document.legal_domain = str(normalized_payload["legal_domain"] or legal_domain).strip()
        document.authority_level = self._normalize_optional_text(normalized_payload["authority_level"])
        document.issuing_authority = self._normalize_optional_text(normalized_payload["issuing_authority"])
        document.document_code = self._normalize_optional_text(normalized_payload["document_code"])
        document.document_type = self._normalize_optional_text(normalized_payload["document_type"])
        document.normative_level = normative_level
        document.signed_date = signed_date
        document.source_reference = normalized_source_reference
        document.storage_path = normalized_storage_path
        document.content_sha256 = content_sha256
        document.source_identity = source_identity
        document.summary = self._normalize_optional_text(normalized_payload["summary"])
        document.effective_date = effective_date
        document.expiry_date = expiry_date
        document.legal_status = self._normalize_optional_text(normalized_payload["legal_status"]) or "unknown"
        document.metadata_review_status = "reviewed"
        document.metadata_last_reviewed_at = datetime.now(timezone.utc)
        document.retrieval_visibility = "indexed_verified"
        document.is_active = is_active
        db.commit()
        db.refresh(document)
        ai_usage_service.attach_document_usage(
            storage_path=document.storage_path,
            document_id=document.id,
            document_title=document.title,
            file_name=document.file_name,
        )
        return document

    def mark_document_metadata_reviewed(self, db: Session, document_id: int, notes: str | None = None) -> Document:
        document = self.get_document(db, document_id)
        document.metadata_review_status = "reviewed"
        document.metadata_review_notes = self._normalize_optional_text(notes)
        document.metadata_last_reviewed_at = datetime.now(timezone.utc)
        if document.retrieval_visibility != "blocked":
            document.retrieval_visibility = "indexed_verified"
        db.commit()
        db.refresh(document)
        return document

    def delete_document(self, db: Session, document_id: int) -> None:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise NotFoundException("Document not found")

        storage_path = document.storage_path
        chunk_ids = [chunk_id for (chunk_id,) in db.query(DocumentChunk.id).filter(DocumentChunk.document_id == document.id).all()]
        provision_ids = [
            provision_id
            for (provision_id,) in db.query(LegalProvision.id).filter(LegalProvision.document_id == document.id).all()
        ]

        if chunk_ids:
            db.query(ArticleConceptLink).filter(ArticleConceptLink.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
            db.query(DocumentChunkVector).filter(DocumentChunkVector.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
            db.query(Citation).filter(Citation.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)

        db.query(ArticleConceptLink).filter(ArticleConceptLink.document_id == document.id).delete(synchronize_session=False)
        db.query(Citation).filter(Citation.document_id == document.id).delete(synchronize_session=False)
        db.query(DocumentRelation).filter(
            (DocumentRelation.source_document_id == document.id) | (DocumentRelation.target_document_id == document.id)
        ).delete(synchronize_session=False)
        provision_relation_filter = (ProvisionRelation.source_document_id == document.id) | (ProvisionRelation.target_document_id == document.id)
        if provision_ids:
            provision_relation_filter = provision_relation_filter | (ProvisionRelation.source_provision_id.in_(provision_ids)) | (
                ProvisionRelation.target_provision_id.in_(provision_ids)
            )
        db.query(ProvisionRelation).filter(provision_relation_filter).delete(synchronize_session=False)
        db.query(LegalProvision).filter(LegalProvision.document_id == document.id).delete(synchronize_session=False)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)
        db.delete(document)
        db.commit()

        if storage_path:
            try:
                path = Path(storage_path)
                if path.exists() and path.is_file():
                    path.unlink()
            except OSError:
                pass

    def update_category(self, db: Session, category_id: int, name: str, slug: str, description: str | None, is_active: bool) -> Category:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category is None:
            raise NotFoundException("Category not found")

        normalized_name = name.strip()
        normalized_slug = self._normalize_slug(slug)
        existing = (
            db.query(Category)
            .filter(Category.id != category_id)
            .filter((Category.slug == normalized_slug) | (Category.name == normalized_name))
            .first()
        )
        if existing is not None:
            raise ConflictException("Category already exists")

        category.name = normalized_name
        category.slug = normalized_slug
        category.description = description.strip() if isinstance(description, str) and description.strip() else None
        category.is_active = is_active
        db.commit()
        db.refresh(category)
        return category

    def delete_category(self, db: Session, category_id: int) -> None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category is None:
            raise NotFoundException("Category not found")

        db.delete(category)
        db.commit()

    def toggle_category(self, db: Session, category_id: int, is_active: bool) -> Category:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category is None:
            raise NotFoundException("Category not found")
        category.is_active = is_active
        db.commit()
        db.refresh(category)
        return category

    def recent_activity(self, db: Session, limit: int = 12) -> list[dict]:
        activities: list[dict] = []

        for item in db.query(LegalCase).order_by(LegalCase.updated_at.desc()).limit(limit).all():
            activities.append(
                {
                    "event_type": "legal_case",
                    "title": f"Case #{item.id} {item.title}",
                    "description": item.summary or item.desired_outcome or item.status,
                    "occurred_at": item.updated_at,
                }
            )

        for item in db.query(Ticket).order_by(Ticket.created_at.desc()).limit(limit).all():
            activities.append(
                {
                    "event_type": "ticket",
                    "title": f"Ticket #{item.id} created",
                    "description": item.escalation_reason,
                    "occurred_at": item.created_at,
                }
            )

        for item in db.query(TicketMessage).order_by(TicketMessage.created_at.desc()).limit(limit).all():
            activities.append(
                {
                    "event_type": "consultant_reply",
                    "title": f"Reply on ticket #{item.ticket_id}",
                    "description": item.content,
                    "occurred_at": item.created_at,
                }
            )

        for item in db.query(Document).order_by(Document.updated_at.desc()).limit(limit).all():
            activities.append(
                {
                    "event_type": "document",
                    "title": f"Document {item.title}",
                    "description": item.summary or "Document metadata updated",
                    "occurred_at": item.updated_at,
                }
            )

        activities.sort(key=lambda activity: activity["occurred_at"], reverse=True)
        return activities[:limit]

    def list_recent_legal_cases(self, db: Session, limit: int = 20) -> list[LegalCase]:
        return (
            db.query(LegalCase)
            .order_by(LegalCase.updated_at.desc(), LegalCase.id.desc())
            .limit(limit)
            .all()
        )

    def list_recent_planner_runs(self, db: Session, limit: int = 20) -> list[PlannerRun]:
        return (
            db.query(PlannerRun)
            .order_by(PlannerRun.updated_at.desc(), PlannerRun.id.desc())
            .limit(limit)
            .all()
        )

    def list_recent_validation_runs(self, db: Session, limit: int = 20) -> list[ValidationRun]:
        return (
            db.query(ValidationRun)
            .order_by(ValidationRun.updated_at.desc(), ValidationRun.id.desc())
            .limit(limit)
            .all()
        )


admin_service = AdminService()
