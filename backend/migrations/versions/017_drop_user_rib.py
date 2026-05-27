"""017 - Suppression du RIB sur le compte utilisateur

Le RIB du bailleur est désormais porté uniquement par la fiche propriétaire
(table owners, migration 016). On retire les colonnes iban/bic/bank_holder de
`users`, devenues inutilisées.

Revision ID: 017
Revises: 016
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS iban")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS bic")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS bank_holder")


def downgrade() -> None:
    op.add_column("users", sa.Column("iban", sa.String(34), nullable=True))
    op.add_column("users", sa.Column("bic", sa.String(11), nullable=True))
    op.add_column("users", sa.Column("bank_holder", sa.String(150), nullable=True))
