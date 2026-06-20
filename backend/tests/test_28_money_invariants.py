"""Tests des INVARIANTS ARGENT (tunnel loyer/paiement/APL/quittance).

Verrouille la sémantique financière côté service (pas d'HTTP) :
  - amount_due = loyer + charges (BRUT, avant APL) ;
  - APL en tiers-payant = paiement initial versé par la CAF ;
  - statut PENDING/PARTIAL/PAID selon (payé vs dû) ;
  - reste à charge locataire = dû − payé ;
  - paiement intégral → quittance générée + avis de loyer « Acquitté » ;
  - trop-perçu autorisé (avance) ; rejet sur loyer déjà payé / annulé.
"""
import pytest
from datetime import date
from sqlalchemy import select

from app.models.payment import Payment, PaymentStatus
from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentRecordIn
from app.core.exceptions import BadRequestException


async def _setup_lease(db, gestionnaire_user, rent=800.0, charges=100.0,
                       apl_amount=None, apl_tiers_payant=False, suffix="m"):
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.lease import Lease
    prop = Property(
        name=f"Prop {suffix}", address="2 Rue", zip_code="75001", city="Paris",
        country="France", property_type="appartement", created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()
    tenant = Tenant(
        first_name="Paul", last_name="Money", email=f"paul.{suffix}@test.fr",
        created_by=gestionnaire_user.id,
    )
    db.add(tenant)
    await db.flush()
    lease = Lease(
        tenant_id=tenant.id, property_id=prop.id, start_date=date(2025, 1, 1),
        rent_amount=rent, charges_amount=charges, lease_type="vide", payment_day=1,
        is_active=True, apl_amount=apl_amount, apl_tiers_payant=apl_tiers_payant,
        created_by=gestionnaire_user.id,
    )
    db.add(lease)
    await db.flush()
    return lease


async def _payment(db, lease, *, due=900.0, paid=0.0, apl=None,
                   status=PaymentStatus.PENDING, year=2026, month=5):
    p = Payment(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=year, period_month=month,
        due_date=date(year, month, 1), amount_rent=800, amount_charges=100,
        amount_apl=apl, amount_due=due, amount_paid=paid, status=status,
    )
    db.add(p)
    await db.flush()
    return p


# ── record_payment : transitions de statut & reste à payer ───────────────────
@pytest.mark.asyncio
async def test_partial_payment_keeps_partial_status(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, suffix="partial")
    p = await _payment(db, lease, due=900, paid=0)
    pay = await PaymentService.record_payment(
        db, p.id, PaymentRecordIn(amount_paid=400, payment_date=date.today()))
    assert pay.status == PaymentStatus.PARTIAL
    assert float(pay.amount_paid) == 400.0
    assert float(pay.amount_due) - float(pay.amount_paid) == 500.0   # reste à payer


@pytest.mark.asyncio
async def test_full_payment_marks_paid_and_acquits_avis(db, gestionnaire_user):
    from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
    lease = await _setup_lease(db, gestionnaire_user, suffix="full")
    p = await _payment(db, lease, due=900, paid=0, year=2026, month=6)
    db.add(AvisEcheance(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=6,
        due_date=date(2026, 6, 1), amount_rent=800, amount_charges=100, amount_total=900,
        kind="loyer", status=AvisEcheanceStatus.ENVOYE,
    ))
    await db.flush()
    pay = await PaymentService.record_payment(
        db, p.id, PaymentRecordIn(amount_paid=900, payment_date=date.today()))
    assert pay.status == PaymentStatus.PAID
    assert pay.quittance_generated_at is not None
    avis = (await db.execute(
        select(AvisEcheance).where(AvisEcheance.lease_id == lease.id)
    )).scalar_one()
    assert avis.status == AvisEcheanceStatus.ACQUITTE


@pytest.mark.asyncio
async def test_two_partials_reach_paid(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, suffix="twopart")
    p = await _payment(db, lease, due=900, paid=0, month=7)
    await PaymentService.record_payment(db, p.id, PaymentRecordIn(amount_paid=500, payment_date=date.today()))
    pay = await PaymentService.record_payment(db, p.id, PaymentRecordIn(amount_paid=400, payment_date=date.today()))
    assert pay.status == PaymentStatus.PAID
    assert float(pay.amount_paid) == 900.0


@pytest.mark.asyncio
async def test_overpayment_allowed_marks_paid(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, suffix="over")
    p = await _payment(db, lease, due=900, paid=0, month=8)
    pay = await PaymentService.record_payment(
        db, p.id, PaymentRecordIn(amount_paid=1000, payment_date=date.today()))
    assert pay.status == PaymentStatus.PAID
    assert float(pay.amount_paid) == 1000.0   # trop-perçu autorisé (avance)


@pytest.mark.asyncio
async def test_cannot_record_on_paid(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, suffix="onpaid")
    p = await _payment(db, lease, due=900, paid=900, status=PaymentStatus.PAID, month=9)
    with pytest.raises(BadRequestException):
        await PaymentService.record_payment(db, p.id, PaymentRecordIn(amount_paid=50, payment_date=date.today()))


@pytest.mark.asyncio
async def test_cannot_record_on_cancelled(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, suffix="oncancel")
    p = await _payment(db, lease, due=900, paid=0, status=PaymentStatus.CANCELLED, month=10)
    with pytest.raises(BadRequestException):
        await PaymentService.record_payment(db, p.id, PaymentRecordIn(amount_paid=50, payment_date=date.today()))


# ── Génération : APL tiers-payant = paiement initial CAF ─────────────────────
@pytest.mark.asyncio
async def test_apl_full_coverage_generates_paid(db, gestionnaire_user):
    """APL ≥ (loyer+charges) → loyer généré déjà PAYÉ (versement CAF), dû reste brut."""
    lease = await _setup_lease(db, gestionnaire_user, apl_amount=900, apl_tiers_payant=True, suffix="aplfull")
    pay = await PaymentService.generate_for_lease(db, lease, 2026, 3, gestionnaire_user.id)
    assert float(pay.amount_due) == 900.0          # brut, loyer + charges
    assert float(pay.amount_apl) == 900.0
    assert float(pay.amount_paid) == 900.0         # versé par la CAF
    assert pay.status == PaymentStatus.PAID


# ── Paiement en ligne (carte) : idempotence du webhook ───────────────────────
@pytest.mark.asyncio
async def test_card_payment_webhook_is_idempotent(db, gestionnaire_user):
    """Un webhook de paiement carte rejoué ne doit JAMAIS encaisser deux fois."""
    from app.services.online_payment_service import _record_card_payment
    lease = await _setup_lease(db, gestionnaire_user, suffix="card")
    p = await _payment(db, lease, due=900, paid=0, month=11)

    ok1 = await _record_card_payment(db, p.id, "Stripe")
    await db.refresh(p)
    assert ok1 is True
    assert p.status == PaymentStatus.PAID
    assert float(p.amount_paid) == 900.0

    # Rejeu du webhook (Stripe peut livrer plusieurs fois le même évènement).
    ok2 = await _record_card_payment(db, p.id, "Stripe")
    await db.refresh(p)
    assert ok2 is True
    assert float(p.amount_paid) == 900.0   # toujours 900, pas 1800


@pytest.mark.asyncio
async def test_apl_partial_leaves_reste_a_charge(db, gestionnaire_user):
    """APL partielle → statut PARTIAL, reste à charge locataire = dû − APL."""
    lease = await _setup_lease(db, gestionnaire_user, apl_amount=400, apl_tiers_payant=True, suffix="aplpart")
    pay = await PaymentService.generate_for_lease(db, lease, 2026, 4, gestionnaire_user.id)
    assert float(pay.amount_due) == 900.0
    assert float(pay.amount_apl) == 400.0
    assert float(pay.amount_paid) == 400.0
    assert pay.status == PaymentStatus.PARTIAL
    assert float(pay.amount_due) - float(pay.amount_paid) == 500.0   # reste à charge
