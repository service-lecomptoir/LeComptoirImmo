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
    async def test_gestionnaire_creates_lease(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)

        resp = await client.post(
            "/api/v1/leases",
            headers=auth(gestionnaire_token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(date.today()),
                "rent_amount": 750.00,
                "charges_amount": 80.00,
                "lease_type": "vide",
                "payment_method": "virement",
                "payment_day": 5,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["is_active"] is True
        assert data["rent_amount"] == 750.0

    async def test_locataire_cannot_create_lease(
        self, client, locataire_token, gestionnaire_user, db
    ):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post(
            "/api/v1/leases",
            headers=auth(locataire_token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(date.today()),
                "rent_amount": 750.00,
                "charges_amount": 80.00,
                "lease_type": "vide",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestLeaseRead:
    async def test_gestionnaire_lists_all_leases(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
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

    async def test_locataire_only_sees_own_lease(
        self, client, locataire_token, locataire_user, gestionnaire_user, db
    ):
        """Le locataire ne voit que son propre bail."""
        from app.models.lease import Lease
        from app.models.property import Property
        from app.models.tenant import Tenant

        prop = Property(
            name="Prop Loc",
            address="1 Rue",
            zip_code="75000",
            city="Paris",
            country="France",
            property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        # Tenant lié au locataire_user
        tenant = Tenant(
            first_name="Jean",
            last_name="Loc",
            email="jean.loc@test.fr",
            user_id=locataire_user.id,
        )
        db.add(tenant)
        await db.flush()

        lease = Lease(
            tenant_id=tenant.id,
            property_id=prop.id,
            start_date=date.today(),
            rent_amount=600.00,
            charges_amount=50.00,
            lease_type="vide",
            payment_day=1,
            is_active=True,
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
    async def test_gestionnaire_terminates_lease(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from app.models.lease import Lease

        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
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
            tenant_id=tenant.id,
            property_id=prop.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            rent_amount=750.00,
            charges_amount=80.00,
            lease_type="vide",
            payment_day=5,
            is_active=True,
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
                select(func.count())
                .select_from(RentRevision)
                .where(RentRevision.lease_id == lease_id)
            )
        ).scalar_one()

    async def test_bail_futur_modif_directe_sans_revision(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from datetime import timedelta

        from app.models.lease import Lease

        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        lease = Lease(
            tenant_id=tenant.id,
            property_id=prop.id,
            start_date=date.today() + timedelta(days=30),  # futur
            rent_amount=750.00,
            charges_amount=80.00,
            lease_type="vide",
            payment_day=5,
            is_active=True,
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
            tenant_id=tenant.id,
            property_id=prop.id,
            start_date=date.today(),  # commencé
            rent_amount=750.00,
            charges_amount=80.00,
            lease_type="vide",
            payment_day=5,
            is_active=True,
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


@pytest.mark.asyncio
class TestLeaseCreationGeneration:
    """Régression : la création d'un bail ne doit JAMAIS générer un loyer « fantôme »
    sans avis, ni anticiper un loyer pour un mois à venir (bail à début futur)."""

    @staticmethod
    def _future_first_of_month(months_ahead: int = 2):
        from datetime import date

        t = date.today()
        m = t.month + months_ahead
        y = t.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        return date(y, m, 1)

    async def _counts(self, db, lease_id):
        from sqlalchemy import func, select

        from app.models.avis_echeance import AvisEcheance
        from app.models.payment import Payment

        n_pay = (
            await db.execute(
                select(func.count()).select_from(Payment).where(Payment.lease_id == lease_id)
            )
        ).scalar_one()
        n_avis = (
            await db.execute(
                select(func.count())
                .select_from(AvisEcheance)
                .where(AvisEcheance.lease_id == lease_id)
            )
        ).scalar_one()
        return n_pay, n_avis

    async def test_future_lease_no_payment_no_avis(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post(
            "/api/v1/leases",
            headers=auth(gestionnaire_token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(self._future_first_of_month(2)),
                "rent_amount": 850.00,
                "charges_amount": 100.00,
                "lease_type": "vide",
                "payment_day": 1,
            },
        )
        assert resp.status_code == 201, resp.text
        n_pay, n_avis = await self._counts(db, resp.json()["id"])
        assert n_pay == 0, "un bail à début futur ne doit pas générer de loyer"
        assert n_avis == 0

    async def test_current_lease_generates_avis_and_payment(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post(
            "/api/v1/leases",
            headers=auth(gestionnaire_token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(date.today().replace(day=1)),
                "rent_amount": 700.00,
                "charges_amount": 50.00,
                "lease_type": "vide",
                "payment_day": 1,
            },
        )
        assert resp.status_code == 201, resp.text
        n_pay, n_avis = await self._counts(db, resp.json()["id"])
        # Bail commençant ce mois-ci : avis ET loyer générés ensemble.
        assert n_pay == 1
        assert n_avis == 1


@pytest.mark.asyncio
class TestRentRevisionAudit:
    """Traçabilité (audit) des réévaluations de loyer + purge cohérente sur bail futur."""

    async def _create_lease(self, client, token, db, gestionnaire_user, start: date):
        prop, tenant = await _setup_lease_chain(db, gestionnaire_user)
        resp = await client.post(
            "/api/v1/leases",
            headers=auth(token),
            json={
                "tenant_id": str(tenant.id),
                "property_id": str(prop.id),
                "start_date": str(start),
                "rent_amount": 1000.00,
                "charges_amount": 150.00,
                "lease_type": "vide",
                "payment_method": "virement",
                "payment_day": 5,
            },
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    async def test_rent_change_creates_revision_and_audit(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from sqlalchemy import select

        from app.models.audit_log import AuditLog

        # Bail déjà commencé → la modification programme une réévaluation datée.
        lease_id = await self._create_lease(
            client, gestionnaire_token, db, gestionnaire_user, date(2026, 1, 1)
        )
        resp = await client.put(
            f"/api/v1/leases/{lease_id}",
            headers=auth(gestionnaire_token),
            json={"rent_amount": 1050.00},
        )
        assert resp.status_code == 200, resp.text

        revs = (
            await client.get(
                f"/api/v1/leases/{lease_id}/rent-revisions", headers=auth(gestionnaire_token)
            )
        ).json()
        assert any(r["kind"] == "rent" and r["amount"] == 1050.0 for r in revs)

        logged = (
            (await db.execute(select(AuditLog).where(AuditLog.action == "revision.schedule")))
            .scalars()
            .all()
        )
        assert len(logged) >= 1
        assert logged[0].user_email == gestionnaire_user.email

    async def test_delete_revision_is_audited(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from sqlalchemy import select

        from app.models.audit_log import AuditLog

        lease_id = await self._create_lease(
            client, gestionnaire_token, db, gestionnaire_user, date(2026, 1, 1)
        )
        await client.put(
            f"/api/v1/leases/{lease_id}",
            headers=auth(gestionnaire_token),
            json={"rent_amount": 1050.00},
        )
        revs = (
            await client.get(
                f"/api/v1/leases/{lease_id}/rent-revisions", headers=auth(gestionnaire_token)
            )
        ).json()
        rev_id = revs[0]["id"]
        d = await client.delete(
            f"/api/v1/leases/{lease_id}/rent-revisions/{rev_id}", headers=auth(gestionnaire_token)
        )
        assert d.status_code == 204, d.text

        logged = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "revision.delete", AuditLog.entity_id == rev_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(logged) == 1

    async def test_future_lease_correction_keeps_legitimate_revision(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        """Corriger un bail NON débuté ne doit PLUS effacer une réévaluation future légitime."""
        from app.models.rent_revision import RentRevision
        from app.schemas.lease import LeaseUpdate
        from app.services.lease_service import LeaseService
        from app.services.rent_revision_service import RentRevisionService

        # Bail commençant dans le futur.
        lease_id = await self._create_lease(
            client, gestionnaire_token, db, gestionnaire_user, date(2027, 1, 1)
        )
        lease = await LeaseService.get_by_id(db, uuid.UUID(lease_id), load_relations=True)
        # Réévaluation future LÉGITIME (postérieure au début, montant différent).
        await RentRevisionService.schedule(
            db,
            lease,
            kind="rent",
            new_amount=1100.00,
            effective_date=date(2027, 6, 1),
            source="manuel",
        )
        await db.commit()

        # Correction de la base (le bail n'a pas commencé) : 1000 -> 1000 inchangé n'aurait
        # rien fait ; on change pour 1020 afin de déclencher la branche de correction.
        await LeaseService.update(
            db, uuid.UUID(lease_id), LeaseUpdate(rent_amount=1020.00), actor_email="x@test.fr"
        )
        await db.commit()

        from sqlalchemy import select

        remaining = (
            (
                await db.execute(
                    select(RentRevision).where(RentRevision.lease_id == uuid.UUID(lease_id))
                )
            )
            .scalars()
            .all()
        )
        # La réévaluation future légitime (1100 au 01/06/2027) est conservée.
        assert any(
            float(r.amount) == 1100.0 and r.effective_date == date(2027, 6, 1) for r in remaining
        )
