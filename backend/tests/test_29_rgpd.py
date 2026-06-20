"""Tests RGPD — export (droit d'accès) et anonymisation (droit à l'effacement)."""
import pytest
from datetime import date
from sqlalchemy import select

from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.audit_log import AuditLog
from app.services import rgpd_service
from tests.conftest import auth


async def _tenant_with_history(db, owner_id, email="rgpd@test.fr"):
    prop = Property(name="Bien RGPD", address="1 rue", zip_code="75001", city="Paris",
                    country="France", property_type="appartement", created_by=owner_id)
    db.add(prop); await db.flush()
    tenant = Tenant(first_name="Jean", last_name="Locataire", email=email, phone="0600000000",
                    monthly_income=2500, notes="note privée", created_by=owner_id)
    db.add(tenant); await db.flush()
    lease = Lease(tenant_id=tenant.id, property_id=prop.id, start_date=date(2025, 1, 1),
                  rent_amount=800, charges_amount=100, lease_type="vide", payment_day=1,
                  is_active=True, created_by=owner_id)
    db.add(lease); await db.flush()
    db.add(Payment(lease_id=lease.id, tenant_id=tenant.id, period_year=2026, period_month=1,
                   due_date=date(2026, 1, 1), amount_rent=800, amount_charges=100,
                   amount_due=900, amount_paid=900, status=PaymentStatus.PAID))
    await db.flush()
    return tenant


@pytest.mark.asyncio
async def test_export_gathers_all_data(db, gestionnaire_user):
    tenant = await _tenant_with_history(db, gestionnaire_user.id)
    data = await rgpd_service.export_tenant(db, tenant)
    assert data["identite"]["email"] == "rgpd@test.fr"
    assert data["identite"]["monthly_income"] == 2500.0
    assert len(data["baux"]) == 1
    assert len(data["loyers"]) == 1
    assert data["loyers"][0]["amount_due"] == 900.0


@pytest.mark.asyncio
async def test_anonymize_strips_pii_keeps_accounting(db, gestionnaire_user):
    tenant = await _tenant_with_history(db, gestionnaire_user.id, email="erase@test.fr")
    tid = tenant.id
    res = await rgpd_service.anonymize_tenant(db, tenant)
    assert res["already"] is False
    await db.refresh(tenant)
    # Identité effacée
    assert tenant.first_name == "Anonymisé"
    assert tenant.email is None
    assert tenant.phone is None
    assert tenant.monthly_income is None
    assert tenant.notes is None
    assert tenant.anonymized_at is not None
    # Historique comptable conservé (obligation légale)
    payments = list((await db.execute(
        select(Payment).where(Payment.tenant_id == tid))).scalars())
    assert len(payments) == 1
    assert float(payments[0].amount_due) == 900.0


@pytest.mark.asyncio
async def test_anonymize_is_idempotent(db, gestionnaire_user):
    tenant = await _tenant_with_history(db, gestionnaire_user.id, email="idem@test.fr")
    await rgpd_service.anonymize_tenant(db, tenant)
    res2 = await rgpd_service.anonymize_tenant(db, tenant)
    assert res2["already"] is True


@pytest.mark.asyncio
async def test_api_export_and_erase_with_audit(client, db, gestionnaire_user, gestionnaire_token):
    tenant = await _tenant_with_history(db, gestionnaire_user.id, email="api@test.fr")
    # Export (droit d'accès)
    r = await client.get(f"/api/v1/rgpd/tenants/{tenant.id}/export", headers=auth(gestionnaire_token))
    assert r.status_code == 200
    assert r.json()["identite"]["email"] == "api@test.fr"
    # Effacement
    r2 = await client.post(f"/api/v1/rgpd/tenants/{tenant.id}/erase", headers=auth(gestionnaire_token))
    assert r2.status_code == 200
    await db.refresh(tenant)
    assert tenant.anonymized_at is not None
    # Journal d'audit : les 2 opérations sont tracées
    actions = set((await db.execute(
        select(AuditLog.action).where(AuditLog.entity_id == tenant.id))).scalars())
    assert "rgpd.export" in actions
    assert "rgpd.erase" in actions


@pytest.mark.asyncio
async def test_api_other_manager_cannot_export(client, db, gestionnaire_user, admin_user, gestionnaire_token):
    # Locataire créé par l'ADMIN → un gestionnaire lambda n'y a pas accès.
    tenant = await _tenant_with_history(db, admin_user.id, email="foreign@test.fr")
    r = await client.get(f"/api/v1/rgpd/tenants/{tenant.id}/export", headers=auth(gestionnaire_token))
    assert r.status_code == 403
