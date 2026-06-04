from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth_router import router as auth_router
from src.api.admin_annotation_router import router as admin_annotation_router
from src.api.admin_router import router as admin_router
from src.api.chat_router import router as chat_router
from src.api.content_router import router as content_router
from src.api.knowledge_router import router as knowledge_router
from src.api.ticket_router import router as ticket_router
from src.core.config import settings
from src.core.database import Base, SessionLocal, engine
from src.core.exceptions import AppException
from src.core.logging import logger, setup_logging
from src.core.schema_bootstrap import ensure_optional_schema_columns
from src.models import AIRequestUsage, AuthorityLevelDefinition, CaseFact, Category, ChatMessage, ChatSession, Citation, ContentArticle, Document, DocumentChunk, DocumentChunkVector, DocumentRelation, DocumentTypeDefinition, LawyerProfile, LegalCase, LegalProvision, PlannerRun, ProvisionRelation, ReasoningRun, Ticket, TicketMessage, User, ValidationRun
from src.services.bootstrap_service import ensure_seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        ensure_optional_schema_columns(engine)
        with SessionLocal() as db:
            ensure_seed_data(db)
        logger.info("Database tables ensured")
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "data": exc.data},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(admin_annotation_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(content_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(ticket_router, prefix=settings.api_prefix)
