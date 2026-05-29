"""025 - Révision du loyer (IRL) : table irl_indices + colonnes bail

Revision ID: 025
Revises: 024
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "irl_indices",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(8, 2), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manuel"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("year", "quarter", name="uq_irl_year_quarter"),
    )
    op.add_column("leases", sa.Column("irl_quarter", sa.Integer(), nullable=True))
    op.add_column("leases", sa.Column("irl_base_index", sa.Numeric(8, 2), nullable=True))
    op.add_column("leases", sa.Column("last_revision_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("leases", "last_revision_date")
    op.drop_column("leases", "irl_base_index")
    op.drop_column("leases", "irl_quarter")
    op.drop_table("irl_indices")
