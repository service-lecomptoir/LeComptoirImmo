"""Isolation GP — ajout created_by sur contacts et automation_rules.

Revision ID: 013
Revises: 012
Create Date: 2026-05-25
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── contacts ──────────────────────────────────────────────────────────────
    op.add_column(
        "contacts",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_contacts_created_by", "contacts", ["created_by"])

    # ── automation_rules ──────────────────────────────────────────────────────
    op.add_column(
        "automation_rules",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_automation_rules_created_by", "automation_rules", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_automation_rules_created_by", "automation_rules")
    op.drop_column("automation_rules", "created_by")
    op.drop_index("ix_contacts_created_by", "contacts")
    op.drop_column("contacts", "created_by")
