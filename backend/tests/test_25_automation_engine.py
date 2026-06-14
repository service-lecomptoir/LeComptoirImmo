"""
Moteur d'automatisation : les envois (avis, rappels/relances, quittance) sont
pilotés par les AutomationRule. Les envois réels (SMTP/SMS) et la génération PDF
sont simulés (patch) pour valider la logique de sélection / dédup / désactivation.
"""
from contextlib import contextmanager
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.services import automation_engine
from app.models.automation import AutomationRule, CommunicationLog
from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
from app.models.payment import Payment, PaymentStatus


@contextmanager
def _mock_sends():
    """Simule les canaux d'envoi + la génération PDF (indépendant de SMTP/xhtml2pdf)."""
    with patch("app.services.email_service.send_email", new=AsyncMock(return_value=True)), \
         patch("app.services.email_service.send_avis_echeance", new=AsyncMock(return_value=True)), \
         patch("app.services.email_service.send_quittance", new=AsyncMock(return_value=True)), \
         patch("app.services.sms_service.send_sms", new=AsyncMock(return_value=True)), \
         patch("app.services.pdf_service.AvisEcheancePDFService.generate", new=AsyncMock(return_value=b"pdf")), \
         patch("app.api.v1.payments.build_quittance_pdf", new=AsyncMock(return_value=(b"pdf", "q.pdf"))):
        yield


async def _setup_lease(db, gestionnaire_user, email="loc.auto@test.fr"):
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.lease import Lease
    prop = Property(name="Auto Prop", address="1 Rue", zip_code="75001", city="Paris",
                    country="France", property_type="appartement", created_by=gestionnaire_user.id)
    db.add(prop); await db.flush()
    tenant = Tenant(first_name="Auto", last_name="Loc", email=email, phone="0600000000",
                    created_by=gestionnaire_user.id)
    db.add(tenant); await db.flush()
    lease = Lease(tenant_id=tenant.id, property_id=prop.id, start_date=date.today(),
                  rent_amount=800, charges_amount=100, lease_type="vide", payment_day=1,
                  is_active=True, created_by=gestionnaire_user.id)
    db.add(lease); await db.flush()
    return lease


def _rule(gid, rule_type, channel="email", trigger_days=0, active=True):
    return AutomationRule(name=rule_type, rule_type=rule_type, channel=channel,
                          trigger_days=trigger_days, is_active=active, created_by=gid)


@pytest.mark.asyncio
async def test_avis_rule_sends_and_dedups(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user)
    rule = _rule(gestionnaire_user.id, "avis_echeance", trigger_days=7)
    db.add(rule); await db.flush()
    avis = AvisEcheance(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=6,
        due_date=date.today(), amount_rent=800, amount_charges=100, amount_total=900,
        kind="loyer", status=AvisEcheanceStatus.BROUILLON,
    )
    db.add(avis); await db.flush()

    with _mock_sends():
        n1 = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)
        n2 = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)

    assert n1.get("avis_echeance") == 1
    assert not n2  # dédup : pas de second envoi
    await db.refresh(avis)
    assert avis.status == AvisEcheanceStatus.ENVOYE
    logs = (await db.execute(select(CommunicationLog).where(CommunicationLog.rule_id == rule.id))).scalars().all()
    assert len([l for l in logs if l.status == "sent"]) == 1


@pytest.mark.asyncio
async def test_avis_not_sent_before_trigger_window(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.future@test.fr")
    db.add(_rule(gestionnaire_user.id, "avis_echeance", trigger_days=3))
    avis = AvisEcheance(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=7,
        due_date=date.today() + timedelta(days=10), amount_rent=800, amount_charges=100,
        amount_total=900, kind="loyer", status=AvisEcheanceStatus.BROUILLON,
    )
    db.add(avis); await db.flush()
    with _mock_sends():
        summary = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)
    assert not summary  # échéance dans 10 j, délai 3 j → pas encore


@pytest.mark.asyncio
async def test_reminder_respects_trigger_days(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.rem@test.fr")
    pay = Payment(lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=5,
                  due_date=date.today() - timedelta(days=5), amount_rent=800, amount_charges=100,
                  amount_due=900, amount_paid=0, status=PaymentStatus.LATE)
    db.add(pay); await db.flush()
    db.add(_rule(gestionnaire_user.id, "rappel_impaye", trigger_days=3))
    db.add(_rule(gestionnaire_user.id, "relance_2", trigger_days=10))
    await db.flush()
    with _mock_sends():
        summary = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)
    assert summary.get("rappel_impaye") == 1
    assert "relance_2" not in summary


@pytest.mark.asyncio
async def test_reminder_skips_when_paid(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.paid@test.fr")
    pay = Payment(lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=5,
                  due_date=date.today() - timedelta(days=20), amount_rent=800, amount_charges=100,
                  amount_due=900, amount_paid=900, status=PaymentStatus.PAID)
    db.add(pay); await db.flush()
    db.add(_rule(gestionnaire_user.id, "rappel_impaye", trigger_days=3)); await db.flush()
    with _mock_sends():
        summary = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)
    assert not summary


@pytest.mark.asyncio
async def test_disabled_rule_does_nothing(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.off@test.fr")
    pay = Payment(lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=5,
                  due_date=date.today() - timedelta(days=10), amount_rent=800, amount_charges=100,
                  amount_due=900, amount_paid=0, status=PaymentStatus.LATE)
    db.add(pay); await db.flush()
    db.add(_rule(gestionnaire_user.id, "rappel_impaye", trigger_days=3, active=False)); await db.flush()
    with _mock_sends():
        summary = await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)
    assert not summary


@pytest.mark.asyncio
async def test_quittance_sent_only_with_active_rule(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.quit@test.fr")
    pay = Payment(lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=4,
                  due_date=date.today(), amount_rent=800, amount_charges=100, amount_due=900,
                  amount_paid=900, payment_date=date.today(), status=PaymentStatus.PAID)
    db.add(pay); await db.flush()

    with _mock_sends():
        sent0 = await automation_engine.send_quittance_for_payment(db, pay)
    assert sent0 is False
    assert pay.quittance_generated_at is not None
    assert pay.quittance_sent_at is None

    db.add(_rule(gestionnaire_user.id, "quittance")); await db.flush()
    with _mock_sends():
        sent1 = await automation_engine.send_quittance_for_payment(db, pay)
        sent2 = await automation_engine.send_quittance_for_payment(db, pay)
    assert sent1 is True
    assert sent2 is False
    assert pay.quittance_sent_at is not None


@pytest.mark.asyncio
async def test_ensure_default_rules_idempotent(db, gestionnaire_user):
    n1 = await automation_engine.ensure_default_rules(db, gestionnaire_user.id)
    n2 = await automation_engine.ensure_default_rules(db, gestionnaire_user.id)
    assert n1 == 5
    assert n2 == 0
    types = set((await db.execute(
        select(AutomationRule.rule_type).where(AutomationRule.created_by == gestionnaire_user.id)
    )).scalars().all())
    assert {"avis_echeance", "quittance", "rappel_impaye", "relance_1", "relance_2"} <= types


@pytest.mark.asyncio
async def test_default_rules_signatures_by_type(db, gestionnaire_user):
    await automation_engine.ensure_default_rules(db, gestionnaire_user.id)
    rows = (await db.execute(
        select(AutomationRule.rule_type, AutomationRule.signature)
        .where(AutomationRule.created_by == gestionnaire_user.id)
    )).all()
    sig = {rt: s for rt, s in rows}
    assert sig["rappel_impaye"] == "Service contentieux"
    assert sig["relance_2"] == "Service contentieux"
    assert sig["avis_echeance"] == "Service Gestion Locative"
    assert sig["quittance"] == "Service Gestion Locative"


def test_signature_block_content():
    from app.services.email_service import build_signature_html
    html = build_signature_html("Service contentieux", has_logo=True)
    assert "Service contentieux" in html
    assert "cid:managerlogo" in html
    assert "automatiquement par le système Le Comptoir" in html
    # Sans logo : pas de balise image.
    assert "cid:managerlogo" not in build_signature_html("Service X", has_logo=False)


@pytest.mark.asyncio
async def test_signature_passed_to_avis_email(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.sig@test.fr")
    rule = _rule(gestionnaire_user.id, "avis_echeance", trigger_days=7)
    rule.signature = "Service Gestion Locative"
    db.add(rule); await db.flush()
    avis = AvisEcheance(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=6,
        due_date=date.today(), amount_rent=800, amount_charges=100, amount_total=900,
        kind="loyer", status=AvisEcheanceStatus.BROUILLON,
    )
    db.add(avis); await db.flush()

    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_avis_echeance", new=sender), \
         patch("app.services.pdf_service.AvisEcheancePDFService.generate", new=AsyncMock(return_value=b"pdf")):
        await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)

    assert sender.await_count == 1
    sig = sender.await_args.kwargs.get("signature_html") or ""
    assert "Service Gestion Locative" in sig
    assert "automatiquement par le système Le Comptoir" in sig


@pytest.mark.asyncio
async def test_rule_body_rendered_and_sent(db, gestionnaire_user):
    lease = await _setup_lease(db, gestionnaire_user, email="loc.body@test.fr")
    rule = _rule(gestionnaire_user.id, "avis_echeance", trigger_days=7)
    rule.body_template = "Bonjour {{tenant_name}},\nLoyer {{period}} : {{amount}}."
    db.add(rule); await db.flush()
    avis = AvisEcheance(
        lease_id=lease.id, tenant_id=lease.tenant_id, period_year=2026, period_month=6,
        due_date=date.today(), amount_rent=800, amount_charges=100, amount_total=900,
        kind="loyer", status=AvisEcheanceStatus.BROUILLON,
    )
    db.add(avis); await db.flush()

    sender = AsyncMock(return_value=True)
    with patch("app.services.email_service.send_avis_echeance", new=sender), \
         patch("app.services.pdf_service.AvisEcheancePDFService.generate", new=AsyncMock(return_value=b"pdf")):
        await automation_engine.run_all(db, date.today(), manager_id=gestionnaire_user.id)

    body = sender.await_args.kwargs.get("body_html") or ""
    assert "Auto Loc" in body  # {{tenant_name}} rendu
    assert "<br>" in body       # saut de ligne converti


@pytest.mark.asyncio
async def test_default_rules_have_subject_and_body(db, gestionnaire_user):
    await automation_engine.ensure_default_rules(db, gestionnaire_user.id)
    rows = (await db.execute(
        select(AutomationRule.rule_type, AutomationRule.subject, AutomationRule.body_template)
        .where(AutomationRule.created_by == gestionnaire_user.id)
    )).all()
    for rt, subj, body in rows:
        if rt == "communication_groupee":
            continue
        assert subj and subj.strip(), f"sujet manquant pour {rt}"
        assert body and body.strip(), f"corps manquant pour {rt}"
