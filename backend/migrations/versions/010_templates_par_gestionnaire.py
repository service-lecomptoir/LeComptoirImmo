"""Templates isolés par gestionnaire — ajout gestionnaire_id

Revision ID: 010
Revises: 009
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajout de la colonne gestionnaire_id (nullable pour compatibilité)
    op.add_column(
        "document_templates",
        sa.Column(
            "gestionnaire_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_templates_gestionnaire_id",
        "document_templates",
        ["gestionnaire_id"],
    )
    # Les templates existants sans gestionnaire_id deviennent inaccessibles
    # aux gestionnaires (visibles uniquement par admin). Les gestionnaires
    # doivent créer leurs propres modèles via "Modèles par défaut".


def downgrade() -> None:
    op.drop_index("ix_document_templates_gestionnaire_id", table_name="document_templates")
    op.drop_column("document_templates", "gestionnaire_id")
