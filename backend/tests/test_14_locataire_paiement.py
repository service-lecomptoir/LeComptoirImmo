"""
Tests API — Module paiement locataire (consultation + déclaration de règlement).
"""
import pytest
from datetime import date
from tests.conftest import auth


async def _setup_locataire_with_payment(db, locataire_user):
    """Crée Property → Unit → Tenant (lié au locataire) → Lease → Payment pending."""
    from app.models.property import Property
    from app.models.unit import Unit
    from app.models.tenant import Tenant
    from app.models.lease import Lease
    from app.models.payment import Payment, PaymentStatus

    prop = Property(
        name="Prop Pay Loc", address="5 Rue", zip_code="75005",
        city="Paris", country="France", property_type="appartement",
    )
    db.add(prop)
    await db.flush()

    unit = Unit(
        property_id=prop.id, unit_ref="PL-01",
        unit_type="T2", base_rent=700.00, charges_amount=80.00,
    )
    db.add(unit)
    await db.flush()

    tenant = Tenant(
        first_name="René", last_name="Payer",
        email="rene.pay.test@test.fr",
        user_id=locataire_user.id,
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        unit_id=unit.id, tenant_id=tenant.id, property_id=prop.id,
        start_date=date.today(), rent_amount=700.00, charges_amount=80.00,
        lease_type="vide", payment_day=5, is_active=True,
    )
    db.add(lease)
    await db.flush()

    payment = Payment(
        lease_id=lease.id, tenant_id=tenant.id, unit_id=unit.id,
        period_year=2026, period_month=5,
        due_date=date.today(),
        amount_rent=700.00, amount_charges=80.00,
        amount_due=780.00,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.flush()
    return tenant, payment


@pytest.mark.asyncio
class TestLocataireCurrentPayment:
    async def test_locataire_sees_current_payment(self, client, locataire_token, locataire_user, db):
        await _setup_locataire_with_payment(db, locataire_user)
        resp = await client.get("/api/v1/payments/locataire/current", headers=auth(locataire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_name" in data
        assert data["payment"] is not None

    async def test_locataire_without_tenant_returns_null(self, client, locataire_token):
        resp = await client.get("/api/v1/payments/locataire/current", headers=auth(locataire_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment"] is None

    async def test_gestionnaire_endpoint_returns_null(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/payments/locataire/current", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["payment"] is None

    async def test_unauthenticated_cannot_access(self, client):
        resp = await client.get("/api/v1/payments/locataire/current")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestLocataireDeclarePayment:
    async def test_declare_virement(self, client, locataire_token, locataire_user, db):
        await _setup_locataire_with_payment(db, locataire_user)
        resp = await client.post(
            "/api/v1/payments/locataire/declare",
            headers=auth(locataire_token),
            json={"method": "virement", "amount": 780.0},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "declared"
        assert data["method"] == "virement"

    async def test_declare_cheque(self, client, locataire_token, locataire_user, db):
        await _setup_locataire_with_payment(db, locataire_user)
        resp = await client.post(
            "/api/v1/payments/locataire/declare",
            headers=auth(locataire_token),
            json={"method": "cheque", "amount": 780.0},
        )
        assert resp.status_code == 201
        assert resp.json()["method"] == "cheque"

    async def test_declare_carte(self, client, locataire_token, locataire_user, db):
        await _setup_locataire_with_payment(db, locataire_user)
        resp = await client.post(
            "/api/v1/payments/locataire/declare",
            headers=auth(locataire_token),
            json={"method": "carte", "amount": 780.0},
        )
        assert resp.status_code == 201
        assert resp.json()["method"] == "carte"

    async def test_declare_without_tenant_fails(self, client, locataire_token):
        resp = await client.post(
            "/api/v1/payments/locataire/declare",
            headers=auth(locataire_token),
            json={"method": "virement", "amount": 500.0},
        )
        assert resp.status_code == 400

    async def test_unauthenticated_cannot_declare(self, client):
        resp = await client.post(
            "/api/v1/payments/locataire/declare",
            json={"method": "virement", "amount": 500.0},
        )
        assert resp.status_code in (401, 403)
