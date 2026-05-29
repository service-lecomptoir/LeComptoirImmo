"""026 - Régularisation des charges : table charge_regularizations

Revision ID: 026
Revises: 025
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charge_regularizations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lease_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("months_count", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("provisions_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("real_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("old_monthly_provision", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("new_monthly_provision", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="applied"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("charge_regularizations")
