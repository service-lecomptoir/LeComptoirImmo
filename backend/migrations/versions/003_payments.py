"""Phase 4 — Payments (quittances de loyer)

Revision ID: 003
Revises: 002
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Enums — instances réutilisées dans les colonnes ────────────────────────
    payment_status_enum = postgresql.ENUM(
        "pending", "paid", "partial", "late", "cancelled",
        name="payment_status_enum", create_type=False,
    )
    # payment_method_enum existe déjà (migration 002), on la référence sans recréer
    payment_method_enum = postgresql.ENUM(
        "virement", "cheque", "prelevement", "especes",
        name="payment_method_enum", create_type=False,
    )

    payment_status_enum.create(bind, checkfirst=True)
    # payment_method_enum déjà créé, checkfirst=True évite l'erreur
    payment_method_enum.create(bind, checkfirst=True)

    # ── Table payments ─────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_year", sa.Integer, nullable=False),
        sa.Column("period_month", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount_rent", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_charges", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("amount_apl", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_due", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_date", sa.Date, nullable=True),
        sa.Column("payment_method", payment_method_enum, nullable=True),
        sa.Column("status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lease_id", "period_year", "period_month", name="uq_payment_lease_period"),
    )
    op.create_index("ix_payments_lease_id", "payments", ["lease_id"])
    op.create_index("ix_payments_unit_id", "payments", ["unit_id"])
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_period", "payments", ["period_year", "period_month"])


def downgrade() -> None:
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS payment_status_enum")
