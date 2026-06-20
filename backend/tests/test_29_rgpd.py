"""Tests RGPD — export (droit d'accès) et anonymisation (droit à l'effacement)."""
import pytest
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select

from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.candidature import Candidature
from app.models.audit_log import AuditLog
from app.services import rgpd_service
from tests.conftest import auth


async def _prop(db, owner_id, name="P"):
    p = Property(name=name, address="x", zip_code="75001", city="Paris",
                 country="France", property_type="appartement", created_by=owner_id)
    db.add(p); await db.flush()
    return p


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


# ── Rétention (purge automatique) ────────────────────────────────────────────
async def _departed_tenant(db, owner_id, end: date, email):
    prop = await _prop(db, owner_id, name=f"P-{email}")
    t = Tenant(first_name="Parti", last_name="Locataire", email=email, created_by=owner_id)
    db.add(t); await db.flush()
    db.add(Lease(tenant_id=t.id, property_id=prop.id, start_date=date(2015, 1, 1),
                 end_date=end, rent_amount=800, charges_amount=0, lease_type="vide",
                 payment_day=1, is_active=False, created_by=owner_id))
    await db.flush()
    return t


@pytest.mark.asyncio
async def test_retention_anonymizes_long_departed_tenant(db, gestionnaire_user):
    t = await _departed_tenant(db, gestionnaire_user.id, date(2019, 1, 1), "longgone@test.fr")
    res = await rgpd_service.apply_retention(db, tenant_years=3, candidature_months=12)
    await db.refresh(t)
    assert res["tenants_anonymized"] >= 1
    assert t.anonymized_at is not None
    assert t.email is None


@pytest.mark.asyncio
async def test_retention_keeps_active_tenant(db, gestionnaire_user):
    t = await _tenant_with_history(db, gestionnaire_user.id, email="stillhere@test.fr")  # bail actif
    await rgpd_service.apply_retention(db)
    await db.refresh(t)
    assert t.anonymized_at is None


@pytest.mark.asyncio
async def test_retention_keeps_recently_departed_tenant(db, gestionnaire_user):
    recent = date.today() - timedelta(days=200)   # parti il y a < 3 ans
    t = await _departed_tenant(db, gestionnaire_user.id, recent, "recent@test.fr")
    await rgpd_service.apply_retention(db, tenant_years=3)
    await db.refresh(t)
    assert t.anonymized_at is None


@pytest.mark.asyncio
async def test_retention_dry_run_changes_nothing(db, gestionnaire_user):
    t = await _departed_tenant(db, gestionnaire_user.id, date(2019, 1, 1), "dry@test.fr")
    res = await rgpd_service.apply_retention(db, dry_run=True)
    await db.refresh(t)
    assert res["dry_run"] is True
    assert res["tenants_anonymized"] >= 1
    assert t.anonymized_at is None     # rien modifié en dry-run


@pytest.mark.asyncio
async def test_retention_anonymizes_old_refused_candidature(db, gestionnaire_user):
    prop = await _prop(db, gestionnaire_user.id, name="P-cand")
    old = datetime.utcnow() - timedelta(days=400)
    c = Candidature(property_id=prop.id, full_name="Refusé Ancien", email="ref@test.fr",
                    phone="0600", status="refusee", created_at=old)
    db.add(c); await db.flush()
    await rgpd_service.apply_retention(db, candidature_months=12)
    await db.refresh(c)
    assert c.full_name == "Anonymisé"
    assert c.email is None


@pytest.mark.asyncio
async def test_retention_keeps_recent_refused_candidature(db, gestionnaire_user):
    prop = await _prop(db, gestionnaire_user.id, name="P-cand2")
    recent = datetime.utcnow() - timedelta(days=30)
    c = Candidature(property_id=prop.id, full_name="Refusé Récent", email="recent.ref@test.fr",
                    status="refusee", created_at=recent)
    db.add(c); await db.flush()
    await rgpd_service.apply_retention(db, candidature_months=12)
    await db.refresh(c)
    assert c.full_name == "Refusé Récent"   # trop récent → conservé
