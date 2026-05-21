"""Phase 7 — Notifications

Revision ID: 004
Revises: 003
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Enums — instances réutilisées dans les colonnes ────────────────────────
    notification_type_enum = postgresql.ENUM(
        "loyer_retard", "bail_expire_soon", "bail_expire", "paiement_recu", "systeme",
        name="notification_type_enum", create_type=False,
    )
    notification_priority_enum = postgresql.ENUM(
        "low", "normal", "high", "urgent",
        name="notification_priority_enum", create_type=False,
    )

    notification_type_enum.create(bind, checkfirst=True)
    notification_priority_enum.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("priority", notification_priority_enum, nullable=False, server_default="normal"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_type", "notifications", ["notification_type"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notification_priority_enum")
    op.execute("DROP TYPE IF EXISTS notification_type_enum")
