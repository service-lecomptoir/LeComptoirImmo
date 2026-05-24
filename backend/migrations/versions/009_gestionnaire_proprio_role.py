"""Ajout du rôle gestionnaire_proprio (fusion gestionnaire + propriétaire)."""
import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'gestionnaire_proprio'"
    ))


def downgrade():
    # PostgreSQL ne supporte pas DROP VALUE sur un enum — pas de rollback possible
    pass
