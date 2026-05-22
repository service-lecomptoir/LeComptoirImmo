"""Phase 6 — Contacts, Automatisation, Templates de documents

Revision ID: 006
Revises: 005
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Table contacts ─────────────────────────────────────────────────────
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("category", sa.String(30), nullable=False, server_default="autre"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("phone2", sa.String(30), nullable=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("siret", sa.String(20), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_favorite", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_contacts_last_name", "contacts", ["last_name"])

    # ── 2. Table automation_rules ─────────────────────────────────────────────
    op.create_table(
        "automation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("trigger_days", sa.Integer, nullable=False, server_default="5"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(300), nullable=True),
        sa.Column("body_template", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("filter_config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── 3. Table communication_logs ───────────────────────────────────────────
    op.create_table(
        "communication_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("automation_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leases.id", ondelete="CASCADE"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(300), nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_comm_logs_tenant", "communication_logs", ["tenant_id"])

    # ── 4. Table document_templates ───────────────────────────────────────────
    op.create_table(
        "document_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("template_type", sa.String(30), nullable=False),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("header_color", sa.String(20), nullable=True, server_default="'#1E3A5F'"),
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("company_address", sa.String(300), nullable=True),
        sa.Column("company_phone", sa.String(30), nullable=True),
        sa.Column("company_email", sa.String(255), nullable=True),
        sa.Column("company_siret", sa.String(20), nullable=True),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("footer_text", sa.Text, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_doc_templates_type", "document_templates", ["template_type"])

    # updated_at géré par SQLAlchemy onupdate — pas de trigger DB nécessaire


def downgrade() -> None:
    for table in ["contacts", "automation_rules", "communication_logs", "document_templates"]:
        op.drop_table(table)
