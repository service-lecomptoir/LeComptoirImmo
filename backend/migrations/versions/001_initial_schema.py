"""Initial schema — Phase 1 & 2

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('lecture','comptable','gestionnaire','admin')")
    op.execute("CREATE TYPE civility_enum AS ENUM ('M','Mme','Autre')")
    op.execute("CREATE TYPE property_type_enum AS ENUM ('immeuble','maison','appartement','local_commercial','autre')")
    op.execute("CREATE TYPE unit_type_enum AS ENUM ('studio','T1','T2','T3','T4','T5+','maison','local','autre')")
    op.execute("CREATE TYPE entity_type_enum AS ENUM ('tenant','lease','unit','property','inspection')")
    op.execute("""CREATE TYPE document_type_enum AS ENUM (
        'cni','passeport','justificatif_domicile','justificatif_revenus','avis_imposition',
        'contrat_bail','avenant','quittance','attestation_caf','attestation_tiers',
        'etat_des_lieux','photo','autre'
    )""")

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('role', sa.Enum('lecture','comptable','gestionnaire','admin', name='user_role', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ── tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('civility', sa.Enum('M','Mme','Autre', name='civility_enum', create_type=False), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('birth_date', sa.Date, nullable=True),
        sa.Column('birth_place', sa.String(150), nullable=True),
        sa.Column('national_id', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('phone2', sa.String(30), nullable=True),
        sa.Column('employer', sa.String(200), nullable=True),
        sa.Column('employer_phone', sa.String(30), nullable=True),
        sa.Column('monthly_income', sa.Numeric(10, 2), nullable=True),
        sa.Column('income_source', sa.String(100), nullable=True),
        sa.Column('notes', sa.String(2000), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tenants_last_name', 'tenants', ['last_name'])
    op.create_index('ix_tenants_email', 'tenants', ['email'])

    # ── properties ────────────────────────────────────────────────────────────
    op.create_table(
        'properties',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('reference', sa.String(50), nullable=True),
        sa.Column('address', sa.String(300), nullable=False),
        sa.Column('address2', sa.String(200), nullable=True),
        sa.Column('zip_code', sa.String(10), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('country', sa.String(50), nullable=False, server_default='France'),
        sa.Column('property_type', sa.Enum('immeuble','maison','appartement','local_commercial','autre', name='property_type_enum', create_type=False), nullable=False),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('owner_email', sa.String(255), nullable=True),
        sa.Column('owner_phone', sa.String(30), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('year_built', sa.Integer, nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_properties_name', 'properties', ['name'])

    # ── units ─────────────────────────────────────────────────────────────────
    op.create_table(
        'units',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('property_id', UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('unit_ref', sa.String(50), nullable=False),
        sa.Column('unit_type', sa.Enum('studio','T1','T2','T3','T4','T5+','maison','local','autre', name='unit_type_enum', create_type=False), nullable=False),
        sa.Column('floor', sa.Integer, nullable=True),
        sa.Column('building', sa.String(50), nullable=True),
        sa.Column('area_sqm', sa.Numeric(8, 2), nullable=True),
        sa.Column('rooms', sa.Integer, nullable=True),
        sa.Column('bedrooms', sa.Integer, nullable=True),
        sa.Column('bathrooms', sa.Integer, nullable=True),
        sa.Column('base_rent', sa.Numeric(10, 2), nullable=False),
        sa.Column('charges_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('deposit_months', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_occupied', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_available', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_units_property_id', 'units', ['property_id'])

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.Enum('tenant','lease','unit','property','inspection', name='entity_type_enum', create_type=False), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.Text, nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=True),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('uploaded_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_documents_entity', 'documents', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('units')
    op.drop_table('properties')
    op.drop_table('tenants')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS document_type_enum")
    op.execute("DROP TYPE IF EXISTS entity_type_enum")
    op.execute("DROP TYPE IF EXISTS unit_type_enum")
    op.execute("DROP TYPE IF EXISTS property_type_enum")
    op.execute("DROP TYPE IF EXISTS civility_enum")
    op.execute("DROP TYPE IF EXISTS user_role")
