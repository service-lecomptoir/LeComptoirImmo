"""020 - Période réellement couverte par un avis d'échéance

Ajoute `avis_echeances.period_start` / `period_end` (Date, nullable) pour stocker la
période couverte (prorata d'entrée/sortie selon la règle d'appel de loyer du bail).

Revision ID: 020
Revises: 019
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("avis_echeances", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("avis_echeances", sa.Column("period_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("avis_echeances", "period_end")
    op.drop_column("avis_echeances", "period_start")
