"""
Tests API — Avis d'échéances.
"""
import pytest
from datetime import date
from tests.conftest import auth


async def _setup_active_lease(db):
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.lease import Lease

    prop = Property(
        name="Prop Avis", address="9 Rue", zip_code="13001",
        city="Marseille", country="France", property_type="appartement",
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="Luc", last_name="Avis",
        email="luc.avis@test.fr",
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id, property_id=prop.id,
        start_date=date.today(), rent_amount=700.00, charges_amount=90.00,
        lease_type="vide", payment_day=1, is_active=True,
    )
    db.add(lease)
    await db.flush()
    return lease


@pytest.mark.asyncio
class TestAvisGeneration:
    async def test_gestionnaire_generates_avis(self, client, gestionnaire_token, db):
        lease = await _setup_active_lease(db)

        resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id),
            "period_year": 2026,
            "period_month": 7,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["period_year"] == 2026
        assert data["period_month"] == 7
        assert data["amount_rent"] == 700.0
        assert data["status"] == "brouillon"

    async def test_no_duplicate_avis(self, client, gestionnaire_token, db):
        """Deux générations pour le même bail/période → 409 Conflict."""
        lease = await _setup_active_lease(db)

        await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id), "period_year": 2026, "period_month": 8,
        })
        resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id), "period_year": 2026, "period_month": 8,
        })
        assert resp.status_code == 409

    async def test_locataire_cannot_generate_avis(self, client, locataire_token, db):
        lease = await _setup_active_lease(db)
        resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(locataire_token), json={
            "lease_id": str(lease.id), "period_year": 2026, "period_month": 9,
        })
        assert resp.status_code == 403

    async def test_gestionnaire_generates_monthly_bulk(self, client, gestionnaire_token, db):
        await _setup_active_lease(db)
        resp = await client.post("/api/v1/avis-echeances/generate-monthly", headers=auth(gestionnaire_token), json={
            "period_year": 2026, "period_month": 10,
        })
        assert resp.status_code == 200
        assert "generated" in resp.json()


@pytest.mark.asyncio
class TestAvisWorkflow:
    async def test_mark_sent_then_acquitte(self, client, gestionnaire_token, db):
        lease = await _setup_active_lease(db)

        create_resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id), "period_year": 2026, "period_month": 11,
        })
        avis_id = create_resp.json()["id"]

        # Marquer comme envoyé
        sent_resp = await client.post(f"/api/v1/avis-echeances/{avis_id}/send", headers=auth(gestionnaire_token))
        assert sent_resp.status_code == 200
        assert sent_resp.json()["status"] == "envoye"
        assert sent_resp.json()["sent_at"] is not None

        # Marquer comme acquitté
        acq_resp = await client.post(f"/api/v1/avis-echeances/{avis_id}/acquitter", headers=auth(gestionnaire_token))
        assert acq_resp.status_code == 200
        assert acq_resp.json()["status"] == "acquitte"

    async def test_delete_draft_only(self, client, gestionnaire_token, db):
        lease = await _setup_active_lease(db)

        create_resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id), "period_year": 2026, "period_month": 12,
        })
        avis_id = create_resp.json()["id"]

        # Supprimer le brouillon → OK
        del_resp = await client.delete(f"/api/v1/avis-echeances/{avis_id}", headers=auth(gestionnaire_token))
        assert del_resp.status_code == 204

    async def test_cannot_delete_sent_avis(self, client, gestionnaire_token, db):
        lease = await _setup_active_lease(db)

        create_resp = await client.post("/api/v1/avis-echeances/generate", headers=auth(gestionnaire_token), json={
            "lease_id": str(lease.id), "period_year": 2027, "period_month": 1,
        })
        avis_id = create_resp.json()["id"]

        # Marquer envoyé
        await client.post(f"/api/v1/avis-echeances/{avis_id}/send", headers=auth(gestionnaire_token))

        # Tenter de supprimer → 400
        del_resp = await client.delete(f"/api/v1/avis-echeances/{avis_id}", headers=auth(gestionnaire_token))
        assert del_resp.status_code == 400


@pytest.mark.asyncio
class TestAvisAccessControl:
    async def test_locataire_only_sees_own_avis(self, client, locataire_token, locataire_user, gestionnaire_token, db):
        from app.models.property import Property
        from app.models.tenant import Tenant
        from app.models.lease import Lease
        from app.models.avis_echeance import AvisEcheance
        from datetime import date

        prop = Property(
            name="Prop Loc Avis", address="7 Rue", zip_code="75007",
            city="Paris", country="France", property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        tenant = Tenant(
            first_name="Loc", last_name="Avis2",
            email="loc.avis2@test.fr",
            user_id=locataire_user.id,
        )
        db.add(tenant)
        await db.flush()

        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(), rent_amount=900.00, charges_amount=100.00,
            lease_type="vide", payment_day=1, is_active=True,
        )
        db.add(lease)
        await db.flush()

        avis = AvisEcheance(
            lease_id=lease.id,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
            due_date=date.today(),
            amount_rent=900.00,
            amount_charges=100.00,
            amount_total=1000.00,
            status="brouillon",
        )
        db.add(avis)
        await db.flush()

        resp = await client.get("/api/v1/avis-echeances", headers=auth(locataire_token))
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        assert str(avis.id) in ids
