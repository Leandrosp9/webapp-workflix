"""Add learning paths, assignments and certificates.

Revision ID: 20260822_0006
Revises: 20260822_0005
Create Date: 2026-08-22 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0006"
down_revision: str | None = "20260822_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.String(700), server_default="", nullable=False),
        sa.Column("status", sa.String(16), server_default="DRAFT", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('DRAFT', 'PUBLISHED')", name="valid_status"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_paths_company_id", "learning_paths", ["company_id"])
    op.create_index("ix_learning_paths_company_status", "learning_paths", ["company_id", "status"])

    op.create_table(
        "learning_path_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("training_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("position >= 0", name="non_negative_position"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learning_path_id", "position", name="path_item_position"),
        sa.UniqueConstraint("learning_path_id", "training_id", name="path_item_training"),
    )
    op.create_index(
        "ix_learning_path_items_learning_path_id", "learning_path_items", ["learning_path_id"]
    )
    op.create_index("ix_learning_path_items_training_id", "learning_path_items", ["training_id"])
    op.create_index(
        "ix_learning_path_items_company_path",
        "learning_path_items",
        ["company_id", "learning_path_id"],
    )

    op.create_table(
        "learning_path_assignments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learning_path_id", "employee_id", name="path_employee"),
    )
    op.create_index(
        "ix_learning_path_assignments_learning_path_id",
        "learning_path_assignments",
        ["learning_path_id"],
    )
    op.create_index(
        "ix_learning_path_assignments_employee_id",
        "learning_path_assignments",
        ["employee_id"],
    )
    op.create_index(
        "ix_path_assignments_company_employee",
        "learning_path_assignments",
        ["company_id", "employee_id"],
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("user_full_name", sa.String(140), nullable=False),
        sa.Column("user_email", sa.String(254), nullable=False),
        sa.Column("company_name", sa.String(160), nullable=False),
        sa.Column("learning_path_title", sa.String(180), nullable=False),
        sa.Column("workload_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("workload_minutes > 0", name="positive_workload_minutes"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("learning_path_id", "user_id", name="certificate_path_user"),
    )
    op.create_index("ix_certificates_company_id", "certificates", ["company_id"])
    op.create_index("ix_certificates_learning_path_id", "certificates", ["learning_path_id"])
    op.create_index("ix_certificates_user_id", "certificates", ["user_id"])
    op.create_index("ix_certificates_code", "certificates", ["code"], unique=True)
    op.create_index("ix_certificates_company_issued", "certificates", ["company_id", "issued_at"])


def downgrade() -> None:
    op.drop_table("certificates")
    op.drop_table("learning_path_assignments")
    op.drop_table("learning_path_items")
    op.drop_table("learning_paths")
