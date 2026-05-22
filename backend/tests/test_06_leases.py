"""
Tests API — Baux (Leases).
"""
import uuid
import pytest
from datetime import date
from tests.conftest import auth


async def _setup_lease_chain(db, gestionnaire_user):
    """Crée Property → Unit → Tenant → Lease et retourne les IDs."""
    from app.models.property import Property
    from app.models.unit import Unit
    from app.models.tenant import Tenant

    prop = Property(
        name="Immeuble Bail Test",
        address="5 Allée des Tests",
        zip_code="33000",
        city="Bordeaux",
        country="France",
        property_type="immeuble",
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()

    unit = Unit(
        property_id=prop.id,
        unit_ref="T2-03",
        unit_type="T2",
        area_sqm=48.5,
        floor=2,
        base_rent=750.00,
        charges_amount=80.00,
    )
    db.add(unit)
    await db.flush()

    tenant = Tenant(
        first_name="Marie",
        last_name="Dupont",
        email="marie.dupont@test.fr",
        phone="0600000001",
        created_by=gestionnaire_user.id,
    )
    db.add(tenant)
    await db.flush()

    return prop, unit, tenant


@pytest.mark.asyncio
class TestLeaseCreate:
    async def test_gestionnaire_creates_lease(self, client, gestionnaire_token, gestionnaire_user, db):
        prop, unit, tenant = await _setup_lease_chain(db, gestionnaire_user)

        resp = await client.post("/api/v1/leases", headers=auth(gestionnaire_token), json={
            "unit_id": str(unit.id),
            "tenant_id": str(tenant.id),
            "property_id": str(prop.id),
            "start_date": str(date.today()),
            "rent_amount": 750.00,
            "charges_amount": 80.00,
            "lease_type": "vide",
            "payment_method": "virement",
            "payment_day": 5,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["is_active"] is True
        assert data["rent_amount"] == 750.0

    async def test_locataire_cannot_create_lease(self, client, locataire_token, gestionnaire_user, db):
        prop, unit, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post("/api/v1/leases", headers=auth(locataire_token), json={
            "unit_id": str(unit.id),
            "tenant_id": str(tenant.id),
            "property_id": str(prop.id),
            "start_date": str(date.today()),
            "rent_amount": 750.00,
            "charges_amount": 80.00,
            "lease_type": "vide",
        })
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestLeaseRead:
    async def test_gestionnaire_lists_all_leases(self, client, gestionnaire_token, gestionnaire_user, db):
        prop, unit, tenant = await _setup_lease_chain(db, gestionnaire_user)
        # Créer un bail directement en DB
        from app.models.lease import Lease
        lease = Lease(
            unit_id=unit.id,
            tenant_id=tenant.id,
            property_id=prop.id,
            start_date=date.today(),
            rent_amount=750.00,
            charges_amount=80.00,
            lease_type="vide",
            payment_day=5,
            is_active=True,
        )
        db.add(lease)
        await db.flush()

        resp = await client.get("/api/v1/leases", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_locataire_only_sees_own_lease(self, client, locataire_token, locataire_user, gestionnaire_user, db):
        """Le locataire ne voit que son propre bail."""
        from app.models.property import Property
        from app.models.unit import Unit
        from app.models.tenant import Tenant
        from app.models.lease import Lease

        prop = Property(
            name="Prop Loc", address="1 Rue", zip_code="75000",
            city="Paris", country="France", property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        unit = Unit(
            property_id=prop.id, unit_ref="L1",
            unit_type="T2", base_rent=600.00, charges_amount=50.00,
        )
        db.add(unit)
        await db.flush()

        # Tenant lié au locataire_user
        tenant = Tenant(
            first_name="Jean", last_name="Loc",
            email="jean.loc@test.fr",
            user_id=locataire_user.id,
        )
        db.add(tenant)
        await db.flush()

        lease = Lease(
            unit_id=unit.id, tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(), rent_amount=600.00, charges_amount=50.00,
            lease_type="vide", payment_day=1, is_active=True,
        )
        db.add(lease)
        await db.flush()

        resp = await client.get("/api/v1/leases", headers=auth(locataire_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == str(lease.id)


@pytest.mark.asyncio
class TestLeaseTerminate:
    async def test_gestionnaire_terminates_lease(self, client, gestionnaire_token, gestionnaire_user, db):
        from app.models.lease import Lease
        prop, unit, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            unit_id=unit.id, tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(), rent_amount=750.00, charges_amount=80.00,
            lease_type="vide", payment_day=5, is_active=True,
        )
        db.add(lease)
        await db.flush()

        resp = await client.post(
            f"/api/v1/leases/{lease.id}/terminate",
            headers=auth(gestionnaire_token),
            json={"end_date": str(date.today()), "termination_reason": "Fin de contrat"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
