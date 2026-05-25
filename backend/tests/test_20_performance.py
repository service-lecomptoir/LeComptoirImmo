"""
Tests de performance — vérification des temps de réponse sur les endpoints critiques.

Seuils : endpoints simples < 500ms, listes avec données < 1000ms.
Ces tests mesurent la latence applicative (in-process), sans réseau.
"""
import time
import asyncio
import pytest
from tests.conftest import auth


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


# ── Constantes de seuil ────────────────────────────────────────────────────────
SIMPLE_THRESHOLD_MS = 500     # endpoints simples (me, liste vide)
LIST_THRESHOLD_MS = 1000      # listes avec données
AUTH_THRESHOLD_MS = 2000      # login (hash bcrypt + DB)
BURST_THRESHOLD_MS = 3000     # 10 requêtes consécutives


@pytest.mark.asyncio
class TestAuthPerformance:
    async def test_login_response_time(self, client, gestionnaire_user):
        start = time.perf_counter()
        resp = await client.post("/api/v1/auth/login", json={
            "email": gestionnaire_user.email,
            "password": "GestPass1!",
        })
        ms = elapsed_ms(start)
        assert resp.status_code == 200, resp.text
        assert ms < AUTH_THRESHOLD_MS, f"Login took {ms:.0f}ms (threshold: {AUTH_THRESHOLD_MS}ms)"

    async def test_me_endpoint_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/users/me", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < SIMPLE_THRESHOLD_MS, f"/me took {ms:.0f}ms"

    async def test_refresh_token_response_time(self, client, gestionnaire_user):
        login = await client.post("/api/v1/auth/login", json={
            "email": gestionnaire_user.email,
            "password": "GestPass1!",
        })
        refresh_token = login.json()["refresh_token"]

        start = time.perf_counter()
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < AUTH_THRESHOLD_MS, f"Token refresh took {ms:.0f}ms"


@pytest.mark.asyncio
class TestListEndpointsPerformance:
    async def test_properties_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/properties", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Properties list took {ms:.0f}ms"

    async def test_tenants_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/tenants", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Tenants list took {ms:.0f}ms"

    async def test_leases_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/leases", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Leases list took {ms:.0f}ms"

    async def test_payments_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/payments", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Payments list took {ms:.0f}ms"

    async def test_notifications_count_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/notifications/count", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < SIMPLE_THRESHOLD_MS, f"Notif count took {ms:.0f}ms"

    async def test_contacts_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/contacts", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Contacts list took {ms:.0f}ms"

    async def test_automation_rules_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/automation/rules", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Automation rules took {ms:.0f}ms"

    async def test_tickets_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/tickets", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Tickets list took {ms:.0f}ms"

    async def test_documents_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/documents", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Documents list took {ms:.0f}ms"

    async def test_avis_echeances_list_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/avis-echeances", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Avis list took {ms:.0f}ms"

    async def test_scheduler_settings_response_time(self, client, gestionnaire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/settings/scheduler", headers=auth(gestionnaire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < SIMPLE_THRESHOLD_MS, f"Scheduler settings took {ms:.0f}ms"


@pytest.mark.asyncio
class TestBurstPerformance:
    async def test_10_sequential_me_requests(self, client, gestionnaire_token):
        """10 appels /me consécutifs doivent rester sous le seuil global."""
        start = time.perf_counter()
        for _ in range(10):
            resp = await client.get("/api/v1/users/me", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
        ms = elapsed_ms(start)
        assert ms < BURST_THRESHOLD_MS, f"10× /me took {ms:.0f}ms"

    async def test_concurrent_list_requests(self, client, gestionnaire_token):
        """5 requêtes en parallèle doivent toutes réussir rapidement."""
        endpoints = [
            "/api/v1/properties",
            "/api/v1/tenants",
            "/api/v1/leases",
            "/api/v1/contacts",
            "/api/v1/automation/rules",
        ]
        start = time.perf_counter()
        tasks = [
            client.get(ep, headers=auth(gestionnaire_token))
            for ep in endpoints
        ]
        responses = await asyncio.gather(*tasks)
        ms = elapsed_ms(start)

        for resp in responses:
            assert resp.status_code == 200
        assert ms < BURST_THRESHOLD_MS, f"5 concurrent requests took {ms:.0f}ms"

    async def test_10_sequential_property_list_requests(self, client, gestionnaire_token):
        """10 listes de propriétés consécutives."""
        start = time.perf_counter()
        for _ in range(10):
            resp = await client.get("/api/v1/properties", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
        ms = elapsed_ms(start)
        assert ms < BURST_THRESHOLD_MS * 2, f"10× properties took {ms:.0f}ms"


@pytest.mark.asyncio
class TestLocatairePerformance:
    async def test_locataire_dashboard_response_time(self, client, locataire_token):
        """Le tableau de bord locataire doit être rapide."""
        start = time.perf_counter()
        resp = await client.get("/api/v1/leases", headers=auth(locataire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Locataire /my leases took {ms:.0f}ms"

    async def test_locataire_payments_response_time(self, client, locataire_token):
        start = time.perf_counter()
        resp = await client.get("/api/v1/payments/locataire/current", headers=auth(locataire_token))
        ms = elapsed_ms(start)
        assert resp.status_code == 200
        assert ms < LIST_THRESHOLD_MS, f"Locataire /my payments took {ms:.0f}ms"
