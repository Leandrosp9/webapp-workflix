"""Enable PostgreSQL extensions required by the platform.

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21 00:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260821_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    # Extensions can be shared by data outside this migration. Dropping them
    # automatically would make rollback unexpectedly destructive.
    pass
