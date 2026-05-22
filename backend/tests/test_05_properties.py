"""
Tests API — Biens immobiliers.
"""
import pytest
from tests.conftest import auth

PROPERTY_PAYLOAD = {
    "name": "Résidence Test",
    "address": "10 Rue des Tests",
    "zip_code": "75001",
    "city": "Paris",
    "country": "France",
    "property_type": "immeuble",
}


async def _create_property(client, token) -> dict:
    resp = await client.post("/api/v1/properties", headers=auth(token), json=PROPERTY_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
class TestPropertyCRUD:
    async def test_gestionnaire_creates_property(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/properties", headers=auth(gestionnaire_token), json=PROPERTY_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Résidence Test"
        assert data["city"] == "Paris"

    async def test_locataire_cannot_create_property(self, client, locataire_token):
        resp = await client.post("/api/v1/properties", headers=auth(locataire_token), json=PROPERTY_PAYLOAD)
        assert resp.status_code == 403

    async def test_proprietaire_cannot_create_property(self, client, proprietaire_token):
        resp = await client.post("/api/v1/properties", headers=auth(proprietaire_token), json=PROPERTY_PAYLOAD)
        assert resp.status_code == 403

    async def test_gestionnaire_lists_all_properties(self, client, gestionnaire_token):
        await _create_property(client, gestionnaire_token)
        resp = await client.get("/api/v1/properties", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_locataire_gets_empty_list(self, client, locataire_token):
        resp = await client.get("/api/v1/properties", headers=auth(locataire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_gestionnaire_gets_property_detail(self, client, gestionnaire_token):
        created = await _create_property(client, gestionnaire_token)
        prop_id = created["id"]

        resp = await client.get(f"/api/v1/properties/{prop_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == prop_id

    async def test_get_nonexistent_property(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/properties/00000000-0000-0000-0000-000000000000",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 404

    async def test_gestionnaire_updates_property(self, client, gestionnaire_token):
        created = await _create_property(client, gestionnaire_token)
        resp = await client.put(
            f"/api/v1/properties/{created['id']}",
            headers=auth(gestionnaire_token),
            json={"name": "Résidence Modifiée"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Résidence Modifiée"

    async def test_proprietaire_only_sees_own_properties(
        self, client, gestionnaire_token, proprietaire_token, proprietaire_user, db
    ):
        """Le propriétaire ne voit que les biens qui lui appartiennent."""
        from app.models.property import Property
        # Créer un bien lié au propriétaire
        own_prop = Property(
            name="Mon Bien",
            address="1 Rue Proprio",
            zip_code="69001",
            city="Lyon",
            country="France",
            property_type="appartement",
            owner_user_id=proprietaire_user.id,
        )
        db.add(own_prop)
        await db.flush()

        # Créer un bien d'un autre propriétaire
        other_prop = await _create_property(client, gestionnaire_token)

        resp = await client.get("/api/v1/properties", headers=auth(proprietaire_token))
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert str(own_prop.id) in ids
        assert other_prop["id"] not in ids


@pytest.mark.asyncio
class TestPropertyOccupancy:
    async def test_occupancy_endpoint(self, client, gestionnaire_token):
        created = await _create_property(client, gestionnaire_token)
        resp = await client.get(
            f"/api/v1/properties/{created['id']}/occupancy",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "occupied" in data
        assert "rate" in data
        assert data["total"] == 0
        assert data["rate"] == 0.0
