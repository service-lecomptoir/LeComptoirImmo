"""023 - Déclaration de paiement par le locataire (à valider)

Ajoute `payments.declared_at`, `payments.declared_method`, `payments.declared_amount`.
Quand le locataire déclare avoir payé (virement/espèces), ces champs sont renseignés ;
le gestionnaire valide → le paiement est enregistré (encaissé).

Revision ID: 023
Revises: 022
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("declared_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("declared_method", sa.String(20), nullable=True))
    op.add_column("payments", sa.Column("declared_amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "declared_amount")
    op.drop_column("payments", "declared_method")
    op.drop_column("payments", "declared_at")
