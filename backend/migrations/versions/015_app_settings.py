"""015 - Table app_settings (configuration dynamique scheduler et autres)

Revision ID: 015
Revises: 014
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Seed par défaut
    op.execute("INSERT INTO app_settings (key, value) VALUES ('avis_generation_day', '1') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO app_settings (key, value) VALUES ('avis_generation_hour', '7') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO app_settings (key, value) VALUES ('avis_generation_minute', '30') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table("app_settings")
