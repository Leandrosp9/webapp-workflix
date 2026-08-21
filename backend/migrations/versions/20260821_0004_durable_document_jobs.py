"""Add the durable document-processing job queue.

Revision ID: 20260821_0004
Revises: 20260821_0003
Create Date: 2026-08-21 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0004"
down_revision: str | None = "20260821_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("leased_until", sa.DateTime(timezone=True)),
        sa.Column("worker_id", sa.String(160)),
        sa.Column("last_error_code", sa.String(80)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("attempts >= 0", name="non_negative_attempts"),
        sa.CheckConstraint("max_attempts > 0", name="positive_max_attempts"),
        sa.CheckConstraint("attempts <= max_attempts", name="attempts_within_limit"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'RETRYING', 'COMPLETED', 'DEAD_LETTER')",
            name="valid_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id", name="uq_document_processing_jobs_document_version"
        ),
    )
    op.create_index(
        "ix_document_processing_jobs_company_id", "document_processing_jobs", ["company_id"]
    )
    op.create_index(
        "ix_document_processing_jobs_document_version_id",
        "document_processing_jobs",
        ["document_version_id"],
    )
    op.create_index(
        "ix_document_processing_jobs_claim",
        "document_processing_jobs",
        ["status", "available_at", "leased_until"],
    )
    op.create_index(
        "ix_document_processing_jobs_company_status",
        "document_processing_jobs",
        ["company_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("document_processing_jobs")
