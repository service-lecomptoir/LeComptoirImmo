"""Régression : avec le rate-limiter ACTIF (comme en production), un login valide
doit renvoyer 200 et non 500. Garde contre le bug d'injection d'en-têtes slowapi
(headers_enabled exigeait un paramètre `response` sur l'endpoint)."""
import pytest

from app.core.rate_limit import limiter


@pytest.mark.asyncio
async def test_login_valide_ne_plante_pas_avec_limiter_actif(client, admin_user):
    limiter.enabled = True
    try:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "AdminPass1!"},
        )
    finally:
        limiter.enabled = False
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_invalide_reste_401_avec_limiter_actif(client, admin_user):
    limiter.enabled = True
    try:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "mauvais"},
        )
    finally:
        limiter.enabled = False
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_endpoint_protege_sans_jeton_renvoie_401(client):
    """Recette : absence de jeton = 401 (non authentifié), pas 403."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_endpoint_protege_jeton_invalide_renvoie_401(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer faux"})
    assert resp.status_code == 401, resp.text
