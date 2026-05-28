"""022 - Période réellement couverte par un loyer (multi-mois)

Ajoute `payments.period_start` / `payments.period_end` (nullable) pour stocker
l'étendue couverte par un loyer dont la fréquence d'appel est > mensuelle.

Revision ID: 022
Revises: 021
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("payments", sa.Column("period_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "period_end")
    op.drop_column("payments", "period_start")
