"""Tests API — Actualisation (IRL) + contrats de génération (loyers / avis).

Couvre :
  • IRL : ajout, listing, robustesse (trimestre invalide → 400) ;
  • Régression du contrat front↔back : les endpoints de génération acceptent
    un corps JSON (et non des query params) — verrou anti-régression sur les
    boutons « Générer les loyers » / « Générer les avis du mois » ;
  • Robustesse : payload incomplet → 422, accès non gestionnaire → 403.
"""
import pytest

from tests.conftest import auth

API = "/api/v1"


# ── IRL : ajout / listing / robustesse ────────────────────────────────────────
@pytest.mark.asyncio
async def test_irl_add_and_list(client, gestionnaire_token):
    r = await client.post(
        f"{API}/actualisation/irl",
        headers=auth(gestionnaire_token),
        json={"year": 2024, "quarter": 1, "value": 143.46},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["year"] == 2024 and body["quarter"] == 1

    r = await client.get(f"{API}/actualisation/irl", headers=auth(gestionnaire_token))
    assert r.status_code == 200
    assert any(i["year"] == 2024 and i["quarter"] == 1 for i in r.json())


@pytest.mark.asyncio
async def test_irl_invalid_quarter_rejected(client, gestionnaire_token):
    r = await client.post(
        f"{API}/actualisation/irl",
        headers=auth(gestionnaire_token),
        json={"year": 2025, "quarter": 9, "value": 100.0},
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_irl_requires_manager(client, locataire_token):
    r = await client.get(f"{API}/actualisation/irl", headers=auth(locataire_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_revision_list_forbidden_for_locataire(client, locataire_token):
    r = await client.get(f"{API}/actualisation/loyers", headers=auth(locataire_token))
    assert r.status_code == 403


# ── Contrat de génération : corps JSON accepté (anti-régression front) ─────────
@pytest.mark.asyncio
async def test_payments_generate_accepts_json_body(client, gestionnaire_token):
    """Le front POST un corps JSON {year, month}; le back ne doit PAS exiger
    des query params (sinon 422 et bouton cassé)."""
    r = await client.post(
        f"{API}/payments/generate",
        headers=auth(gestionnaire_token),
        json={"year": 2026, "month": 1},
    )
    assert r.status_code != 422, f"corps JSON refusé : {r.text}"
    assert r.status_code in (200, 201), r.text


@pytest.mark.asyncio
async def test_avis_generate_monthly_accepts_json_body(client, gestionnaire_token):
    r = await client.post(
        f"{API}/avis-echeances/generate-monthly",
        headers=auth(gestionnaire_token),
        json={"period_year": 2026, "period_month": 1},
    )
    assert r.status_code != 422, f"corps JSON refusé : {r.text}"
    assert r.status_code in (200, 201), r.text


@pytest.mark.asyncio
async def test_avis_generate_one_requires_lease_id(client, gestionnaire_token):
    """Génération unitaire : payload incomplet (sans lease_id) → 422."""
    r = await client.post(
        f"{API}/avis-echeances/generate",
        headers=auth(gestionnaire_token),
        json={"period_year": 2026, "period_month": 1},
    )
    assert r.status_code == 422

# NB : le blocage des rôles non-gestionnaires sur POST /payments/generate est
# vérifié en recette live (403). Il n'est pas reproductible via le client de test
# ASGI : la session monkey-patchée du conftest (commit→flush, sans contexte
# greenlet sur le chemin de nettoyage) lève « greenlet_spawn » quand une
# HTTPException interrompt un POST avec corps. Les variantes GET ci-dessus
# (test_irl_requires_manager / test_revision_list_forbidden_for_locataire)
# couvrent déjà le verrou get_current_gestionnaire.
