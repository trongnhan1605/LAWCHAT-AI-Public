from sqlalchemy import Engine, inspect, text

from src.core.logging import logger


def ensure_optional_schema_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "documents" not in table_names:
        return

    text_type = "VARCHAR"
    text_long_type = "TEXT"
    datetime_type = "DATETIME"
    if engine.dialect.name == "mssql":
        text_type = "NVARCHAR"
        text_long_type = "NVARCHAR(MAX)"
    elif engine.dialect.name == "postgresql":
        datetime_type = "TIMESTAMP WITH TIME ZONE"

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    document_additions = {
        "document_code": f"{text_type}(128) NULL",
        "authority_level": f"{text_type}(64) NULL",
        "document_type": f"{text_type}(64) NULL",
        "normative_level": "INTEGER NULL",
        "signed_date": "DATE NULL",
        "expiry_date": "DATE NULL",
        "legal_status": f"{text_type}(32) NULL",
        "metadata_review_status": f"{text_type}(32) NULL",
        "metadata_review_notes": f"{text_long_type} NULL",
        "metadata_last_reviewed_at": f"{datetime_type} NULL",
        "content_sha256": f"{text_type}(64) NULL",
        "source_identity": f"{text_type}(512) NULL",
        "ingestion_quality_status": f"{text_type}(32) NULL",
        "ingestion_quality_notes": f"{text_long_type} NULL",
        "retrieval_visibility": f"{text_type}(32) NULL",
        "ocr_quality_score": "NUMERIC(5,2) NULL",
        "ocr_quality_label": f"{text_type}(32) NULL",
        "relation_sync_status": f"{text_type}(32) NULL",
        "relation_sync_details": f"{text_long_type} NULL",
    }

    chunk_additions: dict[str, str] = {}
    if "document_chunks" in table_names:
        chunk_columns = {column["name"] for column in inspector.get_columns("document_chunks")}
        chunk_additions = {
            name: ddl
            for name, ddl in {
                "chunk_type": f"{text_type}(32) NULL",
                "citation_label": f"{text_type}(255) NULL",
                "hierarchy_path": f"{text_type}(1000) NULL",
                "article_number": f"{text_type}(64) NULL",
                "clause_number": f"{text_type}(64) NULL",
                "point_number": f"{text_type}(64) NULL",
                "retrieval_text": f"{text_long_type} NULL",
                "metadata_json": f"{text_long_type} NULL",
            }.items()
            if name not in chunk_columns
        }

    chat_session_columns: set[str] = set()
    chat_session_additions: dict[str, str] = {}
    if "chat_sessions" in table_names:
        chat_session_columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
        chat_session_additions = {
            name: ddl
            for name, ddl in {
                "user_id": "INTEGER NULL",
                "session_type": f"{text_type}(32) NULL",
            }.items()
            if name not in chat_session_columns
        }

    planner_run_additions: dict[str, str] = {}
    if "planner_runs" in table_names:
        planner_run_columns = {column["name"] for column in inspector.get_columns("planner_runs")}
        planner_run_additions = {
            name: ddl
            for name, ddl in {
                "case_id": "INTEGER NULL",
            }.items()
            if name not in planner_run_columns
        }

    reasoning_run_additions: dict[str, str] = {}
    if "reasoning_runs" in table_names:
        reasoning_run_columns = {column["name"] for column in inspector.get_columns("reasoning_runs")}
        reasoning_run_additions = {
            name: ddl
            for name, ddl in {
                "case_id": "INTEGER NULL",
            }.items()
            if name not in reasoning_run_columns
        }

    validation_run_additions: dict[str, str] = {}
    if "validation_runs" in table_names:
        validation_run_columns = {column["name"] for column in inspector.get_columns("validation_runs")}
        validation_run_additions = {
            name: ddl
            for name, ddl in {
                "case_id": "INTEGER NULL",
            }.items()
            if name not in validation_run_columns
        }

    ticket_additions: dict[str, str] = {}
    if "tickets" in table_names:
        ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
        ticket_additions = {
            name: ddl
            for name, ddl in {
                "case_id": "INTEGER NULL",
            }.items()
            if name not in ticket_columns
        }

    with engine.begin() as connection:
        for column_name, ddl in document_additions.items():
            if column_name not in document_columns:
                connection.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {ddl}"))

        if "legal_status" in document_columns or "legal_status" in document_additions:
            connection.execute(text("UPDATE documents SET legal_status = 'active' WHERE legal_status IS NULL"))
        if "metadata_review_status" in document_columns or "metadata_review_status" in document_additions:
            connection.execute(text("UPDATE documents SET metadata_review_status = 'pending_review' WHERE metadata_review_status IS NULL"))
        if "relation_sync_status" in document_columns or "relation_sync_status" in document_additions:
            connection.execute(text("UPDATE documents SET relation_sync_status = 'pending' WHERE relation_sync_status IS NULL"))
        if "ingestion_quality_status" in document_columns or "ingestion_quality_status" in document_additions:
            connection.execute(text("UPDATE documents SET ingestion_quality_status = 'pending' WHERE ingestion_quality_status IS NULL"))
        if "retrieval_visibility" in document_columns or "retrieval_visibility" in document_additions:
            connection.execute(text("UPDATE documents SET retrieval_visibility = CASE WHEN metadata_review_status = 'reviewed' THEN 'indexed_verified' ELSE 'indexed_unreviewed' END WHERE retrieval_visibility IS NULL"))

        for column_name, ddl in chunk_additions.items():
            connection.execute(text(f"ALTER TABLE document_chunks ADD COLUMN {column_name} {ddl}"))

        for column_name, ddl in chat_session_additions.items():
            connection.execute(text(f"ALTER TABLE chat_sessions ADD COLUMN {column_name} {ddl}"))

        if "chat_sessions" in table_names and ("session_type" in chat_session_columns or "session_type" in chat_session_additions):
            connection.execute(text("UPDATE chat_sessions SET session_type = 'public' WHERE session_type IS NULL"))

        for column_name, ddl in planner_run_additions.items():
            connection.execute(text(f"ALTER TABLE planner_runs ADD COLUMN {column_name} {ddl}"))

        for column_name, ddl in reasoning_run_additions.items():
            connection.execute(text(f"ALTER TABLE reasoning_runs ADD COLUMN {column_name} {ddl}"))

        for column_name, ddl in validation_run_additions.items():
            connection.execute(text(f"ALTER TABLE validation_runs ADD COLUMN {column_name} {ddl}"))

        for column_name, ddl in ticket_additions.items():
            connection.execute(text(f"ALTER TABLE tickets ADD COLUMN {column_name} {ddl}"))

    logger.info("Optional schema columns for documents, document_chunks, chat_sessions, planner_runs, reasoning_runs, validation_runs, and tickets ensured")
