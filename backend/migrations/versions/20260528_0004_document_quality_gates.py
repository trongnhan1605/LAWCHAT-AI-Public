"""add document identity and quality gate fields

Revision ID: 20260528_0004
Revises: 20260413_0003
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0004"
down_revision = "20260413_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_sha256", sa.Unicode(length=64), nullable=True))
    op.add_column("documents", sa.Column("source_identity", sa.Unicode(length=512), nullable=True))
    op.add_column("documents", sa.Column("ingestion_quality_status", sa.Unicode(length=32), nullable=True))
    op.add_column("documents", sa.Column("ingestion_quality_notes", sa.UnicodeText(), nullable=True))
    op.add_column("documents", sa.Column("retrieval_visibility", sa.Unicode(length=32), nullable=True))
    op.create_index(op.f("ix_documents_content_sha256"), "documents", ["content_sha256"], unique=False)
    op.create_index(op.f("ix_documents_source_identity"), "documents", ["source_identity"], unique=False)
    op.execute("UPDATE documents SET ingestion_quality_status = 'pending' WHERE ingestion_quality_status IS NULL")
    op.execute("UPDATE documents SET retrieval_visibility = CASE WHEN metadata_review_status = 'reviewed' THEN 'indexed_verified' ELSE 'indexed_unreviewed' END WHERE retrieval_visibility IS NULL")
    op.alter_column("documents", "ingestion_quality_status", nullable=False)
    op.alter_column("documents", "retrieval_visibility", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_source_identity"), table_name="documents")
    op.drop_index(op.f("ix_documents_content_sha256"), table_name="documents")
    op.drop_column("documents", "retrieval_visibility")
    op.drop_column("documents", "ingestion_quality_notes")
    op.drop_column("documents", "ingestion_quality_status")
    op.drop_column("documents", "source_identity")
    op.drop_column("documents", "content_sha256")
