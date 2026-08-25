"""Add certificates for completed trainings.

Revision ID: 20260825_0007
Revises: 20260822_0006
Create Date: 2026-08-25 01:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0007"
down_revision: str | None = "20260822_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cpf", sa.String(length=11), nullable=True))
    op.create_unique_constraint("user_company_cpf", "users", ["company_id", "cpf"])
    op.add_column(
        "certificates",
        sa.Column(
            "certificate_type",
            sa.String(length=16),
            server_default="LEARNING_PATH",
            nullable=False,
        ),
    )
    op.add_column("certificates", sa.Column("training_id", sa.Uuid(), nullable=True))
    op.add_column("certificates", sa.Column("user_cpf", sa.String(length=11), nullable=True))
    op.alter_column("certificates", "learning_path_id", existing_type=sa.Uuid(), nullable=True)
    op.create_foreign_key(
        "fk_certificates_training_id",
        "certificates",
        "trainings",
        ["training_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_certificates_training_id", "certificates", ["training_id"])
    op.create_unique_constraint(
        "certificate_training_user", "certificates", ["training_id", "user_id"]
    )
    op.create_check_constraint(
        "valid_certificate_scope",
        "certificates",
        "(certificate_type = 'LEARNING_PATH' AND learning_path_id IS NOT NULL "
        "AND training_id IS NULL) OR "
        "(certificate_type = 'TRAINING' AND learning_path_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("valid_certificate_scope", "certificates", type_="check")
    op.drop_constraint("certificate_training_user", "certificates", type_="unique")
    op.drop_index("ix_certificates_training_id", table_name="certificates")
    op.drop_constraint("fk_certificates_training_id", "certificates", type_="foreignkey")
    op.execute("DELETE FROM certificates WHERE certificate_type = 'TRAINING'")
    op.drop_column("certificates", "user_cpf")
    op.drop_column("certificates", "training_id")
    op.drop_column("certificates", "certificate_type")
    op.alter_column("certificates", "learning_path_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("user_company_cpf", "users", type_="unique")
    op.drop_column("users", "cpf")
