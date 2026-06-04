"""add legal provisions baseline

Revision ID: 20260413_0002
Revises: 20260411_0001
Create Date: 2026-04-13 23:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260413_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("legal_provisions"):
        return

    op.create_table(
        "legal_provisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("parent_provision_id", sa.Integer(), sa.ForeignKey("legal_provisions.id"), nullable=True),
        sa.Column("provision_level", sa.Unicode(length=16), nullable=False),
        sa.Column("article_number", sa.Unicode(length=32), nullable=True),
        sa.Column("clause_number", sa.Unicode(length=32), nullable=True),
        sa.Column("point_code", sa.Unicode(length=32), nullable=True),
        sa.Column("heading", sa.Unicode(length=500), nullable=True),
        sa.Column("content", sa.UnicodeText(), nullable=False),
        sa.Column("citation_label", sa.Unicode(length=255), nullable=True),
        sa.Column("sort_key", sa.Unicode(length=128), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("legal_status", sa.Unicode(length=32), nullable=True, server_default="active"),
        sa.Column("metadata_json", sa.UnicodeText(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_legal_provisions_id", "legal_provisions", ["id"])
    op.create_index("ix_legal_provisions_document_id", "legal_provisions", ["document_id"])
    op.create_index("ix_legal_provisions_parent_provision_id", "legal_provisions", ["parent_provision_id"])
    op.create_index("ix_legal_provisions_provision_level", "legal_provisions", ["provision_level"])
    op.create_index("ix_legal_provisions_article_number", "legal_provisions", ["article_number"])
    op.create_index("ix_legal_provisions_sort_key", "legal_provisions", ["sort_key"])


def downgrade() -> None:
    if not _has_table("legal_provisions"):
        return

    op.drop_index("ix_legal_provisions_sort_key", table_name="legal_provisions")
    op.drop_index("ix_legal_provisions_article_number", table_name="legal_provisions")
    op.drop_index("ix_legal_provisions_provision_level", table_name="legal_provisions")
    op.drop_index("ix_legal_provisions_parent_provision_id", table_name="legal_provisions")
    op.drop_index("ix_legal_provisions_document_id", table_name="legal_provisions")
    op.drop_index("ix_legal_provisions_id", table_name="legal_provisions")
    op.drop_table("legal_provisions")
