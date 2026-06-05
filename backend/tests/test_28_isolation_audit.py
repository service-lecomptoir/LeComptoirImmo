# -*- coding: utf-8 -*-
"""Audit d'isolation cross-comptes — un GP ne doit JAMAIS accéder aux ressources
d'un autre GP (par ID), et un locataire jamais à la démarche d'un autre.

On crée deux portefeuilles GP indépendants (A et B) et on vérifie que B reçoit
403/404 sur chaque accès par ID aux ressources de A (et réciproquement implicite).
"""
import uuid
import pytest
from tests.conftest import auth


async def _chain(client, token):
    """Crée property + tenant + lease + payment + inspection pour un GP, renvoie les ids."""
    prop = await client.post("/api/v1/properties", headers=auth(token), json={
        "name": "Bien Iso", "address": "1 Rue Iso", "zip_code": "75000",
        "city": "Paris", "country": "France", "property_type": "appartement",
    })
    assert prop.status_code == 201, prop.text
    prop_id = prop.json()["id"]
    tenant = await client.post("/api/v1/tenants", headers=auth(token), json={
        "first_name": "Iso", "last_name": "Test", "email": f"iso_{uuid.uuid4().hex[:6]}@t.fr",
        "monthly_income": 3000,
    })
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]
    lease = await client.post("/api/v1/leases", headers=auth(token), json={
        "tenant_id": tenant_id, "property_id": prop_id, "start_date": "2026-01-01",
        "rent_amount": 800.0, "charges_amount": 50.0, "lease_type": "vide",
    })
    assert lease.status_code == 201, lease.text
    lease_id = lease.json()["id"]
    pay = await client.post("/api/v1/payments", headers=auth(token), json={
        "lease_id": lease_id, "period_year": 2026, "period_month": 1,
    })
    assert pay.status_code in (200, 201), pay.text
    payment_id = pay.json()["id"]
    insp = await client.post("/api/v1/inspections", headers=auth(token), json={
        "lease_id": lease_id, "property_id": prop_id,
        "inspection_type": "entree", "inspection_date": "2026-01-02",
    })
    assert insp.status_code == 201, insp.text
    inspection_id = insp.json()["id"]
    return {
        "prop_id": prop_id, "tenant_id": tenant_id, "lease_id": lease_id,
        "payment_id": payment_id, "inspection_id": inspection_id,
    }


def _denied(resp) -> bool:
    return resp.status_code in (403, 404)


@pytest.mark.asyncio
class TestCrossGPIsolation:
    async def test_gp_cannot_touch_other_gp_resources(self, client, gp_token, gp_token2):
        a = await _chain(client, gp_token)      # portefeuille du GP A
        hb = auth(gp_token2)                      # GP B (attaquant)

        # ── Baux ──
        assert _denied(await client.get(f"/api/v1/leases/{a['lease_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/leases/{a['lease_id']}/pdf", headers=hb))
        assert _denied(await client.put(f"/api/v1/leases/{a['lease_id']}", headers=hb,
                                        json={"rent_amount": 1.0}))
        assert _denied(await client.post(f"/api/v1/leases/{a['lease_id']}/terminate", headers=hb,
                                         json={"end_date": "2026-12-31", "reason": "x"}))
        assert _denied(await client.delete(f"/api/v1/leases/{a['lease_id']}", headers=hb))

        # ── Locataire (fiche + documents) ──
        assert _denied(await client.get(f"/api/v1/tenants/{a['tenant_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/tenants/{a['tenant_id']}/documents", headers=hb))

        # ── Propriété ──
        assert _denied(await client.get(f"/api/v1/properties/{a['prop_id']}", headers=hb))

        # ── Inspections / états des lieux ──
        assert _denied(await client.get(f"/api/v1/inspections/{a['inspection_id']}", headers=hb))
        assert _denied(await client.put(f"/api/v1/inspections/{a['inspection_id']}", headers=hb,
                                        json={"notes": "hack"}))
        assert _denied(await client.delete(f"/api/v1/inspections/{a['inspection_id']}", headers=hb))

        # ── Paiements ──
        assert _denied(await client.get(f"/api/v1/payments/{a['payment_id']}", headers=hb))

        # ── Actualisation (révision / charges / taxes) ──
        assert _denied(await client.patch(f"/api/v1/actualisation/loyers/{a['lease_id']}/reference",
                                          headers=hb, json={"irl_quarter": 1, "irl_base_index": 130.0}))
        assert _denied(await client.post(f"/api/v1/actualisation/charges/{a['lease_id']}/preview",
                                         headers=hb, json={"period_start": "2026-01-01",
                                                           "period_end": "2026-12-31", "real_total": 100.0}))
        assert _denied(await client.get(f"/api/v1/actualisation/loyers/{a['lease_id']}/revision-pdf", headers=hb))
        assert _denied(await client.post("/api/v1/actualisation/taxes/pdf", headers=hb,
                                         json={"lease_id": a["lease_id"], "year": 2026, "teom_amount": 100.0}))

        # ── Lettres / CAF ──
        assert _denied(await client.get(f"/api/v1/letters/relance/{a['payment_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/letters/attestation-caf/{a['lease_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/letters/versement-direct/{a['lease_id']}", headers=hb))

        # ── Contrôle positif : le GP A accède bien à SES ressources ──
        own = auth(gp_token)
        assert (await client.get(f"/api/v1/leases/{a['lease_id']}", headers=own)).status_code == 200
        assert (await client.get(f"/api/v1/tenants/{a['tenant_id']}", headers=own)).status_code == 200
        assert (await client.get(f"/api/v1/inspections/{a['inspection_id']}", headers=own)).status_code == 200


@pytest.mark.asyncio
class TestTicketIsolation:
    async def test_locataire_cannot_read_others_ticket(self, client, db, gp_token, gp_user, locataire_user):
        # Démarche rattachée à un locataire du GP
        a = await _chain(client, gp_token)
        from app.models.ticket import Ticket, TicketStatus, TicketCategory, TicketPriority
        t = Ticket(title="Privé", description="confidentiel", category=TicketCategory.AUTRE.value,
                   priority=TicketPriority.MEDIUM.value, tenant_id=uuid.UUID(a["tenant_id"]),
                   status=TicketStatus.OPEN)
        db.add(t)
        await db.flush()

        # Un autre locataire (non rattaché) ne doit pas lire/agir sur ce ticket
        from tests.conftest import _get_token
        # locataire_user n'est pas le tenant de ce ticket
        # (le tenant créé n'a pas de user_id)
        r = await client.post("/api/v1/auth/login",
                              json={"email": locataire_user.email, "password": "LocPass1!"})
        loc_token = r.json()["access_token"]
        assert _denied(await client.get(f"/api/v1/tickets/{t.id}", headers=auth(loc_token)))
        assert _denied(await client.post(f"/api/v1/tickets/{t.id}/messages", headers=auth(loc_token),
                                         json={"content": "intrusion"}))

    async def test_gp_cannot_touch_other_gp_ticket(self, client, db, gp_token, gp_token2):
        a = await _chain(client, gp_token)
        from app.models.ticket import Ticket, TicketStatus, TicketCategory, TicketPriority
        t = Ticket(title="GP-A", description="x", category=TicketCategory.AUTRE.value,
                   priority=TicketPriority.MEDIUM.value, tenant_id=uuid.UUID(a["tenant_id"]),
                   status=TicketStatus.OPEN)
        db.add(t)
        await db.flush()
        hb = auth(gp_token2)
        assert _denied(await client.get(f"/api/v1/tickets/{t.id}", headers=hb))
        assert _denied(await client.patch(f"/api/v1/tickets/{t.id}", headers=hb, json={"status": "closed"}))
        assert _denied(await client.post(f"/api/v1/tickets/{t.id}/propose-closure", headers=hb))
