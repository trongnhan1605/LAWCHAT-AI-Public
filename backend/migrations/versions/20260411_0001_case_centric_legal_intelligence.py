"""case-centric legal intelligence baseline

Revision ID: 20260411_0001
Revises:
Create Date: 2026-04-11 13:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260411_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_table("legal_cases"):
        op.create_table(
            "legal_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.Unicode(length=255), nullable=False),
            sa.Column("legal_domain", sa.Unicode(length=128), nullable=False),
            sa.Column("status", sa.Unicode(length=32), nullable=False, server_default="intake"),
            sa.Column("risk_level", sa.Unicode(length=32), nullable=False, server_default="low"),
            sa.Column("summary", sa.UnicodeText(), nullable=True),
            sa.Column("desired_outcome", sa.UnicodeText(), nullable=True),
            sa.Column("intake_snapshot_json", sa.UnicodeText(), nullable=True),
            sa.Column("structured_facts_json", sa.UnicodeText(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_legal_cases_id", "legal_cases", ["id"])
        op.create_index("ix_legal_cases_legal_domain", "legal_cases", ["legal_domain"])
        op.create_index("ix_legal_cases_risk_level", "legal_cases", ["risk_level"])
        op.create_index("ix_legal_cases_session_id", "legal_cases", ["session_id"])
        op.create_index("ix_legal_cases_status", "legal_cases", ["status"])
        op.create_index("ix_legal_cases_user_id", "legal_cases", ["user_id"])

    if not _has_table("case_facts"):
        op.create_table(
            "case_facts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("legal_cases.id"), nullable=False),
            sa.Column("source_message_id", sa.Integer(), sa.ForeignKey("chat_messages.id"), nullable=True),
            sa.Column("fact_type", sa.Unicode(length=64), nullable=False),
            sa.Column("fact_key", sa.Unicode(length=128), nullable=False),
            sa.Column("fact_value", sa.UnicodeText(), nullable=False),
            sa.Column("happened_on", sa.Date(), nullable=True),
            sa.Column("is_disputed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_case_facts_case_id", "case_facts", ["case_id"])
        op.create_index("ix_case_facts_fact_key", "case_facts", ["fact_key"])
        op.create_index("ix_case_facts_fact_type", "case_facts", ["fact_type"])
        op.create_index("ix_case_facts_id", "case_facts", ["id"])
        op.create_index("ix_case_facts_source_message_id", "case_facts", ["source_message_id"])

    if _has_table("planner_runs") and not _has_column("planner_runs", "case_id"):
        op.add_column("planner_runs", sa.Column("case_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_planner_runs_case_id_legal_cases", "planner_runs", "legal_cases", ["case_id"], ["id"])
        op.create_index("ix_planner_runs_case_id", "planner_runs", ["case_id"])

    if _has_table("reasoning_runs") and not _has_column("reasoning_runs", "case_id"):
        op.add_column("reasoning_runs", sa.Column("case_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_reasoning_runs_case_id_legal_cases", "reasoning_runs", "legal_cases", ["case_id"], ["id"])
        op.create_index("ix_reasoning_runs_case_id", "reasoning_runs", ["case_id"])

    if _has_table("validation_runs") and not _has_column("validation_runs", "case_id"):
        op.add_column("validation_runs", sa.Column("case_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_validation_runs_case_id_legal_cases", "validation_runs", "legal_cases", ["case_id"], ["id"])
        op.create_index("ix_validation_runs_case_id", "validation_runs", ["case_id"])

    if _has_table("tickets") and not _has_column("tickets", "case_id"):
        op.add_column("tickets", sa.Column("case_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_tickets_case_id_legal_cases", "tickets", "legal_cases", ["case_id"], ["id"])
        op.create_index("ix_tickets_case_id", "tickets", ["case_id"])


def downgrade() -> None:
    if _has_column("tickets", "case_id"):
        op.drop_index("ix_tickets_case_id", table_name="tickets")
        op.drop_constraint("fk_tickets_case_id_legal_cases", "tickets", type_="foreignkey")
        op.drop_column("tickets", "case_id")

    if _has_column("validation_runs", "case_id"):
        op.drop_index("ix_validation_runs_case_id", table_name="validation_runs")
        op.drop_constraint("fk_validation_runs_case_id_legal_cases", "validation_runs", type_="foreignkey")
        op.drop_column("validation_runs", "case_id")

    if _has_column("reasoning_runs", "case_id"):
        op.drop_index("ix_reasoning_runs_case_id", table_name="reasoning_runs")
        op.drop_constraint("fk_reasoning_runs_case_id_legal_cases", "reasoning_runs", type_="foreignkey")
        op.drop_column("reasoning_runs", "case_id")

    if _has_column("planner_runs", "case_id"):
        op.drop_index("ix_planner_runs_case_id", table_name="planner_runs")
        op.drop_constraint("fk_planner_runs_case_id_legal_cases", "planner_runs", type_="foreignkey")
        op.drop_column("planner_runs", "case_id")

    if _has_table("case_facts"):
        op.drop_index("ix_case_facts_source_message_id", table_name="case_facts")
        op.drop_index("ix_case_facts_id", table_name="case_facts")
        op.drop_index("ix_case_facts_fact_type", table_name="case_facts")
        op.drop_index("ix_case_facts_fact_key", table_name="case_facts")
        op.drop_index("ix_case_facts_case_id", table_name="case_facts")
        op.drop_table("case_facts")

    if _has_table("legal_cases"):
        op.drop_index("ix_legal_cases_user_id", table_name="legal_cases")
        op.drop_index("ix_legal_cases_status", table_name="legal_cases")
        op.drop_index("ix_legal_cases_session_id", table_name="legal_cases")
        op.drop_index("ix_legal_cases_risk_level", table_name="legal_cases")
        op.drop_index("ix_legal_cases_legal_domain", table_name="legal_cases")
        op.drop_index("ix_legal_cases_id", table_name="legal_cases")
        op.drop_table("legal_cases")
