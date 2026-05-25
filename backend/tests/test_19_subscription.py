"""
Tests API — Abonnement (GET /subscription).
Couvre : accès RBAC, réponse quand ProxyGen indisponible, structure de la réponse.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import auth


@pytest.mark.asyncio
class TestSubscriptionRBAC:
    async def test_gestionnaire_can_get_subscription(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
        # 200 ou 503 si ProxyGen indispo — les deux sont valides en dev
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
    """Teste la structure de réponse quand ProxyGen est mocké."""

    async def test_response_when_proxygen_unavailable(self, client, gestionnaire_token):
        """Quand ProxyGen est injoignable, l'endpoint répond avec les infos DB locales."""
        import httpx

        with patch("httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.side_effect = Exception("ProxyGen unavailable")

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            data = resp.json()
            assert "is_blocked" in data
            assert "property_count" in data
            assert "can_create_property" in data

    async def test_response_when_proxygen_returns_license(self, client, gestionnaire_token):
        """Quand ProxyGen retourne une licence valide, la réponse est bien formée."""
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

    async def test_blocked_gestionnaire_cannot_create_property(self, client, gestionnaire_token):
        """Un gestionnaire bloqué (is_blocked=True) doit avoir can_create_property=False."""
        import httpx

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

            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
            assert resp.status_code == 200
            assert resp.json()["can_create_property"] is False

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
        """ProxyGen 404 (pas de licence) → is_blocked=True."""
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
