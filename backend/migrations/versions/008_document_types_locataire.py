"""Nouveaux types de documents + profil locataire

Revision ID: 008
Revises: 007
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

# Nouveaux types à ajouter à document_type_enum
_NEW_DOC_TYPES = [
    "assurance",
    "regularisation_charges",
    "revision_loyer",
    "taxe_ordures",
]


def upgrade() -> None:
    for value in _NEW_DOC_TYPES:
        op.execute(
            sa.text(f"ALTER TYPE document_type_enum ADD VALUE IF NOT EXISTS '{value}'")
        )


def downgrade() -> None:
    # PostgreSQL ne supporte pas la suppression de valeurs d'enum
    pass
