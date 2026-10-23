"""Add request_hash to idempotency_key

Revision ID: 002_add_idempotency_request_hash
Revises: 001_initial_schema
Create Date: 2026-10-23 10:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_idempotency_request_hash"
down_revision: Union[str, Sequence[str], None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "idempotency_key",
        sa.Column("request_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("idempotency_key", "request_hash")
