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
class TestCrossAgencyIsolation:
    """Deux agences mandataires indépendantes ne se voient pas (multi-tenant)."""

    async def test_two_mandataire_agencies_isolated(self, client, db, gestionnaire_token):
        from tests.conftest import _create_user, _get_token
        a = await _chain(client, gestionnaire_token)  # agence A

        emailB = f"gestB_{uuid.uuid4().hex[:8]}@test.fr"
        await _create_user(db, emailB, "GestPass1!", "gestionnaire")  # principal agence B
        tokenB = await _get_token(client, emailB, "GestPass1!")
        hb = auth(tokenB)

        # Accès par ID : B ne voit RIEN de A
        assert _denied(await client.get(f"/api/v1/leases/{a['lease_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/tenants/{a['tenant_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/properties/{a['prop_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/payments/{a['payment_id']}", headers=hb))
        assert _denied(await client.get(f"/api/v1/inspections/{a['inspection_id']}", headers=hb))

        # Listes : aucune ressource de A visible pour B
        leases_b = await client.get("/api/v1/leases", headers=hb)
        assert leases_b.status_code == 200
        assert a["lease_id"] not in [i["id"] for i in leases_b.json()["items"]]
        props_b = await client.get("/api/v1/properties", headers=hb)
        assert a["prop_id"] not in [i["id"] for i in props_b.json()["items"]]
        tenants_b = await client.get("/api/v1/tenants", headers=hb)
        assert a["tenant_id"] not in [i["id"] for i in tenants_b.json()["items"]]

        # Contrôle positif : A voit bien SES ressources en liste
        leases_a = await client.get("/api/v1/leases", headers=auth(gestionnaire_token))
        assert a["lease_id"] in [i["id"] for i in leases_a.json()["items"]]

    async def test_subaccount_sees_agency_resources(self, client, db, gestionnaire_user, gestionnaire_token):
        from tests.conftest import _create_user, _get_token
        a = await _chain(client, gestionnaire_token)  # créé par le principal A

        # Sous-compte de l'agence A (created_by = principal, agency = principal)
        emailS = f"staffA_{uuid.uuid4().hex[:8]}@test.fr"
        sub = await _create_user(db, emailS, "GestPass1!", "gestionnaire")
        sub.created_by = gestionnaire_user.id
        sub.agency_id = gestionnaire_user.id
        await db.flush()
        tokenS = await _get_token(client, emailS, "GestPass1!")

        # Le sous-compte voit les ressources de SON agence
        leases_s = await client.get("/api/v1/leases", headers=auth(tokenS))
        assert leases_s.status_code == 200
        assert a["lease_id"] in [i["id"] for i in leases_s.json()["items"]]
        assert (await client.get(f"/api/v1/leases/{a['lease_id']}", headers=auth(tokenS))).status_code == 200


async def _owned_chain(db, *, gest_id, owner_user_id, tenant_user_id, tag):
    """Chaîne complète (bien→locataire→bail→paiement→avis→démarche) créée par une
    agence (gest_id), rattachée à un propriétaire (owner_user_id) et un locataire
    (tenant_user_id). Insertion directe en base."""
    from datetime import date
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.lease import Lease
    from app.models.payment import Payment
    from app.models.avis_echeance import AvisEcheance
    from app.models.ticket import Ticket, TicketStatus, TicketCategory, TicketPriority

    prop = Property(name=f"Bien {tag}", address="1 Rue", zip_code="75000", city="Paris",
                    country="France", property_type="appartement",
                    created_by=gest_id, owner_user_id=owner_user_id)
    db.add(prop)
    await db.flush()
    tenant = Tenant(first_name=tag, last_name="Iso", email=f"{tag.lower()}_{uuid.uuid4().hex[:6]}@t.fr",
                    created_by=gest_id, user_id=tenant_user_id)
    db.add(tenant)
    await db.flush()
    lease = Lease(tenant_id=tenant.id, property_id=prop.id, start_date=date.today(),
                  rent_amount=800.0, charges_amount=50.0, lease_type="vide", payment_day=1,
                  is_active=True, created_by=gest_id)
    db.add(lease)
    await db.flush()
    pay = Payment(lease_id=lease.id, tenant_id=tenant.id, period_year=2026, period_month=1,
                  due_date=date(2026, 1, 1), amount_rent=800.0, amount_charges=50.0,
                  amount_due=850.0, amount_paid=0.0, status="pending", created_by=gest_id)
    db.add(pay)
    avis = AvisEcheance(lease_id=lease.id, tenant_id=tenant.id, period_year=2026, period_month=1,
                        due_date=date(2026, 1, 1), amount_rent=800.0, amount_charges=50.0,
                        amount_total=850.0, status="envoye")
    db.add(avis)
    ticket = Ticket(title=f"Démarche {tag}", description="d", tenant_id=tenant.id,
                    category=TicketCategory.AUTRE.value, priority=TicketPriority.MEDIUM.value,
                    status=TicketStatus.OPEN)
    db.add(ticket)
    await db.flush()
    return {"prop": str(prop.id), "tenant": str(tenant.id), "lease": str(lease.id),
            "payment": str(pay.id), "avis": str(avis.id), "ticket": str(ticket.id)}


def _ids(resp, key="items"):
    data = resp.json()
    items = data.get(key, data) if isinstance(data, dict) else data
    return [str(i.get("id")) for i in items]


@pytest.mark.asyncio
class TestProprietaireIsolation:
    """Un propriétaire (lecture seule) ne voit QUE les données de SES biens."""

    async def test_proprietaire_sees_only_own(self, client, db, gestionnaire_user,
                                              proprietaire_user, proprietaire_token, locataire_user):
        from tests.conftest import _create_user
        # Bien du propriétaire A (= proprietaire_user)
        a = await _owned_chain(db, gest_id=gestionnaire_user.id,
                               owner_user_id=proprietaire_user.id,
                               tenant_user_id=locataire_user.id, tag="ProA")
        # Bien d'un AUTRE propriétaire B
        ownerB = await _create_user(db, f"propB_{uuid.uuid4().hex[:8]}@t.fr", "PropPass1!", "proprietaire")
        b = await _owned_chain(db, gest_id=gestionnaire_user.id,
                               owner_user_id=ownerB.id, tenant_user_id=None, tag="ProB")
        await db.flush()
        h = auth(proprietaire_token)

        # Listes : A ne voit que ses biens/baux/paiements
        props = await client.get("/api/v1/properties", headers=h)
        assert props.status_code == 200
        assert a["prop"] in _ids(props) and b["prop"] not in _ids(props)

        leases = await client.get("/api/v1/leases", headers=h)
        assert a["lease"] in _ids(leases) and b["lease"] not in _ids(leases)

        pays = await client.get("/api/v1/payments", headers=h)
        assert a["payment"] in _ids(pays) and b["payment"] not in _ids(pays)

        # Accès par ID au bien d'un autre propriétaire → refusé
        assert _denied(await client.get(f"/api/v1/leases/{b['lease']}", headers=h))
        assert _denied(await client.get(f"/api/v1/payments/{b['payment']}", headers=h))

        # Écriture interdite (rôle non gestionnaire)
        assert _denied(await client.put(f"/api/v1/leases/{a['lease']}", headers=h, json={"rent_amount": 1.0}))


@pytest.mark.asyncio
class TestLocataireIsolation:
    """Un locataire ne voit QUE son bail / ses paiements / ses avis / ses démarches."""

    async def test_locataire_sees_only_own(self, client, db, gestionnaire_user,
                                           proprietaire_user, locataire_user, locataire_token):
        from tests.conftest import _create_user, _get_token
        a = await _owned_chain(db, gest_id=gestionnaire_user.id,
                               owner_user_id=proprietaire_user.id,
                               tenant_user_id=locataire_user.id, tag="LocA")
        # Bail d'un AUTRE locataire B
        locB = await _create_user(db, f"locB_{uuid.uuid4().hex[:8]}@t.fr", "LocPass1!", "locataire")
        b = await _owned_chain(db, gest_id=gestionnaire_user.id,
                               owner_user_id=proprietaire_user.id, tenant_user_id=locB.id, tag="LocB")
        await db.flush()
        h = auth(locataire_token)

        # Listes : uniquement SES données
        leases = await client.get("/api/v1/leases", headers=h)
        assert leases.status_code == 200
        assert a["lease"] in _ids(leases) and b["lease"] not in _ids(leases)

        pays = await client.get("/api/v1/payments", headers=h)
        assert a["payment"] in _ids(pays) and b["payment"] not in _ids(pays)

        avis = await client.get("/api/v1/avis-echeances", headers=h)
        avis_ids = [str(i.get("id")) for i in avis.json()]
        assert a["avis"] in avis_ids and b["avis"] not in avis_ids

        mine = await client.get("/api/v1/tickets/mine", headers=h)
        assert a["ticket"] in _ids(mine, key=None) and b["ticket"] not in _ids(mine, key=None)

        # Accès par ID aux ressources d'un autre locataire → refusé
        assert _denied(await client.get(f"/api/v1/leases/{b['lease']}", headers=h))
        assert _denied(await client.get(f"/api/v1/payments/{b['payment']}", headers=h))
        assert _denied(await client.get(f"/api/v1/tickets/{b['ticket']}", headers=h))

        # Endpoints de gestion interdits au locataire
        assert _denied(await client.get("/api/v1/tenants", headers=h))
        assert _denied(await client.get("/api/v1/properties", headers=h))
        assert _denied(await client.get("/api/v1/tickets", headers=h))


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
