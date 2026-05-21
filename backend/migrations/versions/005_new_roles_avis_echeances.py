"""Phase 10 — Nouveaux rôles (propriétaire/locataire) + avis d'échéances

Revision ID: 005
Revises: 004
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Ajouter les nouvelles valeurs au type user_role ─────────────────────
    # PostgreSQL permet ADD VALUE mais pas DROP VALUE — on garde lecture/comptable
    # comme valeurs legacy non utilisées
    bind.execute(sa.text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'proprietaire'"))
    bind.execute(sa.text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'locataire'"))

    # ── 2. Colonne owner_user_id sur properties ────────────────────────────────
    op.add_column(
        "properties",
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_properties_owner_user_id", "properties", ["owner_user_id"])

    # ── 3. Colonne user_id sur tenants ────────────────────────────────────────
    op.add_column(
        "tenants",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_tenants_user_id", "tenants", ["user_id"])

    # ── 4. Table avis_echeances ───────────────────────────────────────────────
    avis_status_enum = postgresql.ENUM(
        "brouillon", "envoye", "acquitte",
        name="avis_echeance_status_enum", create_type=False,
    )
    avis_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "avis_echeances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_year", sa.Integer, nullable=False),
        sa.Column("period_month", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount_rent", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_charges", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("amount_apl", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", avis_status_enum, nullable=False, server_default="brouillon"),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        # NULL = généré automatiquement par le scheduler
        sa.Column("generated_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lease_id", "period_year", "period_month",
                            name="uq_avis_lease_period"),
    )
    op.create_index("ix_avis_echeances_lease_id", "avis_echeances", ["lease_id"])
    op.create_index("ix_avis_echeances_tenant_id", "avis_echeances", ["tenant_id"])
    op.create_index("ix_avis_echeances_period", "avis_echeances", ["period_year", "period_month"])
    op.create_index("ix_avis_echeances_status", "avis_echeances", ["status"])


def downgrade() -> None:
    op.drop_table("avis_echeances")
    op.execute("DROP TYPE IF EXISTS avis_echeance_status_enum")
    op.drop_index("ix_tenants_user_id", "tenants")
    op.drop_column("tenants", "user_id")
    op.drop_index("ix_properties_owner_user_id", "properties")
    op.drop_column("properties", "owner_user_id")
    # Note: impossible de supprimer des valeurs d'un enum PostgreSQL sans recréer le type
