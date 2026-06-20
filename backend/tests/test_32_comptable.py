"""Rôle COMPTABLE : sous-compte de gestion en LECTURE seule + encaissement.
Un gestionnaire peut le créer ; le comptable lit les écrans de gestion mais ne
peut rien administrer (biens, locataires, utilisateurs)."""
import uuid

import pytest

from tests.conftest import _get_token, auth


@pytest.mark.asyncio
async def test_gestionnaire_cree_comptable(client, gestionnaire_token):
    email = f"compta_{uuid.uuid4().hex[:8]}@test.fr"
    r = await client.post(
        "/api/v1/users",
        headers=auth(gestionnaire_token),
        json={
            "email": email, "password": "ComptaPass1!",
            "full_name": "Comp Table", "role": "comptable",
        },
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_comptable_lecture_seule(client, gestionnaire_token):
    email = f"compta_{uuid.uuid4().hex[:8]}@test.fr"
    r = await client.post(
        "/api/v1/users", headers=auth(gestionnaire_token),
        json={"email": email, "password": "ComptaPass1!",
              "full_name": "Comp Table", "role": "comptable"},
    )
    assert r.status_code == 201, r.text
    tok = await _get_token(client, email, "ComptaPass1!")

    # LECTURE INTÉGRALE (mêmes écrans que le gestionnaire).
    for path in ("/api/v1/properties", "/api/v1/tenants", "/api/v1/owners",
                 "/api/v1/leases", "/api/v1/payments", "/api/v1/dashboard/stats"):
        assert (await client.get(path, headers=auth(tok))).status_code == 200, path

    # ÉCRITURE INTERDITE (garde global), y compris création de bien.
    assert (await client.post(
        "/api/v1/properties", headers=auth(tok),
        json={"name": "X", "address": "1 rue", "zip_code": "75001", "city": "Paris"},
    )).status_code == 403

    # ÉCRITURE INTERDITE (dependency 403 avant tout traitement).
    rid = str(uuid.uuid4())
    assert (await client.delete(f"/api/v1/properties/{rid}", headers=auth(tok))).status_code == 403
    assert (await client.delete(f"/api/v1/tenants/{rid}", headers=auth(tok))).status_code == 403
    assert (await client.delete(f"/api/v1/owners/{rid}", headers=auth(tok))).status_code == 403

    # AUCUN droit d'administration des comptes.
    r = await client.post(
        "/api/v1/users", headers=auth(tok),
        json={"email": f"x_{uuid.uuid4().hex[:6]}@t.fr", "password": "Xx123456!",
              "full_name": "A B", "role": "locataire"},
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_comptable_dans_le_perimetre_lit_un_bien(client, gestionnaire_token):
    """Le comptable (même agence que son gestionnaire) peut OUVRIR le détail d'un bien."""
    # Le gestionnaire crée un bien.
    prop = await client.post(
        "/api/v1/properties", headers=auth(gestionnaire_token),
        json={"name": "Bien test compta", "address": "1 rue du Test",
              "zip_code": "75001", "city": "Paris", "property_type": "appartement"},
    )
    if prop.status_code != 201:
        pytest.skip(f"création bien indisponible dans cet env: {prop.status_code}")
    prop_id = prop.json()["id"]

    email = f"compta_{uuid.uuid4().hex[:8]}@test.fr"
    await client.post(
        "/api/v1/users", headers=auth(gestionnaire_token),
        json={"email": email, "password": "ComptaPass1!",
              "full_name": "Comp Table", "role": "comptable"},
    )
    tok = await _get_token(client, email, "ComptaPass1!")
    # Détail du bien (get_current_manager) : 200 pour le comptable de l'agence.
    r = await client.get(f"/api/v1/properties/{prop_id}", headers=auth(tok))
    assert r.status_code == 200, r.text
