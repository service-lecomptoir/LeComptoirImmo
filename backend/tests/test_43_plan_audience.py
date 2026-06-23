"""Tests — distinction de plan gestionnaire propriétaire vs mandataire.

Le plan Alice porte DEUX listes de fonctionnalités (une par profil) car les deux
profils n'ont pas le même périmètre : compta mandant, syndic et tampon sont
réservés au mandataire. Côté Immo :
  - le catalogue expose une `audience` par fonctionnalité ;
  - `_features_for_role` choisit la bonne liste selon le rôle (repli sur `features`) ;
  - l'endpoint /subscription renvoie la liste résolue pour le rôle connecté.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_catalog import public_catalog
from app.core.features import _features_for_role
from app.core.permissions import Role
from tests.conftest import auth


# ── Catalogue : audience exposée ─────────────────────────────────────────────
class TestCatalogAudience:
    def test_public_catalog_exposes_audience(self):
        cat = {item["key"]: item for item in public_catalog()}
        # Chaque entrée a une audience (défaut "all").
        assert all("audience" in item for item in cat.values())

    def test_mandataire_only_features_tagged(self):
        cat = {item["key"]: item["audience"] for item in public_catalog()}
        assert cat["tampon"] == "mandataire"
        assert cat["compta_mandant"] == "mandataire"
        assert cat["syndic"] == "mandataire"

    def test_common_features_are_all(self):
        cat = {item["key"]: item["audience"] for item in public_catalog()}
        for key in ("dashboard", "properties", "tenants", "leases", "quittances"):
            assert cat[key] == "all"


# ── Résolution de la liste selon le profil ───────────────────────────────────
class TestFeaturesForRole:
    LIC = {
        "features": ["dashboard", "tampon"],
        "features_proprietaire": ["dashboard"],
        "features_mandataire": ["dashboard", "tampon", "syndic"],
    }

    def test_proprio_gets_proprietaire_list(self):
        feats = _features_for_role(self.LIC, Role.GESTIONNAIRE_PROPRIO.value)
        assert feats == ["dashboard"]
        assert "tampon" not in feats  # réservé au mandataire

    def test_mandataire_gets_mandataire_list(self):
        feats = _features_for_role(self.LIC, Role.GESTIONNAIRE.value)
        assert "syndic" in feats and "tampon" in feats

    def test_falls_back_to_features_when_profile_list_missing(self):
        lic = {"features": ["dashboard", "payments"]}  # pas de listes par profil
        assert _features_for_role(lic, Role.GESTIONNAIRE_PROPRIO.value) == ["dashboard", "payments"]
        assert _features_for_role(lic, Role.GESTIONNAIRE.value) == ["dashboard", "payments"]

    def test_profile_none_falls_back_even_if_other_profile_set(self):
        lic = {"features": ["a"], "features_mandataire": ["a", "b"]}
        # GP : sa liste est None → repli sur features.
        assert _features_for_role(lic, Role.GESTIONNAIRE_PROPRIO.value) == ["a"]

    def test_non_manager_role_uses_features(self):
        assert _features_for_role(self.LIC, Role.PROPRIETAIRE.value) == ["dashboard", "tampon"]


# ── Endpoint /subscription : liste résolue selon le rôle connecté ─────────────
def _mock_license(payload):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_class = patch("httpx.AsyncClient")
    return mock_class, mock_response


@pytest.mark.asyncio
class TestSubscriptionResolvesByRole:
    PAYLOAD = {
        "gestionnaire_user_id": "any",
        "is_blocked": False,
        "property_limit": 10,
        "plan_name": "Pro",
        "features": ["dashboard", "tampon", "syndic"],
        "features_proprietaire": ["dashboard"],
        "features_mandataire": ["dashboard", "tampon", "syndic"],
    }

    async def test_gp_receives_proprietaire_features(self, client, gp_token):
        from app.services import alice_client

        alice_client.invalidate_license_cache()
        mock_class, mock_response = _mock_license(self.PAYLOAD)
        with mock_class as mc:
            mock_client = AsyncMock()
            mc.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mc.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response
            resp = await client.get("/api/v1/subscription", headers=auth(gp_token))
        assert resp.status_code == 200
        feats = resp.json()["features"]
        assert feats == ["dashboard"]
        assert "syndic" not in feats and "tampon" not in feats

    async def test_mandataire_receives_mandataire_features(self, client, gestionnaire_token):
        from app.services import alice_client

        alice_client.invalidate_license_cache()
        mock_class, mock_response = _mock_license(self.PAYLOAD)
        with mock_class as mc:
            mock_client = AsyncMock()
            mc.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mc.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get.return_value = mock_response
            resp = await client.get("/api/v1/subscription", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        feats = resp.json()["features"]
        assert "syndic" in feats and "tampon" in feats
