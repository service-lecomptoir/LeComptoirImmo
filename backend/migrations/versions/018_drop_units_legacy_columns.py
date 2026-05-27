"""018 - Nettoyage des reliques de la fusion bien/logement

Supprime les colonnes loyer/charges/dépôt/pièces devenues inutiles sur `properties`
(portées par le contrat), les colonnes de lien `unit_id` (entité logement supprimée)
et la table `units`.

Revision ID: 018
Revises: 017
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

_UNIT_ID_TABLES = ["leases", "payments", "avis_echeances", "inspections", "entretiens", "tickets"]
_PROP_COLS = ["base_rent", "charges_amount", "deposit_months", "rooms", "bedrooms"]


def upgrade() -> None:
    for col in _PROP_COLS:
        op.execute(f"ALTER TABLE properties DROP COLUMN IF EXISTS {col}")
    # Retirer les colonnes de lien (supprime aussi leurs FK) puis la table units.
    for tbl in _UNIT_ID_TABLES:
        op.execute(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS unit_id")
    op.execute("DROP TABLE IF EXISTS units")


def downgrade() -> None:
    # Recrée le schéma (sans les données ni les FK d'origine).
    op.add_column("properties", sa.Column("base_rent", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("properties", sa.Column("charges_amount", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("properties", sa.Column("deposit_months", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("properties", sa.Column("rooms", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("bedrooms", sa.Integer(), nullable=True))
    for tbl in _UNIT_ID_TABLES:
        op.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS unit_id UUID")
