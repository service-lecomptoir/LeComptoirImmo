"""
Tests API — Entretiens & Prestataires.
"""
import pytest
from datetime import date
from tests.conftest import auth


PRESTATAIRE_PAYLOAD = {
    "name": "Plomberie Dupont",
    "specialty": "plomberie",
    "phone": "0600000001",
    "email": "plomberie@dupont.fr",
}


async def _create_property(client, gestionnaire_token):
    resp = await client.post("/api/v1/properties", headers=auth(gestionnaire_token), json={
        "name": "Immeuble Entretien",
        "address": "1 Rue Entretien",
        "zip_code": "75000",
        "city": "Paris",
        "country": "France",
        "property_type": "appartement",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestPrestataireCRUD:
    async def test_gestionnaire_creates_prestataire(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/prestataires", headers=auth(gestionnaire_token), json=PRESTATAIRE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Plomberie Dupont"
        assert "id" in data

    async def test_locataire_cannot_create_prestataire(self, client, locataire_token):
        resp = await client.post("/api/v1/prestataires", headers=auth(locataire_token), json=PRESTATAIRE_PAYLOAD)
        assert resp.status_code == 403

    async def test_gestionnaire_lists_prestataires(self, client, gestionnaire_token):
        await client.post("/api/v1/prestataires", headers=auth(gestionnaire_token), json=PRESTATAIRE_PAYLOAD)
        resp = await client.get("/api/v1/prestataires", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_gestionnaire_updates_prestataire(self, client, gestionnaire_token):
        create_resp = await client.post("/api/v1/prestataires", headers=auth(gestionnaire_token), json=PRESTATAIRE_PAYLOAD)
        pid = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/prestataires/{pid}",
            headers=auth(gestionnaire_token),
            json={"phone": "0700000002"},
        )
        assert resp.status_code == 200
        assert resp.json()["phone"] == "0700000002"

    async def test_gestionnaire_deletes_prestataire(self, client, gestionnaire_token):
        create_resp = await client.post("/api/v1/prestataires", headers=auth(gestionnaire_token), json=PRESTATAIRE_PAYLOAD)
        pid = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/prestataires/{pid}", headers=auth(gestionnaire_token))
        assert del_resp.status_code == 204

    async def test_get_nonexistent_prestataire(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/prestataires/00000000-0000-0000-0000-000000000000",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestEntretienCRUD:
    async def test_gestionnaire_creates_entretien(self, client, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        resp = await client.post("/api/v1/entretiens", headers=auth(gestionnaire_token), json={
            "title": "Vérification chaudière",
            "type": "preventif",
            "status": "planifie",
            "frequency": "annuel",
            "scheduled_date": str(date.today()),
            "property_id": prop_id,
        })
        assert resp.status_code == 201
        assert "id" in resp.json()

    async def test_locataire_cannot_create_entretien(self, client, locataire_token, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        resp = await client.post("/api/v1/entretiens", headers=auth(locataire_token), json={
            "title": "Hack",
            "type": "preventif",
            "status": "planifie",
            "frequency": "unique",
            "scheduled_date": str(date.today()),
            "property_id": prop_id,
        })
        assert resp.status_code == 403

    async def test_gestionnaire_lists_entretiens(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/entretiens", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_gestionnaire_filters_by_status(self, client, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        await client.post("/api/v1/entretiens", headers=auth(gestionnaire_token), json={
            "title": "Planifié", "type": "preventif", "status": "planifie",
            "frequency": "unique", "scheduled_date": str(date.today()), "property_id": prop_id,
        })
        resp = await client.get("/api/v1/entretiens?status=planifie", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(e["status"] == "planifie" for e in items)

    async def test_gestionnaire_updates_entretien(self, client, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        create_resp = await client.post("/api/v1/entretiens", headers=auth(gestionnaire_token), json={
            "title": "Nettoyage toiture",
            "type": "preventif",
            "status": "planifie",
            "frequency": "annuel",
            "scheduled_date": str(date.today()),
            "property_id": prop_id,
        })
        eid = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/entretiens/{eid}",
            headers=auth(gestionnaire_token),
            json={"status": "en_cours"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "en_cours"

    async def test_gestionnaire_deletes_entretien(self, client, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        create_resp = await client.post("/api/v1/entretiens", headers=auth(gestionnaire_token), json={
            "title": "À supprimer",
            "type": "preventif",
            "status": "planifie",
            "frequency": "unique",
            "scheduled_date": str(date.today()),
            "property_id": prop_id,
        })
        eid = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/entretiens/{eid}", headers=auth(gestionnaire_token))
        assert del_resp.status_code == 204

    async def test_proprietaire_can_read_entretiens(self, client, proprietaire_token):
        resp = await client.get("/api/v1/entretiens", headers=auth(proprietaire_token))
        assert resp.status_code == 200

    async def test_locataire_cannot_read_entretiens(self, client, locataire_token):
        resp = await client.get("/api/v1/entretiens", headers=auth(locataire_token))
        assert resp.status_code == 403

    async def test_entretien_with_prestataire(self, client, gestionnaire_token):
        prop_id = await _create_property(client, gestionnaire_token)
        prest_resp = await client.post(
            "/api/v1/prestataires",
            headers=auth(gestionnaire_token),
            json={"name": "Électricité Martin"},
        )
        prest_id = prest_resp.json()["id"]

        resp = await client.post("/api/v1/entretiens", headers=auth(gestionnaire_token), json={
            "title": "Révision tableau électrique",
            "type": "preventif",
            "status": "planifie",
            "frequency": "annuel",
            "scheduled_date": str(date.today()),
            "property_id": prop_id,
            "prestataire_id": prest_id,
            "cost": 350.0,
        })
        assert resp.status_code == 201
