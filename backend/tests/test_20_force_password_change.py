"""
Mot de passe temporaire : un gestionnaire provisionné par Alice (POST /internal
/managers) reçoit must_change_password=True et doit définir son propre mot de
passe à la première connexion. Le flag retombe à False après changement.
"""
import uuid
import pytest

from app.config import get_settings

INTERNAL_HEADERS = {"X-Internal-Key": get_settings().ALICE_INTERNAL_KEY}


@pytest.mark.asyncio
async def test_provisioned_manager_must_change_password(client):
    email = f"mgr_{uuid.uuid4().hex[:8]}@cabinet.fr"
    temp_pw = "TempPass123!"

    # 1) Alice crée le gestionnaire avec un mot de passe provisoire.
    resp = await client.post(
        "/internal/managers",
        headers=INTERNAL_HEADERS,
        json={"email": email, "password": temp_pw, "full_name": "Cabinet Test", "role": "gestionnaire"},
    )
    assert resp.status_code == 201, resp.text

    # 2) Il se connecte et /auth/me indique le mot de passe temporaire.
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": temp_pw})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=auth)
    assert me.status_code == 200, me.text
    assert me.json()["must_change_password"] is True

    # 3) Il définit son propre mot de passe → le flag retombe à False.
    chg = await client.patch(
        "/api/v1/users/me/password",
        headers=auth,
        json={"current_password": temp_pw, "new_password": "MyOwnPass456!"},
    )
    assert chg.status_code == 204, chg.text

    me2 = await client.get("/api/v1/auth/me", headers=auth)
    assert me2.json()["must_change_password"] is False

    # 4) Le nouveau mot de passe fonctionne ; l'ancien (temporaire) non.
    ok = await client.post("/api/v1/auth/login", json={"email": email, "password": "MyOwnPass456!"})
    assert ok.status_code == 200
    ko = await client.post("/api/v1/auth/login", json={"email": email, "password": temp_pw})
    assert ko.status_code == 401


@pytest.mark.asyncio
async def test_internal_reset_password_sets_temporary_flag(client):
    email = f"mgr_{uuid.uuid4().hex[:8]}@cabinet.fr"
    create = await client.post(
        "/internal/managers",
        headers=INTERNAL_HEADERS,
        json={"email": email, "password": "TempPass123!", "full_name": "Cabinet Reset", "role": "gestionnaire"},
    )
    mid = create.json()["id"]

    # Le gestionnaire normalise son mot de passe une première fois.
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "TempPass123!"})
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me/password", headers=auth,
                       json={"current_password": "TempPass123!", "new_password": "Personal789!"})

    # Alice réinitialise le mot de passe → de nouveau temporaire.
    reset = await client.post(
        f"/internal/managers/{mid}/reset-password",
        headers=INTERNAL_HEADERS,
        json={"new_password": "ResetTemp999!"},
    )
    assert reset.status_code == 204, reset.text

    login2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "ResetTemp999!"})
    token2 = login2.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert me.json()["must_change_password"] is True
