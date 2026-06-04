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


@pytest.mark.asyncio
class TestNotificationIsolation:
    """Garde-fou : chaque compte ne voit QUE ses propres notifications (pas de broadcast)."""

    def _notif(self, user_id, title):
        from app.models.notification import (
            Notification, NotificationType, NotificationPriority,
        )
        return Notification(
            title=title, message="…",
            notification_type=NotificationType.SYSTEME,
            priority=NotificationPriority.NORMAL,
            user_id=user_id,
        )

    async def test_only_own_no_broadcast(self, client, db, gestionnaire_user, gestionnaire_token, gp_user):
        own = self._notif(gestionnaire_user.id, "Pour moi")
        other = self._notif(gp_user.id, "Pour un autre")
        broadcast = self._notif(None, "Ancien broadcast")
        db.add_all([own, other, broadcast])
        await db.flush()

        resp = await client.get("/api/v1/notifications", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert "Pour moi" in titles
        assert "Pour un autre" not in titles      # isolation entre comptes
        assert "Ancien broadcast" not in titles    # plus de diffusion globale

    async def test_cannot_mark_foreign_notification(self, client, db, gp_user, gestionnaire_token):
        foreign = self._notif(gp_user.id, "Notif d'autrui")
        db.add(foreign)
        await db.flush()
        resp = await client.post(
            f"/api/v1/notifications/{foreign.id}/read", headers=auth(gestionnaire_token)
        )
        assert resp.status_code == 404  # ne peut pas marquer lue une notif qui n'est pas la sienne

    async def test_locataire_only_sees_own(self, client, db, locataire_user, locataire_token, gestionnaire_user):
        """Le locataire ne voit QUE ses notifications (ni celles du gestionnaire, ni broadcast)."""
        mine = self._notif(locataire_user.id, "Votre loyer a été validé")
        manager = self._notif(gestionnaire_user.id, "Notif du gestionnaire")
        broadcast = self._notif(None, "Ancien broadcast")
        db.add_all([mine, manager, broadcast])
        await db.flush()

        resp = await client.get("/api/v1/notifications", headers=auth(locataire_token))
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert "Votre loyer a été validé" in titles
        assert "Notif du gestionnaire" not in titles   # pas les notifs d'un autre rôle
        assert "Ancien broadcast" not in titles          # plus de diffusion globale

    async def test_locataire_cannot_mark_manager_notification(self, client, db, gestionnaire_user, locataire_token):
        foreign = self._notif(gestionnaire_user.id, "Notif gestionnaire")
        db.add(foreign)
        await db.flush()
        resp = await client.post(
            f"/api/v1/notifications/{foreign.id}/read", headers=auth(locataire_token)
        )
        assert resp.status_code == 404
