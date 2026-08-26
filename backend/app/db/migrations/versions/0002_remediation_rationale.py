"""add remediation.rationale — persist the remediation agent's stated reason

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default "" backfills existing rows; the old app version ignores the column.
    op.add_column(
        "remediation",
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("remediation", "rationale")
