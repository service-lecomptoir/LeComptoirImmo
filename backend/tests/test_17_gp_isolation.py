"""
Tests isolation données — gestionnaire_proprio vs gestionnaire (mandataire).

Vérifie que :
  - Un GP ne voit que ses propriétés, locataires, baux, paiements, tickets
  - Un mandataire ne voit pas les données d'un GP et vice versa
  - Un admin voit tout

Note : les endpoints /properties/{id}, /tenants/{id} etc. n'ont pas de contrôle
d'accès par ID — l'isolation est assurée au niveau des listes uniquement.
"""
import pytest
from datetime import date
from tests.conftest import auth


# ── Helpers de création de données ────────────────────────────────────────────

async def _get_user_id(client, token):
    """Retourne l'ID de l'utilisateur courant."""
    me = await client.get("/api/v1/users/me", headers=auth(token))
    assert me.status_code == 200, me.text
    return me.json()["id"]


async def _create_full_chain(client, token):
    """Crée propriété → unité → locataire → bail. Retourne les IDs.

    Pour GESTIONNAIRE_PROPRIO, on passe owner_user_id pour que les
    endpoints de liste (qui filtrent par owner_user_id) fonctionnent.
    """
    user_id = await _get_user_id(client, token)

    prop = await client.post("/api/v1/properties", headers=auth(token), json={
        "name": f"Prop-{token[:8]}",
        "address": "1 Rue Test",
        "zip_code": "75001",
        "city": "Paris",
        "country": "France",
        "property_type": "immeuble",
        "owner_user_id": user_id,
    })
    assert prop.status_code == 201, prop.text
    prop_id = prop.json()["id"]

    unit = await client.post("/api/v1/units", headers=auth(token), json={
        "property_id": prop_id,
        "unit_ref": "A1",
        "unit_type": "T2",
        "base_rent": 800.0,
        "charges_amount": 80.0,
    })
    assert unit.status_code == 201, unit.text
    unit_id = unit.json()["id"]

    tenant = await client.post("/api/v1/tenants", headers=auth(token), json={
        "first_name": "Test",
        "last_name": f"Locataire-{token[:8]}",
        "email": f"loc-{token[:8]}@test.fr",
    })
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]

    lease = await client.post("/api/v1/leases", headers=auth(token), json={
        "unit_id": unit_id,
        "tenant_id": tenant_id,
        "property_id": prop_id,
        "start_date": "2026-01-01",
        "rent_amount": 800.0,
        "charges_amount": 80.0,
        "lease_type": "vide",
    })
    assert lease.status_code == 201, lease.text

    return {
        "prop_id": prop_id,
        "unit_id": unit_id,
        "tenant_id": tenant_id,
        "lease_id": lease.json()["id"],
    }


# ── Tests isolation propriétés ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGPPropertyIsolation:
    async def test_gp_only_sees_own_properties(self, client, gp_token, gp_token2):
        ids1 = await _create_full_chain(client, gp_token)
        ids2 = await _create_full_chain(client, gp_token2)

        resp1 = await client.get("/api/v1/properties", headers=auth(gp_token))
        assert resp1.status_code == 200
        prop_ids_1 = {p["id"] for p in resp1.json()["items"]}
        assert ids1["prop_id"] in prop_ids_1
        assert ids2["prop_id"] not in prop_ids_1

        resp2 = await client.get("/api/v1/properties", headers=auth(gp_token2))
        assert resp2.status_code == 200
        prop_ids_2 = {p["id"] for p in resp2.json()["items"]}
        assert ids2["prop_id"] in prop_ids_2
        assert ids1["prop_id"] not in prop_ids_2

    async def test_mandataire_list_excludes_gp_properties(self, client, gp_token, gestionnaire_token):
        gp_ids = await _create_full_chain(client, gp_token)
        resp = await client.get("/api/v1/properties", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        prop_ids = {p["id"] for p in resp.json()["items"]}
        assert gp_ids["prop_id"] not in prop_ids

    async def test_admin_sees_all_properties(self, client, admin_token, gp_token, gestionnaire_token):
        gp_ids = await _create_full_chain(client, gp_token)
        mand_ids = await _create_full_chain(client, gestionnaire_token)
        resp = await client.get("/api/v1/properties", headers=auth(admin_token))
        assert resp.status_code == 200
        all_ids = {p["id"] for p in resp.json()["items"]}
        assert gp_ids["prop_id"] in all_ids
        assert mand_ids["prop_id"] in all_ids


# ── Tests isolation locataires ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGPTenantIsolation:
    async def test_gp_only_sees_own_tenants(self, client, gp_token, gp_token2):
        ids1 = await _create_full_chain(client, gp_token)
        ids2 = await _create_full_chain(client, gp_token2)

        resp1 = await client.get("/api/v1/tenants", headers=auth(gp_token))
        assert resp1.status_code == 200
        tenant_ids_1 = {t["id"] for t in resp1.json()["items"]}
        assert ids1["tenant_id"] in tenant_ids_1
        assert ids2["tenant_id"] not in tenant_ids_1

    async def test_mandataire_list_excludes_gp_tenants(self, client, gp_token, gestionnaire_token):
        gp_ids = await _create_full_chain(client, gp_token)
        resp = await client.get("/api/v1/tenants", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        tenant_ids = {t["id"] for t in resp.json()["items"]}
        assert gp_ids["tenant_id"] not in tenant_ids


# ── Tests isolation baux ───────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGPLeaseIsolation:
    async def test_gp_only_sees_own_leases(self, client, gp_token, gp_token2):
        ids1 = await _create_full_chain(client, gp_token)
        ids2 = await _create_full_chain(client, gp_token2)

        resp = await client.get("/api/v1/leases", headers=auth(gp_token))
        assert resp.status_code == 200
        lease_ids = {le["id"] for le in resp.json()["items"]}
        assert ids1["lease_id"] in lease_ids
        assert ids2["lease_id"] not in lease_ids

    async def test_mandataire_list_excludes_gp_leases(self, client, gp_token, gestionnaire_token):
        gp_ids = await _create_full_chain(client, gp_token)
        resp = await client.get("/api/v1/leases", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        lease_ids = {le["id"] for le in resp.json()["items"]}
        assert gp_ids["lease_id"] not in lease_ids


# ── Tests isolation paiements ──────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGPPaymentIsolation:
    async def test_gp_generates_payments_only_for_own_leases(self, client, gp_token, gp_token2):
        await _create_full_chain(client, gp_token)
        await _create_full_chain(client, gp_token2)

        gen = await client.post("/api/v1/payments/generate", headers=auth(gp_token), json={
            "year": 2026, "month": 6,
        })
        assert gen.status_code in (200, 201)

        # GP1 voit ses paiements (au moins 1 généré)
        resp1 = await client.get("/api/v1/payments", headers=auth(gp_token))
        assert resp1.status_code == 200
        assert len(resp1.json()["items"]) >= 1

        # GP2 génère aussi ses paiements et voit uniquement les siens
        gen2 = await client.post("/api/v1/payments/generate", headers=auth(gp_token2), json={
            "year": 2026, "month": 6,
        })
        assert gen2.status_code in (200, 201)
        resp2 = await client.get("/api/v1/payments", headers=auth(gp_token2))
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) >= 1

        # Les paiements sont distincts
        ids1 = {p["id"] for p in resp1.json()["items"]}
        ids2 = {p["id"] for p in resp2.json()["items"]}
        assert ids1.isdisjoint(ids2)

    async def test_mandataire_list_excludes_gp_payments(self, client, gp_token, gestionnaire_token):
        gp_ids = await _create_full_chain(client, gp_token)

        await client.post("/api/v1/payments/generate", headers=auth(gp_token), json={
            "year": 2026, "month": 7,
        })
        resp = await client.get("/api/v1/payments", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        lease_ids_in_payments = {p.get("lease_id") for p in resp.json()["items"]}
        assert gp_ids["lease_id"] not in lease_ids_in_payments


# ── Tests isolation tickets ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGPTicketIsolation:
    async def test_gp_can_list_tickets(self, client, gp_token):
        """GP peut lister ses tickets (liste filtrée à son périmètre)."""
        resp = await client.get("/api/v1/tickets", headers=auth(gp_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_mandataire_can_list_tickets(self, client, gestionnaire_token):
        """Mandataire peut lister les tickets (hors périmètre GP)."""
        resp = await client.get("/api/v1/tickets", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_gp_and_mandataire_ticket_lists_are_disjoint(
        self, client, gp_token, gestionnaire_token
    ):
        """Les tickets GP et mandataire ne se croisent pas dans leurs listes."""
        resp_gp = await client.get("/api/v1/tickets", headers=auth(gp_token))
        resp_mand = await client.get("/api/v1/tickets", headers=auth(gestionnaire_token))
        assert resp_gp.status_code == 200
        assert resp_mand.status_code == 200

        gp_ticket_ids = {t["id"] for t in resp_gp.json()["items"]}
        mand_ticket_ids = {t["id"] for t in resp_mand.json()["items"]}
        # Leurs listes ne doivent pas se croiser
        assert gp_ticket_ids.isdisjoint(mand_ticket_ids)
