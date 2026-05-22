"""
Tests API — Notifications.
"""
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestNotificationCount:
    async def test_admin_gets_count(self, client, admin_token):
        resp = await client.get("/api/v1/notifications/count", headers=auth(admin_token))
        assert resp.status_code == 200
        assert "count" in resp.json()
        assert isinstance(resp.json()["count"], int)

    async def test_gestionnaire_gets_count(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/notifications/count", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["count"] >= 0

    async def test_locataire_gets_count(self, client, locataire_token):
        """Locataire peut voir son compteur de notifications (fix du bug require_role)."""
        resp = await client.get("/api/v1/notifications/count", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert "count" in resp.json()

    async def test_proprietaire_gets_count(self, client, proprietaire_token):
        resp = await client.get("/api/v1/notifications/count", headers=auth(proprietaire_token))
        assert resp.status_code == 200

    async def test_unauthenticated_denied(self, client):
        resp = await client.get("/api/v1/notifications/count")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestNotificationList:
    async def test_any_user_lists_own_notifications(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/notifications", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data

    async def test_locataire_lists_notifications(self, client, locataire_token):
        resp = await client.get("/api/v1/notifications", headers=auth(locataire_token))
        assert resp.status_code == 200

    async def test_unread_only_filter(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/notifications?unread_only=true", headers=auth(gestionnaire_token))
        assert resp.status_code == 200

    async def test_generate_alerts_admin_only(self, client, admin_token, gestionnaire_token, locataire_token):
        # Admin peut déclencher
        resp = await client.post("/api/v1/notifications/generate-alerts", headers=auth(admin_token))
        assert resp.status_code == 200

        # Gestionnaire ne peut pas
        resp2 = await client.post("/api/v1/notifications/generate-alerts", headers=auth(gestionnaire_token))
        assert resp2.status_code == 403

        # Locataire ne peut pas
        resp3 = await client.post("/api/v1/notifications/generate-alerts", headers=auth(locataire_token))
        assert resp3.status_code == 403


@pytest.mark.asyncio
class TestNotificationMarkRead:
    async def test_mark_all_read(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/notifications/read-all", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert "marked_read" in resp.json()

    async def test_mark_nonexistent_notification(self, client, gestionnaire_token):
        resp = await client.post(
            "/api/v1/notifications/00000000-0000-0000-0000-000000000000/read",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 404
