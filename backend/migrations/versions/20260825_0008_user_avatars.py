"""Add private employee profile images.

Revision ID: 20260825_0008
Revises: 20260825_0007
Create Date: 2026-08-25 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0008"
down_revision: str | None = "20260825_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_object_key", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("avatar_content_type", sa.String(length=64), nullable=True))
    op.add_column(
        "users", sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "valid_user_avatar",
        "users",
        "(avatar_object_key IS NULL AND avatar_content_type IS NULL) OR "
        "(avatar_object_key IS NOT NULL AND avatar_content_type IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("valid_user_avatar", "users", type_="check")
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_object_key")
