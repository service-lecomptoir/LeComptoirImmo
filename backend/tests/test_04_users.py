"""
Tests API — Gestion des utilisateurs.
"""
import uuid
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestUserList:
    async def test_admin_can_list_users(self, client, admin_token):
        resp = await client.get("/api/v1/users", headers=auth(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_gestionnaire_can_list_users(self, client, gestionnaire_token):
        # Gestionnaire peut lister (restreint à proprio/locataire dans sa portée)
        resp = await client.get("/api/v1/users", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_gestionnaire_list_excludes_self(self, client, gestionnaire_token):
        # Le mandataire gère son propre compte dans « Mes informations » : il ne
        # doit jamais apparaître dans la liste « Gestion des utilisateurs ».
        me = (await client.get("/api/v1/users/me", headers=auth(gestionnaire_token))).json()
        rows = (await client.get("/api/v1/users", headers=auth(gestionnaire_token))).json()
        ids = {u["id"] for u in rows}
        assert me["id"] not in ids
        # Aucun compte de niveau gestionnaire dans la liste.
        assert all(u["role"] not in ("admin", "gestionnaire", "gestionnaire_proprio") for u in rows)

    async def test_gp_list_excludes_self_and_shows_only_managed(self, client, gp_token):
        # Le GP ne voit pas son propre compte (géré dans « Mes informations »).
        me = (await client.get("/api/v1/users/me", headers=auth(gp_token))).json()
        rows = (await client.get("/api/v1/users", headers=auth(gp_token))).json()
        ids = {u["id"] for u in rows}
        assert me["id"] not in ids
        assert all(u["role"] not in ("admin", "gestionnaire", "gestionnaire_proprio") for u in rows)

    async def test_locataire_cannot_list_users(self, client, locataire_token):
        resp = await client.get("/api/v1/users", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_list_users(self, client):
        resp = await client.get("/api/v1/users")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestUserCreate:
    async def test_admin_creates_user(self, client, admin_token):
        # Règle : les comptes gestionnaire/admin sont créés EXCLUSIVEMENT depuis Alice.
        # L'admin ne peut créer que des rôles non-gestionnaire (propriétaire, locataire).
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "new_user@test.fr",
            "password": "NewPass1!",
            "full_name": "Nouvel Utilisateur",
            "role": "proprietaire",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new_user@test.fr"
        assert data["role"] == "proprietaire"
        assert "hashed_password" not in data

    async def test_admin_cannot_create_gestionnaire(self, client, admin_token):
        # Les comptes gestionnaire ne se créent que depuis Alice → 403 attendu.
        resp = await client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": f"gest_{uuid.uuid4().hex[:8]}@test.fr",
            "password": "GestPass1!",
            "full_name": "Gestionnaire interdit",
            "role": "gestionnaire",
        })
        assert resp.status_code == 403

    async def test_gestionnaire_can_create_locataire(self, client, gestionnaire_token):
        # Gestionnaire peut créer un locataire ou propriétaire (pas admin/gestionnaire)
        resp = await client.post("/api/v1/users", headers=auth(gestionnaire_token), json={
            "email": f"loc_{uuid.uuid4().hex[:8]}@test.fr",
            "password": "LocPass1!",
            "full_name": "Nouveau Locataire",
            "role": "locataire",
        })
        assert resp.status_code == 201

    async def test_gestionnaire_cannot_create_admin(self, client, gestionnaire_token):
        # Gestionnaire ne peut pas créer un admin
        resp = await client.post("/api/v1/users", headers=auth(gestionnaire_token), json={
            "email": f"adm_{uuid.uuid4().hex[:8]}@test.fr",
            "password": "AdminPass1!",
            "full_name": "Hack Admin",
            "role": "admin",
        })
        assert resp.status_code == 403

    async def test_create_user_without_password_autogenerates(self, client, gestionnaire_token):
        # Sans mot de passe fourni : le serveur en génère un (transparent) et
        # marque le compte « à changer à la 1re connexion ».
        resp = await client.post("/api/v1/users", headers=auth(gestionnaire_token), json={
            "email": f"auto_{uuid.uuid4().hex[:8]}@test.fr",
            "full_name": "Compte Auto",
            "role": "locataire",
        })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["must_change_password"] is True
        assert "credentials_email_sent" in body  # champ présent (best-effort)

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
            "password": "ValidPass1!",
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
