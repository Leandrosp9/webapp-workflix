"""Add hybrid OCR provenance and immutable PDF acknowledgements.

Revision ID: 20260822_0005
Revises: 20260821_0004
Create Date: 2026-08-22 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0005"
down_revision: str | None = "20260821_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column("ocr_page_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "non_negative_ocr_page_count", "document_versions", "ocr_page_count >= 0"
    )
    op.create_check_constraint(
        "ocr_pages_within_page_count",
        "document_versions",
        "ocr_page_count <= page_count",
    )
    op.add_column(
        "document_pages",
        sa.Column("extraction_method", sa.String(16), server_default="NATIVE", nullable=False),
    )
    op.create_check_constraint(
        "valid_extraction_method",
        "document_pages",
        "extraction_method IN ('NATIVE', 'OCR', 'NONE')",
    )
    op.create_table(
        "document_acknowledgements",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("training_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_email", sa.String(254), nullable=False),
        sa.Column("user_full_name", sa.String(140), nullable=False),
        sa.Column("document_title", sa.String(180), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("document_checksum", sa.String(64), nullable=False),
        sa.Column("attestation", sa.String(500), nullable=False),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("version_number > 0", name="positive_version_number"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "document_version_id",
            name="uq_document_acknowledgements_user_version",
        ),
    )
    op.create_index(
        "ix_document_acknowledgements_company_training_time",
        "document_acknowledgements",
        ["company_id", "training_id", "acknowledged_at"],
    )
    op.create_index(
        "ix_document_acknowledgements_company_user",
        "document_acknowledgements",
        ["company_id", "user_id"],
    )
    op.create_index(
        "ix_document_acknowledgements_company_version",
        "document_acknowledgements",
        ["company_id", "document_version_id"],
    )


def downgrade() -> None:
    op.drop_table("document_acknowledgements")
    op.drop_constraint("valid_extraction_method", "document_pages", type_="check")
    op.drop_column("document_pages", "extraction_method")
    op.drop_constraint("ocr_pages_within_page_count", "document_versions", type_="check")
    op.drop_constraint("non_negative_ocr_page_count", "document_versions", type_="check")
    op.drop_column("document_versions", "ocr_page_count")
