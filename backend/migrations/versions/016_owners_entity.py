"""016 - Entité propriétaire (fiche Owner) + lien sur le bien

Crée la table `owners` (fiche bailleur, compte de connexion optionnel via user_id),
ajoute `properties.owner_id`, puis rapatrie les propriétaires existants (comptes
utilisateur + propriétaire "texte" owner_name) en fiches et relie les biens.

Revision ID: 016
Revises: 015
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("civility", sa.Enum("M", "Mme", "Autre", name="civility_enum", create_type=False), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(150), nullable=False, index=True),
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("national_id", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("phone2", sa.String(30), nullable=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("iban", sa.String(34), nullable=True),
        sa.Column("bic", sa.String(11), nullable=True),
        sa.Column("bank_holder", sa.String(150), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column(
        "properties",
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("owners.id", ondelete="SET NULL"), nullable=True, index=True),
    )

    # ── Backfill ────────────────────────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO owners (id, last_name, email, phone, address, iban, bic, bank_holder, user_id, created_by)
        SELECT gen_random_uuid(), u.full_name, u.email, u.phone, u.address,
               u.iban, u.bic, u.bank_holder, u.id, u.created_by
        FROM users u
        WHERE (u.role IN ('proprietaire', 'gestionnaire_proprio')
               OR u.id IN (SELECT DISTINCT owner_user_id FROM properties WHERE owner_user_id IS NOT NULL))
          AND NOT EXISTS (SELECT 1 FROM owners o WHERE o.user_id = u.id)
        """
    )
    op.execute(
        """
        UPDATE properties p SET owner_id = o.id
        FROM owners o
        WHERE o.user_id = p.owner_user_id
          AND p.owner_user_id IS NOT NULL
          AND p.owner_id IS NULL
        """
    )
    op.execute(
        """
        DO $$
        DECLARE r RECORD; new_id uuid;
        BEGIN
          FOR r IN SELECT id, owner_name, owner_email, owner_phone, created_by
                   FROM properties
                   WHERE owner_id IS NULL AND owner_user_id IS NULL
                     AND owner_name IS NOT NULL AND btrim(owner_name) <> ''
          LOOP
            INSERT INTO owners (id, last_name, email, phone, created_by)
            VALUES (gen_random_uuid(), r.owner_name,
                    NULLIF(btrim(r.owner_email), ''), NULLIF(btrim(r.owner_phone), ''),
                    r.created_by)
            RETURNING id INTO new_id;
            UPDATE properties SET owner_id = new_id WHERE id = r.id;
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_column("properties", "owner_id")
    op.drop_table("owners")
