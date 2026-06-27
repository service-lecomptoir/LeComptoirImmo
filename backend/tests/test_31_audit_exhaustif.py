"""Audit EXHAUSTIF (db.create / db.update / db.delete) via les écouteurs SQLAlchemy.

Vérifie que toute écriture ORM produit une ligne d'audit, que le diff des champs
est capturé en modification, et que l'acteur (utilisateur) est estampillé quand
l'écriture passe par une requête authentifiée.
"""

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.property import Property
from tests.conftest import auth


@pytest.mark.asyncio
class TestAuditExhaustif:
    async def test_orm_create_update_delete_are_audited(self, db, gestionnaire_user):
        prop = Property(
            name="Audit Test",
            address="1 rue de l'Audit",
            zip_code="75001",
            city="Paris",
            country="France",
            property_type="appartement",
            created_by=gestionnaire_user.id,
        )
        db.add(prop)
        await db.commit()
        created = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "db.create",
                        AuditLog.entity_type == "properties",
                        AuditLog.entity_id == prop.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(created) >= 1

        prop.name = "Audit Test (modifié)"
        await db.commit()
        updated = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "db.update",
                        AuditLog.entity_id == prop.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert updated
        changes = (updated[-1].details or {}).get("changes", {})
        assert "name" in changes
        assert changes["name"]["new"] == "Audit Test (modifié)"

        pid = prop.id
        await db.delete(prop)
        await db.commit()
        deleted = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "db.delete",
                        AuditLog.entity_id == pid,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert deleted

    async def test_actor_is_captured_via_api(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        """Écriture via une requête authentifiée : l'audit porte l'utilisateur."""
        from datetime import date

        from tests.test_06_leases import _setup_lease_chain

        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post(
            "/api/v1/leases",
            headers=auth(gestionnaire_token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(date(2026, 1, 1)),
                "rent_amount": 800.00,
                "charges_amount": 100.00,
                "lease_type": "vide",
                "payment_method": "virement",
                "payment_day": 5,
            },
        )
        assert resp.status_code == 201, resp.text
        rows = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "db.create",
                        AuditLog.entity_type == "leases",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert rows
        assert any(r.user_email == gestionnaire_user.email for r in rows)

    async def test_secret_columns_are_not_logged(self, db, gestionnaire_user):
        """Les colonnes sensibles (mot de passe…) ne fuitent pas dans l'audit."""
        created = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "db.create",
                        AuditLog.entity_type == "users",
                        AuditLog.entity_id == gestionnaire_user.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        # Le compte de test est créé en fixture ; si une ligne d'audit existe, elle
        # ne doit jamais contenir le hash du mot de passe en clair.
        for row in created:
            snap = (row.details or {}).get("snapshot", {})
            assert snap.get("hashed_password", "***") == "***"
