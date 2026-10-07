"""cache speech clips in the database

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-07 05:35:12.392486
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tts_clips",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("audio", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_tts_clips")),
    )


def downgrade() -> None:
    op.drop_table("tts_clips")
