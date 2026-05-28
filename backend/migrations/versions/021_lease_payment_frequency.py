"""021 - Fréquence d'appel du loyer sur le contrat

Ajoute `leases.payment_frequency` (texte : 'mensuelle' | 'bimestrielle' |
'trimestrielle' | 'semestrielle' | 'annuelle', défaut 'mensuelle').

Revision ID: 021
Revises: 020
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leases",
        sa.Column("payment_frequency", sa.String(20), nullable=False, server_default="mensuelle"),
    )


def downgrade() -> None:
    op.drop_column("leases", "payment_frequency")
