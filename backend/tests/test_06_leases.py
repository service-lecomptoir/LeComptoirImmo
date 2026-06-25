"""
Tests API — Baux (Leases).
"""
import uuid
from datetime import date

import pytest

from tests.conftest import auth


async def _setup_lease_chain(db, gestionnaire_user):
    """Crée Property → Tenant et retourne (prop, tenant)."""
    from app.models.property import Property
    from app.models.tenant import Tenant

    prop = Property(
        name="Immeuble Bail Test",
        address="5 Allée des Tests",
        zip_code="33000",
        city="Bordeaux",
        country="France",
        property_type="appartement",
        area_sqm=48.5,
        floor=2,
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
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

    return prop, tenant


@pytest.mark.asyncio
class TestLeaseCreate:
    async def test_gestionnaire_creates_lease(self, client, gestionnaire_token, gestionnaire_user, db):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)

        resp = await client.post("/api/v1/leases", headers=auth(gestionnaire_token), json={
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
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post("/api/v1/leases", headers=auth(locataire_token), json={
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
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        # Créer un bail directement en DB
        from app.models.lease import Lease
        lease = Lease(
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
        from app.models.lease import Lease
        from app.models.property import Property
        from app.models.tenant import Tenant

        prop = Property(
            name="Prop Loc", address="1 Rue", zip_code="75000",
            city="Paris", country="France", property_type="appartement",
        )
        db.add(prop)
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
            tenant_id=tenant.id, property_id=prop.id,
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
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
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


@pytest.mark.asyncio
class TestLeaseUpdateStartDate:
    async def test_gestionnaire_modifie_date_entree(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from datetime import timedelta

        from app.models.lease import Lease
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(), rent_amount=750.00, charges_amount=80.00,
            lease_type="vide", payment_day=5, is_active=True,
        )
        db.add(lease)
        await db.flush()
        await db.commit()

        nouvelle_date = date.today() + timedelta(days=20)
        resp = await client.put(
            f"/api/v1/leases/{lease.id}",
            headers=auth(gestionnaire_token),
            json={"start_date": str(nouvelle_date)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["start_date"] == str(nouvelle_date)

    async def test_date_entree_apres_fin_refusee(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from datetime import timedelta

        from app.models.lease import Lease
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            rent_amount=750.00, charges_amount=80.00,
            lease_type="vide", payment_day=5, is_active=True,
        )
        db.add(lease)
        await db.flush()
        await db.commit()

        # Entrée après la fin => refus (cohérence des dates).
        resp = await client.put(
            f"/api/v1/leases/{lease.id}",
            headers=auth(gestionnaire_token),
            json={"start_date": str(date.today() + timedelta(days=60))},
        )
        assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
class TestLeaseFutureRentCorrection:
    """Bail futur (pas encore commencé) : modifier loyer/charges = correction directe
    (pas de révision datée, pas d'historique). Bail commencé : révision datée."""

    async def _count_revisions(self, db, lease_id):
        from sqlalchemy import func, select

        from app.models.rent_revision import RentRevision

        return (
            await db.execute(
                select(func.count()).select_from(RentRevision).where(
                    RentRevision.lease_id == lease_id
                )
            )
        ).scalar_one()

    async def test_bail_futur_modif_directe_sans_revision(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from datetime import timedelta

        from app.models.lease import Lease
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today() + timedelta(days=30),  # futur
            rent_amount=750.00, charges_amount=80.00,
            lease_type="vide", payment_day=5, is_active=True,
        )
        db.add(lease)
        await db.flush()
        await db.commit()

        resp = await client.put(
            f"/api/v1/leases/{lease.id}",
            headers=auth(gestionnaire_token),
            json={"rent_amount": 800.00, "charges_amount": 90.00},
        )
        assert resp.status_code == 200, resp.text
        # Montants appliqués directement, aucune révision créée.
        assert resp.json()["rent_amount"] == 800.0
        assert resp.json()["charges_amount"] == 90.0
        assert await self._count_revisions(db, lease.id) == 0

    async def test_bail_commence_cree_une_revision(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from app.models.lease import Lease
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id, property_id=prop.id,
            start_date=date.today(),  # commencé
            rent_amount=750.00, charges_amount=80.00,
            lease_type="vide", payment_day=5, is_active=True,
        )
        db.add(lease)
        await db.flush()
        await db.commit()

        resp = await client.put(
            f"/api/v1/leases/{lease.id}",
            headers=auth(gestionnaire_token),
            json={"rent_amount": 800.00},
        )
        assert resp.status_code == 200, resp.text
        # Une révision datée est créée (l'historique est conservé).
        assert await self._count_revisions(db, lease.id) >= 1
