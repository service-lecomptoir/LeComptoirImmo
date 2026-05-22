"""Module tickets, entretiens et prestataires

Revision ID: 007
Revises: 006
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Création des enums ─────────────────────────────────────────────────
    ticket_status = postgresql.ENUM(
        'open', 'in_progress', 'resolved', 'closed',
        name='ticket_status_enum', create_type=False,
    )
    ticket_priority = postgresql.ENUM(
        'low', 'medium', 'high', 'urgent',
        name='ticket_priority_enum', create_type=False,
    )
    ticket_category = postgresql.ENUM(
        'incident', 'question', 'demande', 'autre',
        name='ticket_category_enum', create_type=False,
    )
    entretien_type = postgresql.ENUM(
        'preventif', 'correctif', 'inspection',
        name='entretien_type_enum', create_type=False,
    )
    entretien_status = postgresql.ENUM(
        'planifie', 'en_cours', 'termine', 'annule',
        name='entretien_status_enum', create_type=False,
    )
    entretien_frequency = postgresql.ENUM(
        'unique', 'mensuel', 'trimestriel', 'semestriel', 'annuel',
        name='entretien_frequency_enum', create_type=False,
    )

    for enum in [ticket_status, ticket_priority, ticket_category,
                 entretien_type, entretien_status, entretien_frequency]:
        enum.create(bind, checkfirst=True)

    # ── 2. Table prestataires ─────────────────────────────────────────────────
    op.create_table(
        "prestataires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("siret", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_prestataires_name", "prestataires", ["name"])

    # ── 3. Table entretiens ───────────────────────────────────────────────────
    op.create_table(
        "entretiens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", entretien_type, nullable=False, server_default="preventif"),
        sa.Column("status", entretien_status, nullable=False, server_default="planifie"),
        sa.Column("frequency", entretien_frequency, nullable=False, server_default="unique"),
        sa.Column("scheduled_date", sa.Date, nullable=False),
        sa.Column("completed_date", sa.Date, nullable=True),
        sa.Column("next_date", sa.Date, nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prestataire_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prestataires.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_entretiens_scheduled_date", "entretiens", ["scheduled_date"])
    op.create_index("ix_entretiens_status", "entretiens", ["status"])
    op.create_index("ix_entretiens_property_id", "entretiens", ["property_id"])

    # ── 4. Table tickets ──────────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", ticket_category, nullable=False, server_default="autre"),
        sa.Column("status", ticket_status, nullable=False, server_default="open"),
        sa.Column("priority", ticket_priority, nullable=False, server_default="medium"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tickets_tenant_id", "tickets", ["tenant_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_category", "tickets", ["category"])

    # ── 5. Table ticket_messages ──────────────────────────────────────────────
    op.create_table(
        "ticket_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ticket_messages_ticket_id", "ticket_messages", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("ticket_messages")
    op.drop_table("tickets")
    op.drop_table("entretiens")
    op.drop_table("prestataires")
    op.execute(sa.text("DROP TYPE IF EXISTS ticket_status_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS ticket_priority_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS ticket_category_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS entretien_type_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS entretien_status_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS entretien_frequency_enum"))
