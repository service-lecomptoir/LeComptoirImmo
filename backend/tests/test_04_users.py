"""
Tests API — Gestion des utilisateurs.
"""
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestUserList:
    async def test_admin_can_list_users(self, client, admin_token):
        resp = await client.get("/api/v1/users", headers=auth(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_gestionnaire_cannot_list_users(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/users", headers=auth(gestionnaire_token))
        assert resp.status_code == 403

    async def test_locataire_cannot_list_users(self, client, locataire_token):
        resp = await client.get("/api/v1/users", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_list_users(self, client):
        resp = await client.get("/api/v1/users")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestUserCreate:
    async def test_admin_creates_user(self, client, admin_token):
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "new_user@test.fr",
            "password": "NewPass1!",
            "full_name": "Nouvel Utilisateur",
            "role": "gestionnaire",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new_user@test.fr"
        assert data["role"] == "gestionnaire"
        assert "hashed_password" not in data

    async def test_gestionnaire_cannot_create_user(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/users", headers=auth(gestionnaire_token), json={
            "email": "forbidden@test.fr",
            "password": "Pass1!",
            "full_name": "X",
            "role": "locataire",
        })
        assert resp.status_code == 403

    async def test_create_user_short_password(self, client, admin_token):
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "short@test.fr",
            "password": "abc",
            "full_name": "Short",
            "role": "locataire",
        })
        assert resp.status_code == 422

    async def test_create_user_invalid_role(self, client, admin_token):
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "role@test.fr",
            "password": "ValidPass1!",
            "full_name": "X",
            "role": "superadmin",
        })
        assert resp.status_code == 422

    async def test_create_duplicate_email(self, client, admin_token, gestionnaire_user):
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": gestionnaire_user.email,
            "password": "Pass1!",
            "full_name": "Dupliquer",
            "role": "locataire",
        })
        assert resp.status_code in (409, 400)


@pytest.mark.asyncio
class TestUserMe:
    async def test_any_role_can_get_me(self, client, locataire_token, locataire_user):
        resp = await client.get("/api/v1/users/me", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert resp.json()["email"] == locataire_user.email

    async def test_me_does_not_expose_password(self, client, admin_token):
        resp = await client.get("/api/v1/users/me", headers=auth(admin_token))
        data = resp.json()
        assert "password" not in data
        assert "hashed_password" not in data
