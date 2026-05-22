"""
Tests API — Tickets (communication locataire ↔ gestionnaire).
"""
import pytest
from tests.conftest import auth


async def _create_tenant_for_locataire(db, locataire_user):
    from app.models.tenant import Tenant
    tenant = Tenant(
        first_name="Jean",
        last_name="Locataire",
        email=f"jean.ticket@test.fr",
        user_id=locataire_user.id,
    )
    db.add(tenant)
    await db.flush()
    return tenant


@pytest.mark.asyncio
class TestTicketCreate:
    async def test_locataire_creates_ticket(self, client, locataire_token, locataire_user, db):
        await _create_tenant_for_locataire(db, locataire_user)
        resp = await client.post("/api/v1/tickets", headers=auth(locataire_token), json={
            "title": "Fuite d'eau",
            "description": "Il y a une fuite sous l'évier.",
            "category": "incident",
            "priority": "high",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "open"

    async def test_create_ticket_without_tenant_fails(self, client, locataire_token):
        resp = await client.post("/api/v1/tickets", headers=auth(locataire_token), json={
            "title": "Test",
            "description": "Test desc",
        })
        assert resp.status_code == 400

    async def test_unauthenticated_cannot_create(self, client):
        resp = await client.post("/api/v1/tickets", json={
            "title": "Hack", "description": "Hack desc",
        })
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestTicketList:
    async def test_gestionnaire_lists_all_tickets(self, client, gestionnaire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        db.add(Ticket(
            title="Problème chauffage", description="Chauffage en panne.",
            tenant_id=tenant.id, status=TicketStatus.OPEN,
        ))
        await db.flush()

        resp = await client.get("/api/v1/tickets", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_gestionnaire_filters_by_status(self, client, gestionnaire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        db.add(Ticket(title="Ouvert", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN))
        db.add(Ticket(title="Résolu", description="D", tenant_id=tenant.id, status=TicketStatus.RESOLVED))
        await db.flush()

        resp = await client.get("/api/v1/tickets?status=open", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(t["status"] == "open" for t in items)

    async def test_locataire_cannot_list_all(self, client, locataire_token):
        resp = await client.get("/api/v1/tickets", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_locataire_sees_own_tickets(self, client, locataire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        db.add(Ticket(title="Mon ticket", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN))
        await db.flush()

        resp = await client.get("/api/v1/tickets/mine", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


@pytest.mark.asyncio
class TestTicketStats:
    async def test_gestionnaire_gets_stats(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/tickets/stats", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert "open" in resp.json()

    async def test_locataire_cannot_get_stats(self, client, locataire_token):
        resp = await client.get("/api/v1/tickets/stats", headers=auth(locataire_token))
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestTicketDetail:
    async def test_get_ticket_detail(self, client, gestionnaire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        ticket = Ticket(title="Détail", description="Contenu", tenant_id=tenant.id, status=TicketStatus.OPEN)
        db.add(ticket)
        await db.flush()

        resp = await client.get(f"/api/v1/tickets/{ticket.id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Détail"
        assert "messages" in data


@pytest.mark.asyncio
class TestTicketUpdate:
    async def test_gestionnaire_updates_status(self, client, gestionnaire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        ticket = Ticket(title="Status", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN)
        db.add(ticket)
        await db.flush()

        resp = await client.patch(
            f"/api/v1/tickets/{ticket.id}",
            headers=auth(gestionnaire_token),
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_locataire_cannot_update_status(self, client, locataire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        ticket = Ticket(title="T", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN)
        db.add(ticket)
        await db.flush()

        resp = await client.patch(
            f"/api/v1/tickets/{ticket.id}",
            headers=auth(locataire_token),
            json={"status": "resolved"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestTicketMessages:
    async def test_gestionnaire_adds_reply(self, client, gestionnaire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        ticket = Ticket(title="Msg", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN)
        db.add(ticket)
        await db.flush()

        resp = await client.post(
            f"/api/v1/tickets/{ticket.id}/messages",
            headers=auth(gestionnaire_token),
            json={"content": "Nous avons bien pris note.", "is_internal": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Nous avons bien pris note."
        assert data["is_internal"] is False

    async def test_locataire_adds_message(self, client, locataire_token, locataire_user, db):
        tenant = await _create_tenant_for_locataire(db, locataire_user)
        from app.models.ticket import Ticket, TicketStatus
        ticket = Ticket(title="Réponse", description="D", tenant_id=tenant.id, status=TicketStatus.OPEN)
        db.add(ticket)
        await db.flush()

        resp = await client.post(
            f"/api/v1/tickets/{ticket.id}/messages",
            headers=auth(locataire_token),
            json={"content": "Merci pour votre réponse.", "is_internal": False},
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "Merci pour votre réponse."
