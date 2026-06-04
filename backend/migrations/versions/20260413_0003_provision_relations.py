"""add provision relations baseline

Revision ID: 20260413_0003
Revises: 20260413_0002
Create Date: 2026-04-13 23:55:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260413_0003"
down_revision = "20260413_0002"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("provision_relations"):
        return

    op.create_table(
        "provision_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("source_provision_id", sa.Integer(), sa.ForeignKey("legal_provisions.id"), nullable=False),
        sa.Column("target_document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("target_provision_id", sa.Integer(), sa.ForeignKey("legal_provisions.id"), nullable=False),
        sa.Column("relation_type", sa.Unicode(length=64), nullable=False),
        sa.Column("relation_label", sa.Unicode(length=255), nullable=True),
        sa.Column("source_excerpt", sa.UnicodeText(), nullable=True),
        sa.Column("target_excerpt", sa.UnicodeText(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("extraction_method", sa.Unicode(length=32), nullable=True),
        sa.Column("metadata_json", sa.UnicodeText(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provision_relations_id", "provision_relations", ["id"])
    op.create_index("ix_provision_relations_source_document_id", "provision_relations", ["source_document_id"])
    op.create_index("ix_provision_relations_source_provision_id", "provision_relations", ["source_provision_id"])
    op.create_index("ix_provision_relations_target_document_id", "provision_relations", ["target_document_id"])
    op.create_index("ix_provision_relations_target_provision_id", "provision_relations", ["target_provision_id"])
    op.create_index("ix_provision_relations_relation_type", "provision_relations", ["relation_type"])


def downgrade() -> None:
    if not _has_table("provision_relations"):
        return

    op.drop_index("ix_provision_relations_relation_type", table_name="provision_relations")
    op.drop_index("ix_provision_relations_target_provision_id", table_name="provision_relations")
    op.drop_index("ix_provision_relations_target_document_id", table_name="provision_relations")
    op.drop_index("ix_provision_relations_source_provision_id", table_name="provision_relations")
    op.drop_index("ix_provision_relations_source_document_id", table_name="provision_relations")
    op.drop_index("ix_provision_relations_id", table_name="provision_relations")
    op.drop_table("provision_relations")
