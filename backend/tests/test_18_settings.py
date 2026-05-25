"""
Tests API — Paramètres / Scheduler.
Couvre : lecture config scheduler, mise à jour, calcul next_run, accès RBAC.
"""
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestSchedulerRead:
    async def test_gestionnaire_can_read_scheduler(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "day" in data
        assert "hour" in data
        assert "minute" in data
        assert "next_run" in data

    async def test_gp_can_read_scheduler(self, client, gp_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gp_token))
        assert resp.status_code == 200

    async def test_admin_can_read_scheduler(self, client, admin_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(admin_token))
        assert resp.status_code == 200

    async def test_locataire_cannot_read_scheduler(self, client, locataire_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_proprietaire_cannot_read_scheduler(self, client, proprietaire_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(proprietaire_token))
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_read_scheduler(self, client):
        resp = await client.get("/api/v1/settings/scheduler")
        assert resp.status_code in (401, 403)

    async def test_scheduler_day_range(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gestionnaire_token))
        data = resp.json()
        assert 1 <= data["day"] <= 28
        assert 0 <= data["hour"] <= 23
        assert 0 <= data["minute"] <= 59

    async def test_next_run_is_iso_format(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gestionnaire_token))
        next_run = resp.json().get("next_run")
        assert next_run is not None
        # Doit être parseable comme ISO 8601
        from datetime import datetime
        dt = datetime.fromisoformat(next_run)
        assert dt is not None


@pytest.mark.asyncio
class TestSchedulerUpdate:
    async def test_gestionnaire_can_update_scheduler(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 15, "hour": 8, "minute": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["day"] == 15
        assert data["hour"] == 8
        assert data["minute"] == 0

    async def test_gp_can_update_scheduler(self, client, gp_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gp_token),
            json={"day": 5, "hour": 9, "minute": 30},
        )
        assert resp.status_code == 200
        assert resp.json()["day"] == 5

    async def test_locataire_cannot_update_scheduler(self, client, locataire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(locataire_token),
            json={"day": 1, "hour": 0, "minute": 0},
        )
        assert resp.status_code == 403

    async def test_invalid_day_too_large(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 29, "hour": 8, "minute": 0},
        )
        assert resp.status_code == 422

    async def test_invalid_day_too_small(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 0, "hour": 8, "minute": 0},
        )
        assert resp.status_code == 422

    async def test_invalid_hour(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 1, "hour": 24, "minute": 0},
        )
        assert resp.status_code == 422

    async def test_invalid_minute(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 1, "hour": 8, "minute": 60},
        )
        assert resp.status_code == 422

    async def test_update_returns_next_run(self, client, gestionnaire_token):
        resp = await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 20, "hour": 7, "minute": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "next_run" in data
        assert data["next_run"] is not None

    async def test_update_persists(self, client, gestionnaire_token):
        await client.put(
            "/api/v1/settings/scheduler",
            headers=auth(gestionnaire_token),
            json={"day": 22, "hour": 10, "minute": 15},
        )
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["day"] == 22
        assert data["hour"] == 10
        assert data["minute"] == 15
