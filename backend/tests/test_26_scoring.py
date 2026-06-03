"""Tests — Scoring de qualité de payeur des locataires."""
import pytest
from tests.conftest import auth


async def _chain(client, token, income=3000.0, rent=800.0):
    prop = await client.post("/api/v1/properties", headers=auth(token), json={
        "name": "Bien Scoring", "address": "1 Rue Score", "zip_code": "75000",
        "city": "Paris", "country": "France", "property_type": "appartement",
    })
    assert prop.status_code == 201, prop.text
    prop_id = prop.json()["id"]
    tenant = await client.post("/api/v1/tenants", headers=auth(token), json={
        "first_name": "Score", "last_name": "Test", "email": "score@test.fr",
        "monthly_income": income,
    })
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]
    lease = await client.post("/api/v1/leases", headers=auth(token), json={
        "tenant_id": tenant_id, "property_id": prop_id, "start_date": "2026-01-01",
        "rent_amount": rent, "charges_amount": 0.0, "lease_type": "vide",
    })
    assert lease.status_code == 201, lease.text
    return tenant_id, lease.json()["id"]


@pytest.mark.asyncio
class TestScoring:
    async def test_list_and_detail(self, client, gestionnaire_token):
        tenant_id, _ = await _chain(client, gestionnaire_token)
        lst = await client.get("/api/v1/scoring", headers=auth(gestionnaire_token))
        assert lst.status_code == 200, lst.text
        row = next((r for r in lst.json()["items"] if r["tenant_id"] == tenant_id), None)
        assert row is not None
        assert 0 <= row["score"] <= 100
        assert row["grade"] in ("A", "B", "C", "D", "E")

        det = await client.get(f"/api/v1/scoring/{tenant_id}", headers=auth(gestionnaire_token))
        assert det.status_code == 200, det.text
        data = det.json()
        assert {"score", "grade", "strategy", "factors", "stats"} <= set(data)
        assert any(f["key"] == "ponctualite" for f in data["factors"])

    async def test_relationship_event_lowers_relation_score(self, client, gestionnaire_token):
        tenant_id, lease_id = await _chain(client, gestionnaire_token)
        before = (await client.get(f"/api/v1/scoring/{tenant_id}", headers=auth(gestionnaire_token))).json()
        rel_before = next(f["score"] for f in before["factors"] if f["key"] == "relation")

        ev = await client.post(f"/api/v1/leases/{lease_id}/relationship-events",
                               headers=auth(gestionnaire_token),
                               json={"kind": "litige", "note": "Contentieux loyer"})
        assert ev.status_code == 201, ev.text
        assert any(e["kind"] == "litige" for e in ev.json())

        after = (await client.get(f"/api/v1/scoring/{tenant_id}", headers=auth(gestionnaire_token))).json()
        rel_after = next(f["score"] for f in after["factors"] if f["key"] == "relation")
        assert rel_after < rel_before  # un litige dégrade le sous-score relation

    async def test_event_kinds_listed(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/scoring/event-kinds", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        kinds = {k["kind"] for k in resp.json()}
        assert {"litige", "paiement_spontane", "refus_paiement"} <= kinds

    async def test_locataire_cannot_access_scoring(self, client, locataire_token):
        assert (await client.get("/api/v1/scoring", headers=auth(locataire_token))).status_code == 403

    async def test_invalid_event_kind_rejected(self, client, gestionnaire_token):
        _, lease_id = await _chain(client, gestionnaire_token)
        resp = await client.post(f"/api/v1/leases/{lease_id}/relationship-events",
                                 headers=auth(gestionnaire_token), json={"kind": "n_existe_pas"})
        assert resp.status_code == 400
