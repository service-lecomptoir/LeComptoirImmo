"""Phase 3 — Leases & Inspections

Revision ID: 002
Revises: 001
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Enums — instances réutilisées dans les colonnes ────────────────────────
    lease_type_enum = postgresql.ENUM(
        "vide", "meuble", "mobilite", "commercial",
        name="lease_type_enum", create_type=False,
    )
    payment_method_enum = postgresql.ENUM(
        "virement", "cheque", "prelevement", "especes",
        name="payment_method_enum", create_type=False,
    )
    inspection_type_enum = postgresql.ENUM(
        "entree", "sortie", "contradictoire", "periodique",
        name="inspection_type_enum", create_type=False,
    )
    overall_condition_enum = postgresql.ENUM(
        "tres_bon", "bon", "moyen", "mauvais",
        name="overall_condition_enum", create_type=False,
    )

    for enum in [lease_type_enum, payment_method_enum, inspection_type_enum, overall_condition_enum]:
        enum.create(bind, checkfirst=True)

    # ── Table leases ───────────────────────────────────────────────────────────
    op.create_table(
        "leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lease_type", lease_type_enum, nullable=False, server_default="vide"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("notice_date", sa.Date, nullable=True),
        sa.Column("rent_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("charges_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_day", sa.Integer, nullable=False, server_default="1"),
        sa.Column("payment_method", payment_method_enum, nullable=False, server_default="virement"),
        sa.Column("apl_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("apl_tiers_payant", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("has_guarantor", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("guarantor_name", sa.String(200), nullable=True),
        sa.Column("guarantor_email", sa.String(255), nullable=True),
        sa.Column("guarantor_phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_leases_property_id", "leases", ["property_id"])
    op.create_index("ix_leases_unit_id", "leases", ["unit_id"])
    op.create_index("ix_leases_tenant_id", "leases", ["tenant_id"])
    op.create_index("ix_leases_is_active", "leases", ["is_active"])

    # ── Table inspections ──────────────────────────────────────────────────────
    op.create_table(
        "inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leases.id", ondelete="CASCADE"), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_type", inspection_type_enum, nullable=False),
        sa.Column("inspection_date", sa.Date, nullable=False),
        sa.Column("inspector_name", sa.String(200), nullable=True),
        sa.Column("tenant_present", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("overall_condition", overall_condition_enum, nullable=True),
        sa.Column("notes", sa.String(3000), nullable=True),
        sa.Column("rooms_data", postgresql.JSONB, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_inspections_lease_id", "inspections", ["lease_id"])
    op.create_index("ix_inspections_unit_id", "inspections", ["unit_id"])


def downgrade() -> None:
    op.drop_table("inspections")
    op.drop_table("leases")
    op.execute("DROP TYPE IF EXISTS overall_condition_enum")
    op.execute("DROP TYPE IF EXISTS inspection_type_enum")
    op.execute("DROP TYPE IF EXISTS payment_method_enum")
    op.execute("DROP TYPE IF EXISTS lease_type_enum")
