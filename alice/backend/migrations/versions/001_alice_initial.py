"""Alice initial tables

Revision ID: 001_alice_initial
Revises:
Create Date: 2026-05-24

Crée les 3 tables Alice sans toucher aux tables existantes de LeComptoirImmo.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = "001_alice_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── alice_admins ───────────────────────────────────────────────────────
    op.create_table(
        "alice_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alice_admins_email", "alice_admins", ["email"])

    # ── alice_plans ────────────────────────────────────────────────────────
    op.create_table(
        "alice_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("property_limit", sa.Integer(), nullable=True),  # null = illimité
        sa.Column("monthly_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── alice_licenses ─────────────────────────────────────────────────────
    op.create_table(
        "alice_licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("gestionnaire_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_limit_override", sa.Integer(), nullable=True),
        sa.Column("monthly_price_override", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("blocked_user_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["plan_id"], ["alice_plans.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_alice_licenses_gestionnaire", "alice_licenses", ["gestionnaire_user_id"], unique=True)

    # ── Seed des plans par défaut ─────────────────────────────────────────────
    import uuid as _uuid
    id1 = str(_uuid.uuid4())
    id2 = str(_uuid.uuid4())
    id3 = str(_uuid.uuid4())
    op.execute(
        sa.text(f"""
        INSERT INTO alice_plans (id, name, description, property_limit, monthly_price, is_active, created_at)
        VALUES
            ('{id1}'::uuid, 'Starter', 'Pour les petits portefeuilles', 10, 29.90, true, now()),
            ('{id2}'::uuid, 'Pro', 'Pour les gestionnaires professionnels', 50, 79.90, true, now()),
            ('{id3}'::uuid, 'Enterprise', 'Sans limite, support prioritaire', NULL, 199.90, true, now())
        ON CONFLICT (name) DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_alice_licenses_gestionnaire", "alice_licenses")
    op.drop_table("alice_licenses")
    op.drop_table("alice_plans")
    op.drop_index("ix_alice_admins_email", "alice_admins")
    op.drop_table("alice_admins")
