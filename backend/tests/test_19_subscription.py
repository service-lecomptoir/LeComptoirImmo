"""
Tests API — Abonnement (GET /subscription).
Couvre : accès RBAC, réponse quand Alice indisponible, structure de la réponse.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import auth


@pytest.mark.asyncio
class TestSubscriptionRBAC:
    async def test_gestionnaire_can_get_subscription(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
        # 200 ou 503 si Alice indispo — les deux sont valides en dev
        assert resp.status_code in (200,)

    async def test_gp_can_get_subscription(self, client, gp_token):
        resp = await client.get("/api/v1/subscription", headers=auth(gp_token))
        assert resp.status_code in (200,)

    async def test_locataire_cannot_get_subscription(self, client, locataire_token):
        resp = await client.get("/api/v1/subscription", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_proprietaire_cannot_get_subscription(self, client, proprietaire_token):
        resp = await client.get("/api/v1/subscription", headers=auth(proprietaire_token))
        assert resp.status_code == 403

    async def test_admin_cannot_get_subscription(self, client, admin_token):
        # Admin n'est pas gestionnaire → 403
        resp = await client.get("/api/v1/subscription", headers=auth(admin_token))
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_get_subscription(self, client):
        resp = await client.get("/api/v1/subscription")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestSubscriptionResponseStructure:
    """Teste la structure de réponse quand Alice est mocké."""

    async def test_response_when_alice_unavailable(self, client, gestionnaire_token):
        """Quand Alice est injoignable, l'endpoint répond avec les infos DB locales."""
        import httpx

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.side_effect = Exception("Alice unavailable")

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            data = resp.json()
            assert "is_blocked" in data
            assert "property_count" in data
            assert "can_create_property" in data

    async def test_response_when_alice_returns_license(self, client, gestionnaire_token):
        """Quand Alice retourne une licence valide, la réponse est bien formée."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "gestionnaire_user_id": "00000000-0000-0000-0000-000000000001",
            "is_blocked": False,
            "property_limit": 10,
            "plan_name": "Pro",
        }

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            data = resp.json()
            assert data["plan_name"] == "Pro"
            assert data["is_blocked"] is False
            assert data["property_limit"] == 10
            assert "property_count" in data
            assert "can_create_property" in data

    async def test_blocked_gestionnaire_is_locked_out(self, client, gestionnaire_token):
        """Une licence bloquée (is_blocked=True) suspend le compte : toute requête
        authentifiée est refusée (401), ce qui empêche a fortiori la création de biens.
        L'enforcement se fait au niveau de get_current_user (_check_alice_license)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "gestionnaire_user_id": "any",
            "is_blocked": True,
            "property_limit": 10,
            "plan_name": "Pro",
        }

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response

            # La licence est mise en cache (perf) ; le login du fixture a mis en
            # cache l'état "non bloqué". On vide le cache pour que le statut bloqué
            # mocké ici soit pris en compte immédiatement.
            from app.services import alice_client
            alice_client.invalidate_license_cache()

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 401

    async def test_property_limit_reached_cannot_create(self, client, gestionnaire_token):
        """Atteinte de la limite property_limit → can_create_property=False."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "gestionnaire_user_id": "any",
            "is_blocked": False,
            "property_limit": 0,  # Limite atteinte
            "plan_name": "Starter",
        }

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            assert resp.json()["can_create_property"] is False

    async def test_no_license_404_means_blocked(self, client, gestionnaire_token):
        """Alice 404 (pas de licence) → is_blocked=True."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            assert resp.json()["is_blocked"] is True
