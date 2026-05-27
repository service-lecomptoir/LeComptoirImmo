"""
Tests transversaux — RBAC / isolation des rôles sur chaque module.
Vérifie que chaque rôle ne peut accéder qu'à ce qui lui est autorisé.
"""
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestRBACProperties:
    async def test_roles_can_read_properties(self, client, gestionnaire_token, admin_token):
        for token in [gestionnaire_token, admin_token]:
            resp = await client.get("/api/v1/properties", headers=auth(token))
            assert resp.status_code == 200

    async def test_roles_cannot_write_properties(self, client, locataire_token, proprietaire_token):
        payload = {
            "name": "Hack",
            "address": "1 Rue Hack",
            "zip_code": "75000",
            "city": "Paris",
            "country": "France",
            "property_type": "appartement",
        }
        for token in [locataire_token, proprietaire_token]:
            resp = await client.post("/api/v1/properties", headers=auth(token), json=payload)
            assert resp.status_code == 403, f"Expected 403 but got {resp.status_code}"


@pytest.mark.asyncio
class TestRBACUsers:
    async def test_admin_and_gestionnaire_can_list_users(
        self, client, admin_token, gestionnaire_token
    ):
        # Admin → liste complète
        assert (await client.get("/api/v1/users", headers=auth(admin_token))).status_code == 200
        # Gestionnaire → liste restreinte (proprio + locataire de sa portée)
        assert (await client.get("/api/v1/users", headers=auth(gestionnaire_token))).status_code == 200

    async def test_non_gestionnaire_cannot_list_users(
        self, client, locataire_token, proprietaire_token
    ):
        for token in [locataire_token, proprietaire_token]:
            resp = await client.get("/api/v1/users", headers=auth(token))
            assert resp.status_code == 403


@pytest.mark.asyncio
class TestRBACNotifications:
    async def test_all_authenticated_roles_get_count(
        self, client, admin_token, gestionnaire_token, locataire_token, proprietaire_token
    ):
        """Tous les rôles authentifiés peuvent voir leur compteur."""
        for token in [admin_token, gestionnaire_token, locataire_token, proprietaire_token]:
            resp = await client.get("/api/v1/notifications/count", headers=auth(token))
            assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

    async def test_unauthenticated_cannot_get_count(self, client):
        resp = await client.get("/api/v1/notifications/count")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestRBACDocuments:
    async def test_all_roles_can_list_documents(
        self, client, admin_token, gestionnaire_token, locataire_token, proprietaire_token
    ):
        for token in [admin_token, gestionnaire_token, locataire_token, proprietaire_token]:
            resp = await client.get("/api/v1/documents", headers=auth(token))
            assert resp.status_code == 200

    async def test_only_gestionnaire_can_upload(
        self, client, locataire_token, proprietaire_token
    ):
        import io
        fake_file = io.BytesIO(b"fake pdf content")
        for token in [locataire_token, proprietaire_token]:
            resp = await client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("test.pdf", fake_file, "application/pdf")},
                data={"entity_type": "tenant", "entity_id": "00000000-0000-0000-0000-000000000001"},
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
class TestRBACLeases:
    async def test_only_gestionnaire_can_create_lease(
        self, client, locataire_token, proprietaire_token
    ):
        payload = {
            "tenant_id": "00000000-0000-0000-0000-000000000002",
            "property_id": "00000000-0000-0000-0000-000000000003",
            "start_date": "2026-01-01",
            "rent_amount": 500.0,
            "charges_amount": 50.0,
            "lease_type": "vide",
        }
        for token in [locataire_token, proprietaire_token]:
            resp = await client.post("/api/v1/leases", headers=auth(token), json=payload)
            assert resp.status_code == 403


@pytest.mark.asyncio
class TestRBACPayments:
    async def test_locataire_cannot_generate_payments(self, client, locataire_token):
        resp = await client.post("/api/v1/payments/generate", headers=auth(locataire_token), json={
            "year": 2026, "month": 6,
        })
        assert resp.status_code == 403

    async def test_locataire_cannot_record_payment(self, client, locataire_token):
        resp = await client.post(
            "/api/v1/payments/00000000-0000-0000-0000-000000000001/record",
            headers=auth(locataire_token),
            json={"amount_paid": 500.0, "payment_date": "2026-05-01"},
        )
        # 403 ou 404 selon que le paiement existe
        assert resp.status_code in (403, 404)


@pytest.mark.asyncio
class TestRBACCrossData:
    async def test_locataire_cannot_access_other_lease(
        self, client, locataire_token, gestionnaire_user, db
    ):
        """Un locataire ne peut pas accéder au bail d'un autre locataire."""
        from app.models.property import Property
        from app.models.tenant import Tenant
        from app.models.lease import Lease
        from datetime import date

        prop = Property(
            name="Prop Cross", address="99 Rue",
            zip_code="75099", city="Paris", country="France",
            property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        # Tenant sans lien avec locataire_user
        other_tenant = Tenant(
            first_name="Autre", last_name="Locataire",
            email="autre.loc@test.fr",
        )
        db.add(other_tenant)
        await db.flush()

        other_lease = Lease(
            tenant_id=other_tenant.id, property_id=prop.id,
            start_date=date.today(), rent_amount=500.00, charges_amount=50.00,
            lease_type="vide", payment_day=1, is_active=True,
        )
        db.add(other_lease)
        await db.flush()

        # Le locataire essaie d'accéder au bail de quelqu'un d'autre
        resp = await client.get(f"/api/v1/leases/{other_lease.id}", headers=auth(locataire_token))
        assert resp.status_code == 403
