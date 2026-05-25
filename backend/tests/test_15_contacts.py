"""
Tests API — Contacts (carnet d'adresses prestataires).
Couvre : CRUD, recherche, favoris, isolation GP/mandataire, RBAC.
"""
import pytest
from tests.conftest import auth

CONTACT_PAYLOAD = {
    "last_name": "Dupont",
    "first_name": "Jean",
    "category": "plombier",
    "phone": "0601020304",
    "email": "jean.dupont@test.fr",
    "city": "Paris",
}


@pytest.mark.asyncio
class TestContactCRUD:
    async def test_gestionnaire_can_create_contact(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["last_name"] == "Dupont"
        assert data["category"] == "plombier"

    async def test_gp_can_create_contact(self, client, gp_token):
        resp = await client.post("/api/v1/contacts", headers=auth(gp_token), json={
            **CONTACT_PAYLOAD, "last_name": "Martin",
        })
        assert resp.status_code == 201
        assert resp.json()["last_name"] == "Martin"

    async def test_locataire_cannot_create_contact(self, client, locataire_token):
        resp = await client.post("/api/v1/contacts", headers=auth(locataire_token), json=CONTACT_PAYLOAD)
        assert resp.status_code == 403

    async def test_proprietaire_cannot_create_contact(self, client, proprietaire_token):
        resp = await client.post("/api/v1/contacts", headers=auth(proprietaire_token), json=CONTACT_PAYLOAD)
        assert resp.status_code == 403

    async def test_create_contact_missing_last_name(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            "category": "plombier",
        })
        assert resp.status_code == 422

    async def test_get_contact_by_id(self, client, gestionnaire_token):
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]
        resp = await client.get(f"/api/v1/contacts/{contact_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == contact_id

    async def test_update_contact(self, client, gestionnaire_token):
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=auth(gestionnaire_token),
            json={"city": "Lyon", "phone": "0699887766"},
        )
        assert resp.status_code == 200
        assert resp.json()["city"] == "Lyon"

    async def test_delete_contact(self, client, gestionnaire_token):
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/contacts/{contact_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 204

        get = await client.get(f"/api/v1/contacts/{contact_id}", headers=auth(gestionnaire_token))
        assert get.status_code == 404

    async def test_toggle_favorite(self, client, gestionnaire_token):
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]

        # Activer favori
        resp = await client.post(
            f"/api/v1/contacts/{contact_id}/toggle-favorite",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_favorite"] is True

        # Désactiver favori
        resp2 = await client.post(
            f"/api/v1/contacts/{contact_id}/toggle-favorite",
            headers=auth(gestionnaire_token),
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_favorite"] is False


@pytest.mark.asyncio
class TestContactSearch:
    async def test_list_contacts_returns_200(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/contacts", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_filter_by_category(self, client, gestionnaire_token):
        await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            **CONTACT_PAYLOAD, "last_name": "Elec", "category": "electricien",
        })
        resp = await client.get("/api/v1/contacts?category=electricien", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        for c in resp.json():
            assert c["category"] == "electricien"

    async def test_filter_favorites_only(self, client, gestionnaire_token):
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]
        await client.post(f"/api/v1/contacts/{contact_id}/toggle-favorite", headers=auth(gestionnaire_token))

        resp = await client.get("/api/v1/contacts?favorites_only=true", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        for c in resp.json():
            assert c["is_favorite"] is True

    async def test_search_by_name(self, client, gestionnaire_token):
        await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            **CONTACT_PAYLOAD, "last_name": "Moreau", "first_name": "Claire",
        })
        resp = await client.get("/api/v1/contacts?search=Moreau", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert any("Moreau" in c["last_name"] for c in resp.json())


@pytest.mark.asyncio
class TestContactIsolation:
    """GP et mandataire ne voient pas les contacts de l'autre."""

    async def test_gp_cannot_see_gestionnaire_contacts(self, client, gestionnaire_token, gp_token):
        # Mandataire crée un contact
        create = await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            **CONTACT_PAYLOAD, "last_name": "MandataireContact",
        })
        contact_id = create.json()["id"]

        # GP essaie de lire ce contact → 403
        resp = await client.get(f"/api/v1/contacts/{contact_id}", headers=auth(gp_token))
        assert resp.status_code == 403

    async def test_gestionnaire_cannot_see_gp_contacts(self, client, gp_token, gestionnaire_token):
        # GP crée un contact
        create = await client.post("/api/v1/contacts", headers=auth(gp_token), json={
            **CONTACT_PAYLOAD, "last_name": "GPContact",
        })
        contact_id = create.json()["id"]

        # Mandataire essaie de lire ce contact → 403
        resp = await client.get(f"/api/v1/contacts/{contact_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 403

    async def test_gp_list_excludes_gestionnaire_contacts(self, client, gestionnaire_token, gp_token):
        # Mandataire crée un contact unique
        await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            **CONTACT_PAYLOAD, "last_name": "ExcluDeGP",
        })
        # GP liste → ne doit pas voir le contact du mandataire
        resp = await client.get("/api/v1/contacts", headers=auth(gp_token))
        assert resp.status_code == 200
        assert not any(c["last_name"] == "ExcluDeGP" for c in resp.json())

    async def test_gestionnaire_list_excludes_gp_contacts(self, client, gp_token, gestionnaire_token):
        # GP crée un contact unique
        await client.post("/api/v1/contacts", headers=auth(gp_token), json={
            **CONTACT_PAYLOAD, "last_name": "ExcluDeMand",
        })
        # Mandataire liste → ne doit pas voir le contact du GP
        resp = await client.get("/api/v1/contacts", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert not any(c["last_name"] == "ExcluDeMand" for c in resp.json())

    async def test_gp_cannot_delete_other_gp_contact(self, client, gp_token, gp_token2):
        # GP1 crée un contact
        create = await client.post("/api/v1/contacts", headers=auth(gp_token), json=CONTACT_PAYLOAD)
        contact_id = create.json()["id"]

        # GP2 essaie de le supprimer → 403
        resp = await client.delete(f"/api/v1/contacts/{contact_id}", headers=auth(gp_token2))
        assert resp.status_code == 403

    async def test_admin_can_see_all_contacts(self, client, admin_token, gestionnaire_token, gp_token):
        # Mandataire et GP créent chacun un contact
        await client.post("/api/v1/contacts", headers=auth(gestionnaire_token), json={
            **CONTACT_PAYLOAD, "last_name": "AdminVoitMand",
        })
        await client.post("/api/v1/contacts", headers=auth(gp_token), json={
            **CONTACT_PAYLOAD, "last_name": "AdminVoitGP",
        })
        # Admin liste tout
        resp = await client.get("/api/v1/contacts", headers=auth(admin_token))
        assert resp.status_code == 200
        names = [c["last_name"] for c in resp.json()]
        assert "AdminVoitMand" in names
        assert "AdminVoitGP" in names
