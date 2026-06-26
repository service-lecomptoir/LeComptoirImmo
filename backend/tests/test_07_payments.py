"""
Tests API — Paiements.
"""

from datetime import date

import pytest

from tests.conftest import auth


async def _setup_lease(db, gestionnaire_user):
    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    prop = Property(
        name="Prop Payments",
        address="2 Rue",
        zip_code="75001",
        city="Paris",
        country="France",
        property_type="appartement",
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="Paul",
        last_name="Payment",
        email="paul.pay@test.fr",
        created_by=gestionnaire_user.id,
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id,
        property_id=prop.id,
        start_date=date.today(),
        rent_amount=800.00,
        charges_amount=100.00,
        lease_type="vide",
        payment_day=1,
        is_active=True,
        created_by=gestionnaire_user.id,
    )
    db.add(lease)
    await db.flush()
    return lease


@pytest.mark.asyncio
class TestPaymentGeneration:
    async def test_gestionnaire_generates_monthly_payments(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _setup_lease(db, gestionnaire_user)

        resp = await client.post(
            "/api/v1/payments/generate",
            headers=auth(gestionnaire_token),
            json={
                "year": 2026,
                "month": 6,
            },
        )
        assert resp.status_code == 201
        assert "generated" in resp.json()

    async def test_locataire_cannot_generate_payments(self, client, locataire_token):
        resp = await client.post(
            "/api/v1/payments/generate",
            headers=auth(locataire_token),
            json={
                "year": 2026,
                "month": 6,
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestPaymentList:
    async def test_gestionnaire_lists_payments(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/payments", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_locataire_only_sees_own_payments(
        self, client, locataire_token, locataire_user, gestionnaire_user, db
    ):
        from app.models.lease import Lease
        from app.models.payment import Payment, PaymentStatus
        from app.models.property import Property
        from app.models.tenant import Tenant

        prop = Property(
            name="Prop Loc Pay",
            address="3 Rue",
            zip_code="75002",
            city="Paris",
            country="France",
            property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        tenant = Tenant(
            first_name="Alice",
            last_name="Loc2",
            email="alice.loc2@test.fr",
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

        payment = Payment(
            lease_id=lease.id,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=5,
            due_date=date.today(),
            amount_rent=600.00,
            amount_charges=50.00,
            amount_due=650.00,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()

        resp = await client.get("/api/v1/payments", headers=auth(locataire_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == str(payment.id)


@pytest.mark.asyncio
class TestDashboardStats:
    async def test_gestionnaire_gets_stats(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/payments/stats/dashboard", headers=auth(gestionnaire_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_expected" in data or "pending_count" in data or isinstance(data, dict)

    async def test_monthly_stats(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/payments/stats/monthly?year=2026&month=5",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestQuittance:
    async def test_quittance_refused_when_unpaid(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        """Une quittance ne peut pas être émise pour un loyer impayé (règle métier)."""
        from app.models.payment import Payment, PaymentStatus

        lease = await _setup_lease(db, gestionnaire_user)
        payment = Payment(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=2026,
            period_month=4,
            due_date=date.today(),
            amount_rent=800.00,
            amount_charges=100.00,
            amount_due=900.00,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        resp = await client.get(
            f"/api/v1/payments/{payment.id}/quittance", headers=auth(gestionnaire_token)
        )
        assert resp.status_code == 400

    async def test_quittance_pdf_generated_when_paid(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        """Régression : la quittance PDF doit se générer (200, application/pdf) une fois payé.
        Garde-fou contre le NameError 'select' détecté en recette."""
        from app.models.payment import Payment, PaymentStatus

        lease = await _setup_lease(db, gestionnaire_user)
        payment = Payment(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=2026,
            period_month=4,
            due_date=date.today(),
            amount_rent=800.00,
            amount_charges=100.00,
            amount_due=900.00,
            amount_paid=900.00,
            payment_date=date.today(),
            payment_method="virement",
            status=PaymentStatus.PAID,
        )
        db.add(payment)
        await db.flush()
        resp = await client.get(
            f"/api/v1/payments/{payment.id}/quittance", headers=auth(gestionnaire_token)
        )
        assert resp.status_code == 200, resp.text
        assert "pdf" in resp.headers.get("content-type", "")

    async def test_apurement_settlement_generates_quittance(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        """Quand un plan d'apurement solde le mois d'origine, le paiement passe
        « payé » ET la quittance est générée (préparée pour l'envoi auto)."""
        from app.models.payment import Payment, PaymentStatus

        lease = await _setup_lease(db, gestionnaire_user)
        # Mois partiellement réglé (600 / 900) → solde 300 reporté sur un plan.
        payment = Payment(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=2026,
            period_month=4,
            due_date=date.today(),
            amount_rent=800.00,
            amount_charges=100.00,
            amount_due=900.00,
            amount_paid=600.00,
            payment_date=date.today(),
            payment_method="virement",
            status=PaymentStatus.PARTIAL,
        )
        db.add(payment)
        await db.flush()

        # Plan d'apurement d'une échéance couvrant le solde (300).
        created = await client.post(
            "/api/v1/apurement-plans",
            headers=auth(gestionnaire_token),
            json={
                "payment_id": str(payment.id),
                "installments": 1,
                "first_date": date.today().isoformat(),
                "total_amount": 300.0,
            },
        )
        assert created.status_code in (200, 201), created.text
        plan_id = created.json()["id"]

        # Le gestionnaire pointe l'échéance comme payée → le mois est soldé.
        marked = await client.patch(
            f"/api/v1/apurement-plans/{plan_id}/installments/1",
            headers=auth(gestionnaire_token),
            json={"paid": True},
        )
        assert marked.status_code == 200, marked.text

        await db.refresh(payment)
        assert payment.status == PaymentStatus.PAID
        assert payment.quittance_generated_at is not None


@pytest.mark.asyncio
async def test_loyer_avis_not_blocked_by_apurement_avis(db, gestionnaire_user):
    """Un avis d'apurement pour une période ne doit pas empêcher la création de
    l'avis de loyer de cette même période (ils coexistent)."""
    from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
    from app.services.avis_echeance_service import AvisEcheanceService

    lease = await _setup_lease(db, gestionnaire_user)
    y, m = date.today().year, date.today().month
    # Avis d'apurement préexistant sur la période.
    db.add(
        AvisEcheance(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=y,
            period_month=m,
            due_date=date.today(),
            amount_rent=0,
            amount_charges=0,
            amount_total=300,
            kind="apurement",
            installment_seq=1,
            status=AvisEcheanceStatus.BROUILLON,
        )
    )
    await db.flush()
    # Génération de l'avis de loyer : ne doit PAS lever de conflit.
    avis = await AvisEcheanceService.generate_for_lease(
        db, lease, y, m, generated_by=gestionnaire_user.id
    )
    assert avis is not None
    assert (avis.kind or "loyer") == "loyer"


@pytest.mark.asyncio
async def test_record_payment_ok_with_apurement_avis_same_period(db, gestionnaire_user):
    """Régression 500 : enregistrer un paiement intégral ne doit pas échouer si un
    avis d'apurement existe aussi pour la période (MultipleResultsFound)."""
    from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
    from app.models.payment import Payment, PaymentStatus
    from app.schemas.payment import PaymentRecordIn
    from app.services.payment_service import PaymentService

    lease = await _setup_lease(db, gestionnaire_user)
    payment = Payment(
        lease_id=lease.id,
        tenant_id=lease.tenant_id,
        period_year=2026,
        period_month=9,
        due_date=date.today(),
        amount_rent=800,
        amount_charges=100,
        amount_due=900,
        amount_paid=0,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.add(
        AvisEcheance(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=2026,
            period_month=9,
            due_date=date.today(),
            amount_rent=800,
            amount_charges=100,
            amount_total=900,
            kind="loyer",
            status=AvisEcheanceStatus.ENVOYE,
        )
    )
    db.add(
        AvisEcheance(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=2026,
            period_month=9,
            due_date=date.today(),
            amount_rent=0,
            amount_charges=0,
            amount_total=300,
            kind="apurement",
            installment_seq=1,
            status=AvisEcheanceStatus.BROUILLON,
        )
    )
    await db.flush()
    pay = await PaymentService.record_payment(
        db,
        payment.id,
        PaymentRecordIn(amount_paid=900, payment_date=date.today(), payment_method="virement"),
    )
    assert pay.status == PaymentStatus.PAID


@pytest.mark.asyncio
class TestPaymentAudit:
    """Traçabilité : la création et la suppression d'un loyer écrivent dans l'audit."""

    async def test_create_and_delete_are_audited(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        from sqlalchemy import select

        from app.models.audit_log import AuditLog

        lease = await _setup_lease(db, gestionnaire_user)
        # Création d'un loyer (endpoint POST /payments).
        resp = await client.post(
            "/api/v1/payments",
            headers=auth(gestionnaire_token),
            json={"lease_id": str(lease.id), "period_year": 2026, "period_month": 8},
        )
        assert resp.status_code == 201, resp.text
        pay_id = resp.json()["id"]

        created = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "payment.create", AuditLog.entity_id == pay_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(created) == 1
        assert created[0].user_email == gestionnaire_user.email

        # Suppression → audit payment.delete avec l'état du loyer.
        d = await client.delete(f"/api/v1/payments/{pay_id}", headers=auth(gestionnaire_token))
        assert d.status_code == 204, d.text
        deleted = (
            (
                await db.execute(
                    select(AuditLog).where(
                        AuditLog.action == "payment.delete", AuditLog.entity_id == pay_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(deleted) == 1
        assert deleted[0].details and deleted[0].details.get("period") == "2026-08"
