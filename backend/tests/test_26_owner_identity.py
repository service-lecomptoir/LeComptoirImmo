"""Tests API — règle d'identité d'une fiche propriétaire (Owner).

Une fiche est valide si elle identifie soit une PERSONNE (prénom + nom),
soit une PERSONNE MORALE (société + SIREN/SIRET). Le « Nom » seul n'est plus
suffisant ni obligatoire.
"""
import pytest

from tests.conftest import auth

API = "/api/v1"


@pytest.mark.asyncio
async def test_owner_person_ok(client, gestionnaire_token):
    """Personne : prénom + nom → 201."""
    r = await client.post(
        f"{API}/owners",
        headers=auth(gestionnaire_token),
        json={"first_name": "Jean", "last_name": "Dupont"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["full_name"] == "Jean Dupont"


@pytest.mark.asyncio
async def test_owner_company_ok(client, gestionnaire_token):
    """Personne morale : société + SIREN, sans prénom/nom → 201 ;
    le nom affiché (full_name) est la société, et last_name est rempli."""
    r = await client.post(
        f"{API}/owners",
        headers=auth(gestionnaire_token),
        json={"company_name": "SCI Les Tilleuls", "national_id": "812345678"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["full_name"] == "SCI Les Tilleuls"
    assert body["last_name"] == "SCI Les Tilleuls"


@pytest.mark.asyncio
async def test_owner_last_name_only_rejected(client, gestionnaire_token):
    """Nom seul (sans prénom, sans couple société+SIREN) → 422."""
    r = await client.post(
        f"{API}/owners",
        headers=auth(gestionnaire_token),
        json={"last_name": "Dupont"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_owner_company_without_siren_rejected(client, gestionnaire_token):
    """Société sans SIREN et sans prénom/nom → 422."""
    r = await client.post(
        f"{API}/owners",
        headers=auth(gestionnaire_token),
        json={"company_name": "SCI Les Tilleuls"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_owner_empty_rejected(client, gestionnaire_token):
    """Aucune identité → 422."""
    r = await client.post(
        f"{API}/owners",
        headers=auth(gestionnaire_token),
        json={"email": "x@y.fr"},
    )
    assert r.status_code == 422, r.text
