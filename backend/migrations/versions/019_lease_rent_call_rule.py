"""019 - Règle d'appel de loyer sur le contrat

Ajoute `leases.rent_call_rule` (texte : 'contractuelle' | 'calendrier', défaut
'calendrier').

Revision ID: 019
Revises: 018
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leases",
        sa.Column("rent_call_rule", sa.String(20), nullable=False, server_default="calendrier"),
    )


def downgrade() -> None:
    op.drop_column("leases", "rent_call_rule")
