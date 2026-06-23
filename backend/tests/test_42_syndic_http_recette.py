"""Recette HTTP de bout en bout du module Syndic (parcours réel via l'API).

Un gestionnaire (syndic) déroule : copropriété → clé → lots → budget → appel de
fonds → encaissement → comptes → dépense → régularisation → AG + vote → fonds de
travaux → carnet d'entretien → coffre de documents (upload/list/download/delete).
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth

YEAR = 2026


@pytest.mark.asyncio
async def test_syndic_full_http_workflow(client: AsyncClient, gestionnaire_token):
    h = auth(gestionnaire_token)

    # 1) Créer la copropriété (clé générale auto).
    r = await client.post(
        "/api/v1/coproprietes", json={"name": "Résidence Recette", "city": "Lyon"}, headers=h
    )
    assert r.status_code == 201, r.text
    copro = r.json()
    cid = copro["id"]
    gen = copro["keys"][0]["id"]
    assert copro["keys"][0]["is_general"] is True

    # 2) Clé spéciale ascenseur (base 1000).
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/keys",
        json={"name": "Ascenseur", "total_tantiemes": 1000},
        headers=h,
    )
    assert r.status_code == 201, r.text
    asc = r.json()["id"]

    # 3) Deux propriétaires + deux lots.
    async def mk_owner(name):
        rr = await client.post(
            "/api/v1/owners",
            json={"first_name": name, "last_name": "Copro", "email": f"{name}@t.fr"},
            headers=h,
        )
        assert rr.status_code == 201, rr.text
        return rr.json()["id"]

    o1 = await mk_owner("alice")
    o2 = await mk_owner("bob")
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/lots",
        headers=h,
        json={
            "numero": "Lot 1",
            "owner_id": o1,
            "tantiemes": [{"key_id": gen, "tantiemes": 6000}, {"key_id": asc, "tantiemes": 600}],
        },
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/lots",
        headers=h,
        json={
            "numero": "Lot 2",
            "owner_id": o2,
            "tantiemes": [{"key_id": gen, "tantiemes": 4000}, {"key_id": asc, "tantiemes": 400}],
        },
    )
    assert r.status_code == 201, r.text

    # Détail : clés équilibrées.
    r = await client.get(f"/api/v1/coproprietes/{cid}", headers=h)
    keys = {k["name"]: k for k in r.json()["keys"]}
    assert keys["Charges générales"]["balanced"] is True
    assert keys["Ascenseur"]["balanced"] is True

    # 4) Budget trimestriel (général 12000 + ascenseur 4000).
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/budgets",
        headers=h,
        json={
            "year": YEAR,
            "periodicity": "trimestriel",
            "lines": [
                {"key_id": gen, "label": "Charges générales", "amount": 12000},
                {"key_id": asc, "label": "Ascenseur", "amount": 4000},
            ],
        },
    )
    assert r.status_code == 201, r.text
    budget = r.json()
    assert budget["total"] == 16000
    bid = budget["id"]

    # 5) Appel de fonds T1 : 16000/4 = 4000 ; o1 2400, o2 1600.
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/budgets/{bid}/calls", headers=h, json={"period_index": 1}
    )
    assert r.status_code == 201, r.text
    call = r.json()
    assert call["total_due"] == 4000
    item_o1 = next(i for i in call["items"] if i["owner_id"] == o1)
    assert item_o1["amount_due"] == 2400

    # 6) Encaissement partiel de o1 (1000).
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/call-items/{item_o1['id']}/payments",
        headers=h,
        json={"amount": 1000, "payment_date": f"{YEAR}-02-01"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "partial"

    # 7) Comptes copropriétaires.
    r = await client.get(f"/api/v1/coproprietes/{cid}/accounts", params={"year": YEAR}, headers=h)
    accounts = {a["owner_id"]: a for a in r.json()}
    assert accounts[o1]["total_due"] == 2400
    assert accounts[o1]["total_paid"] == 1000
    assert accounts[o1]["balance"] == 1400

    # 8) Dépense réelle + régularisation.
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/expenses",
        headers=h,
        json={"year": YEAR, "key_id": gen, "label": "Nettoyage", "amount": 10000},
    )
    assert r.status_code == 201, r.text
    r = await client.get(
        f"/api/v1/coproprietes/{cid}/regularization", params={"year": YEAR}, headers=h
    )
    regul = r.json()
    assert regul["expenses_total"] == 10000
    row_o1 = next(x for x in regul["rows"] if x["owner_id"] == o1)
    assert row_o1["reel"] == 6000  # 10000 * 6000/10000

    # 9) Assemblée + résolution + vote → adoptée (art24).
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/assemblies",
        headers=h,
        json={"title": "AG 2026", "kind": "ordinaire"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/assemblies/{aid}/resolutions",
        headers=h,
        json={"title": "Approbation des comptes", "majority": "art24"},
    )
    rid = r.json()["resolutions"][0]["id"]
    await client.post(
        f"/api/v1/coproprietes/{cid}/assemblies/{aid}/resolutions/{rid}/vote",
        headers=h,
        json={"owner_id": o1, "choice": "pour"},
    )
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/assemblies/{aid}/resolutions/{rid}/vote",
        headers=h,
        json={"owner_id": o2, "choice": "contre"},
    )
    res = r.json()["resolutions"][0]
    assert res["pour"] == 6000 and res["contre"] == 4000 and res["outcome"] == "adopted"

    # PV PDF.
    r = await client.get(f"/api/v1/coproprietes/{cid}/assemblies/{aid}/pv/pdf", headers=h)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    # 10) Fonds de travaux (ALUR).
    await client.post(
        f"/api/v1/coproprietes/{cid}/works-fund",
        headers=h,
        json={
            "entry_date": f"{YEAR}-01-01",
            "kind": "contribution",
            "label": "Cotisation",
            "amount": 5000,
        },
    )
    r = await client.get(f"/api/v1/coproprietes/{cid}/works-fund", headers=h)
    assert r.json()["balance"] == 5000

    # 11) Carnet d'entretien.
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/maintenance",
        headers=h,
        json={
            "entry_date": f"{YEAR}-03-01",
            "category": "Ascenseur",
            "description": "Visite",
            "cost": 350,
        },
    )
    assert r.status_code == 201, r.text

    # 12) Coffre de documents : upload (multipart) → list → download → delete.
    r = await client.post(
        f"/api/v1/coproprietes/{cid}/documents",
        headers=h,
        files={"file": ("RCP.pdf", b"%PDF-1.4 reglement", "application/pdf")},
        data={"label": "Règlement de copropriété"},
    )
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    r = await client.get(f"/api/v1/coproprietes/{cid}/documents", headers=h)
    assert len(r.json()) == 1
    r = await client.get(f"/api/v1/documents/{doc_id}/download", headers=h)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    r = await client.delete(f"/api/v1/documents/{doc_id}", headers=h)
    assert r.status_code == 204
    r = await client.get(f"/api/v1/coproprietes/{cid}/documents", headers=h)
    assert r.json() == []


@pytest.mark.asyncio
async def test_syndic_isolation_other_manager_403(
    client: AsyncClient, gestionnaire_token, gp_token2
):
    """Une copropriété n'est pas visible/accessible par un autre périmètre."""
    h = auth(gestionnaire_token)
    r = await client.post("/api/v1/coproprietes", json={"name": "Privée"}, headers=h)
    cid = r.json()["id"]
    # Le GP d'une autre agence ne voit pas la copro et reçoit 403/404 sur le détail.
    r = await client.get(f"/api/v1/coproprietes/{cid}", headers=auth(gp_token2))
    assert r.status_code in (403, 404), r.text
    # Sa liste ne contient pas la copropriété.
    r = await client.get("/api/v1/coproprietes", headers=auth(gp_token2))
    assert all(c["id"] != cid for c in r.json())
