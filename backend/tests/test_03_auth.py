"""
Tests API — Authentification (login, refresh, me).
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from tests.conftest import auth, _create_user


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client, gestionnaire_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": gestionnaire_user.email,
            "password": "GestPass1!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client, gestionnaire_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": gestionnaire_user.email,
            "password": "MauvaisMotDePasse",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "inexistant@test.fr",
            "password": "Password1!",
        })
        assert resp.status_code == 401

    async def test_login_inactive_user(self, client, db):
        user = await _create_user(db, "inactive@test.fr", "Pass1!", "gestionnaire")
        user.is_active = False
        await db.flush()

        resp = await client.post("/api/v1/auth/login", json={
            "email": "inactive@test.fr",
            "password": "Pass1!",
        })
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client):
        resp = await client.post("/api/v1/auth/login", json={"email": "x@test.fr"})
        assert resp.status_code == 422

    async def test_login_invalid_email_format(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "pas-un-email",
            "password": "Pass1!",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestRefreshToken:
    async def test_refresh_success(self, client, gestionnaire_user):
        login = await client.post("/api/v1/auth/login", json={
            "email": gestionnaire_user.email,
            "password": "GestPass1!",
        })
        refresh_token = login.json()["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_with_access_token_fails(self, client, gestionnaire_token):
        """Un access token ne doit pas être accepté comme refresh token."""
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": gestionnaire_token})
        assert resp.status_code == 401

    async def test_refresh_invalid_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "token.invalide.ici"})
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestGetMe:
    async def test_me_returns_user_info(self, client, gestionnaire_token, gestionnaire_user):
        resp = await client.get("/api/v1/auth/me", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == gestionnaire_user.email
        assert data["role"] == "gestionnaire"
        assert "hashed_password" not in data

    async def test_me_without_token_returns_403(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    async def test_me_with_bad_token_returns_401(self, client):
        resp = await client.get("/api/v1/auth/me", headers=auth("mauvais.token.ici"))
        assert resp.status_code == 401

    async def test_me_locataire_role(self, client, locataire_token):
        resp = await client.get("/api/v1/auth/me", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert resp.json()["role"] == "locataire"

    async def test_me_proprietaire_role(self, client, proprietaire_token):
        resp = await client.get("/api/v1/auth/me", headers=auth(proprietaire_token))
        assert resp.status_code == 200
        assert resp.json()["role"] == "proprietaire"
