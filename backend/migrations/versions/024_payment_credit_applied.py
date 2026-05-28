"""024 - Crédit (avance) appliqué à une échéance

Ajoute `payments.credit_applied` : montant de trop-perçu (avance) issu d'échéances
précédentes du même bail, automatiquement déduit de cette échéance.

Revision ID: 024
Revises: 023
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("credit_applied", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("payments", "credit_applied")
