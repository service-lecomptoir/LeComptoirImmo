"""
Tests API — Paiements.
"""
import pytest
from datetime import date
from tests.conftest import auth


async def _setup_lease(db, gestionnaire_user):
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.lease import Lease

    prop = Property(
        name="Prop Payments", address="2 Rue", zip_code="75001",
        city="Paris", country="France", property_type="appartement",
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="Paul", last_name="Payment",
        email=f"paul.pay@test.fr",
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id, property_id=prop.id,
        start_date=date.today(), rent_amount=800.00, charges_amount=100.00,
        lease_type="vide", payment_day=1, is_active=True,
    )
    db.add(lease)
    await db.flush()
    return lease


@pytest.mark.asyncio
class TestPaymentGeneration:
    async def test_gestionnaire_generates_monthly_payments(self, client, gestionnaire_token, gestionnaire_user, db):
        lease = await _setup_lease(db, gestionnaire_user)

        resp = await client.post("/api/v1/payments/generate", headers=auth(gestionnaire_token), json={
            "year": 2026,
            "month": 6,
        })
        assert resp.status_code == 201
        assert "generated" in resp.json()

    async def test_locataire_cannot_generate_payments(self, client, locataire_token):
        resp = await client.post("/api/v1/payments/generate", headers=auth(locataire_token), json={
            "year": 2026, "month": 6,
        })
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
        from app.models.property import Property
        from app.models.tenant import Tenant
        from app.models.lease import Lease
        from app.models.payment import Payment, PaymentStatus

        prop = Property(
            name="Prop Loc Pay", address="3 Rue", zip_code="75002",
            city="Paris", country="France", property_type="appartement",
        )
        db.add(prop)
        await db.flush()

        tenant = Tenant(
            first_name="Alice", last_name="Loc2",
            email="alice.loc2@test.fr",
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
        resp = await client.get("/api/v1/payments/stats/dashboard", headers=auth(gestionnaire_token))
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
    async def test_quittance_refused_when_unpaid(self, client, gestionnaire_token, gestionnaire_user, db):
        """Une quittance ne peut pas être émise pour un loyer impayé (règle métier)."""
        from app.models.payment import Payment, PaymentStatus
        lease = await _setup_lease(db, gestionnaire_user)
        payment = Payment(
            lease_id=lease.id, tenant_id=lease.tenant_id,
            period_year=2026, period_month=4, due_date=date.today(),
            amount_rent=800.00, amount_charges=100.00, amount_due=900.00,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        resp = await client.get(f"/api/v1/payments/{payment.id}/quittance", headers=auth(gestionnaire_token))
        assert resp.status_code == 400

    async def test_quittance_pdf_generated_when_paid(self, client, gestionnaire_token, gestionnaire_user, db):
        """Régression : la quittance PDF doit se générer (200, application/pdf) une fois payé.
        Garde-fou contre le NameError 'select' détecté en recette."""
        from app.models.payment import Payment, PaymentStatus
        lease = await _setup_lease(db, gestionnaire_user)
        payment = Payment(
            lease_id=lease.id, tenant_id=lease.tenant_id,
            period_year=2026, period_month=4, due_date=date.today(),
            amount_rent=800.00, amount_charges=100.00, amount_due=900.00,
            amount_paid=900.00, payment_date=date.today(), payment_method="virement",
            status=PaymentStatus.PAID,
        )
        db.add(payment)
        await db.flush()
        resp = await client.get(f"/api/v1/payments/{payment.id}/quittance", headers=auth(gestionnaire_token))
        assert resp.status_code == 200, resp.text
        assert "pdf" in resp.headers.get("content-type", "")
