"""website content management

Revision ID: 20260604_0005
Revises: 20260528_0004
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Unicode(length=255), nullable=False),
        sa.Column("slug", sa.Unicode(length=255), nullable=False),
        sa.Column("category", sa.Unicode(length=120), nullable=False),
        sa.Column("excerpt", sa.Unicode(length=600), nullable=False),
        sa.Column("source_url", sa.Unicode(length=600), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_content_articles_id"), "content_articles", ["id"], unique=False)
    op.create_index(op.f("ix_content_articles_slug"), "content_articles", ["slug"], unique=True)

    op.create_table(
        "lawyer_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.Unicode(length=160), nullable=False),
        sa.Column("slug", sa.Unicode(length=255), nullable=False),
        sa.Column("title", sa.Unicode(length=180), nullable=False),
        sa.Column("location", sa.Unicode(length=160), nullable=False),
        sa.Column("specialties", sa.Unicode(length=500), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Unicode(length=20), nullable=True),
        sa.Column("bio", sa.Unicode(length=700), nullable=True),
        sa.Column("avatar_url", sa.Unicode(length=600), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lawyer_profiles_id"), "lawyer_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_lawyer_profiles_slug"), "lawyer_profiles", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_lawyer_profiles_slug"), table_name="lawyer_profiles")
    op.drop_index(op.f("ix_lawyer_profiles_id"), table_name="lawyer_profiles")
    op.drop_table("lawyer_profiles")
    op.drop_index(op.f("ix_content_articles_slug"), table_name="content_articles")
    op.drop_index(op.f("ix_content_articles_id"), table_name="content_articles")
    op.drop_table("content_articles")
