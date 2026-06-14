"""Moteur d'automatisation : SEUL émetteur automatique des e-mails/SMS locataires.

Principe (exigence produit) : AUCUN envoi automatique en dur. Tout est piloté par
les `AutomationRule` configurées par le gestionnaire. Types gérés :

- ``avis_echeance``  : envoie l'avis d'échéance (PDF) du mois, ``trigger_days``
  jours avant la date d'échéance.
- ``quittance``      : envoie la quittance (PDF) quand un mois devient soldé
  (déclenché par l'événement de paiement, voir ``send_quittance_for_payment``).
- ``rappel_impaye`` / ``relance_1`` / ``relance_2`` : relance d'impayé,
  ``trigger_days`` jours APRÈS la date d'échéance, tant que le solde est dû.
- ``communication_groupee`` : manuel uniquement (non planifié).

Dédup : ``CommunicationLog.dedup_key`` (une cible + une règle = un seul envoi).
Canal : email / sms / email_sms. Le gestionnaire est mis en copie selon le
réglage ``cc_manager_emails`` (cf. cc_service).
"""
import logging
import re
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Types « relance d'impayé » (déclenchés N jours après l'échéance).
_REMINDER_TYPES = {"rappel_impaye", "relance_1", "relance_2"}
_REMINDER_LABELS = {
    "rappel_impaye": "Rappel de loyer",
    "relance_1": "Relance",
    "relance_2": "Mise en demeure",
}


def _rule_cc(rule) -> Optional[str]:
    """Adresse(s) en copie de la règle (CC), nettoyées ; None si vide."""
    raw = (getattr(rule, "cc_emails", None) or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return ", ".join(parts) or None


def _render(template: Optional[str], ctx: dict) -> Optional[str]:
    """Remplace les {{variables}} d'un modèle par les valeurs du contexte."""
    if not template:
        return None
    def repl(m):
        return str(ctx.get(m.group(1).strip(), m.group(0)))
    return re.sub(r"\{\{\s*([\w]+)\s*\}\}", repl, template)


async def _already_sent(db: AsyncSession, dedup_key: str) -> bool:
    from app.models.automation import CommunicationLog
    row = (await db.execute(
        select(CommunicationLog.id).where(
            CommunicationLog.dedup_key == dedup_key,
            CommunicationLog.status == "sent",
        ).limit(1)
    )).first()
    return row is not None


async def _log(db, *, rule, tenant_id, lease_id, channel, recipient, subject,
               body, status, dedup_key, error=None) -> None:
    from app.models.automation import CommunicationLog
    db.add(CommunicationLog(
        rule_id=getattr(rule, "id", None),
        tenant_id=tenant_id, lease_id=lease_id,
        channel=channel, recipient=recipient, subject=subject,
        body=(body or "")[:5000] if body else None,
        status=status, error_message=(str(error)[:500] if error else None),
        dedup_key=dedup_key, sent_at=datetime.now(timezone.utc),
    ))
    await db.flush()


async def _manager_lease_ids(db: AsyncSession, manager_id) -> list:
    """Baux dans le périmètre d'un gestionnaire (créateur du bail)."""
    from app.models.lease import Lease
    rows = (await db.execute(
        select(Lease.id).where(Lease.created_by == manager_id)
    )).scalars().all()
    return list(rows)


# ── Règles par défaut (no-régression : les envois actuels continuent) ─────────

# Jeu de règles standard créé pour chaque gestionnaire. (rule_type, name, channel,
# trigger_days). Les délais : avis 7 j avant l'échéance ; rappels/relances après.
_DEFAULT_RULES = [
    ("avis_echeance", "Avis d'échéance", "email", 7),
    ("quittance", "Quittance", "email", 0),
    ("rappel_impaye", "Rappel impayé", "email", 3),
    ("relance_1", "Relance 1", "email", 8),
    ("relance_2", "Relance 2 (mise en demeure)", "email_sms", 15),
]


async def ensure_default_rules(db: AsyncSession, gestionnaire_id) -> int:
    """Crée les règles d'automatisation par défaut manquantes pour un gestionnaire
    (idempotent : ne recrée jamais un type déjà présent). Renvoie le nb créé."""
    from app.models.automation import AutomationRule
    from app.models.user import User
    if not gestionnaire_id:
        return 0
    existing = set((await db.execute(
        select(AutomationRule.rule_type).where(AutomationRule.created_by == gestionnaire_id)
    )).scalars().all())
    # Le gestionnaire est mis en copie par défaut (son propre e-mail).
    mgr = await db.get(User, gestionnaire_id)
    cc_default = (getattr(mgr, "email", None) or "").strip() or None
    created = 0
    for rule_type, name, channel, days in _DEFAULT_RULES:
        if rule_type in existing:
            continue
        db.add(AutomationRule(
            name=name, rule_type=rule_type, channel=channel,
            trigger_days=days, is_active=True, created_by=gestionnaire_id,
            cc_emails=cc_default,
        ))
        created += 1
    if created:
        await db.flush()
    return created


async def backfill_default_rules(db: AsyncSession) -> int:
    """Au démarrage : seede les règles par défaut pour les gestionnaires qui n'ont
    AUCUNE règle (comptes créés avant la fonctionnalité). Ne touche pas ceux qui en
    ont déjà (respecte les suppressions/personnalisations)."""
    from app.models.user import User
    from app.models.automation import AutomationRule
    from app.core.permissions import Role
    mgr_roles = [Role.ADMIN.value, Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value]
    managers = (await db.execute(
        select(User.id).where(User.role.in_(mgr_roles))
    )).scalars().all()
    if not managers:
        return 0
    with_rules = set((await db.execute(
        select(AutomationRule.created_by).where(AutomationRule.created_by.in_(managers))
    )).scalars().all())
    total = 0
    for mid in managers:
        if mid in with_rules:
            continue
        total += await ensure_default_rules(db, mid)
    return total


# ── Avis d'échéance ───────────────────────────────────────────────────────────

async def _send_avis(db, rule, avis, today: date) -> bool:
    from app.models.tenant import Tenant
    from app.models.avis_echeance import AvisEcheanceStatus

    dedup = f"avis:{avis.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, avis.tenant_id)
    if tenant is None:
        return False

    period = avis.period_range_label or avis.period_label
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": period,
        "amount": f"{float(avis.amount_total or 0):.2f} €",
        "due_date": avis.due_date.strftime("%d/%m/%Y") if avis.due_date else "",
    }
    subject = _render(rule.subject, ctx) or f"Avis d'échéance : {period}"
    sms_text = _render(rule.body_template, ctx) or (
        f"Le Comptoir Immo : votre avis d'échéance {period} "
        f"({ctx['amount']}) est disponible. Échéance le {ctx['due_date']}.")
    channel = (rule.channel or "email")
    cc = _rule_cc(rule)

    any_sent = False
    last_err = None
    # E-mail (PDF joint)
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.services.pdf_service import AvisEcheancePDFService
            from app.services.email_service import send_avis_echeance
            pdf = await AvisEcheancePDFService.generate(db, avis)
            ok = await send_avis_echeance(
                to=tenant.email, tenant_name=tenant.full_name or tenant.email,
                period_label=period, amount_total=float(avis.amount_total or 0),
                due_date=ctx["due_date"], pdf_bytes=pdf, cc=cc, subject=subject,
            )
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] avis email échec avis=%s: %r", avis.id, exc)
    # SMS
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms
            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] avis sms échec avis=%s: %r", avis.id, exc)

    if any_sent:
        if avis.status != AvisEcheanceStatus.ACQUITTE:
            avis.status = AvisEcheanceStatus.ENVOYE
            if not avis.sent_at:
                # Colonne avis.sent_at = TIMESTAMP sans fuseau → datetime naïf.
                avis.sent_at = datetime.utcnow()
        await _log(db, rule=rule, tenant_id=avis.tenant_id, lease_id=avis.lease_id,
                   channel=channel, recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
                   subject=subject, body=sms_text, status="sent", dedup_key=dedup)
    elif last_err is not None:
        await _log(db, rule=rule, tenant_id=avis.tenant_id, lease_id=avis.lease_id,
                   channel=channel, recipient=getattr(tenant, "email", None),
                   subject=subject, body=sms_text, status="error", dedup_key=dedup, error=last_err)
    return any_sent


async def _run_avis_rule(db, rule, today: date) -> int:
    from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
    lease_ids = await _manager_lease_ids(db, rule.created_by)
    if not lease_ids:
        return 0
    horizon = today - timedelta(days=60)
    avis_list = (await db.execute(
        select(AvisEcheance).where(
            AvisEcheance.lease_id.in_(lease_ids),
            AvisEcheance.kind == "loyer",
            AvisEcheance.status != AvisEcheanceStatus.ACQUITTE,
            AvisEcheance.due_date >= horizon,
        )
    )).scalars().all()
    sent = 0
    for avis in avis_list:
        # Envoyer dès que l'on est à trigger_days (ou moins) de l'échéance.
        if avis.due_date and (avis.due_date - timedelta(days=int(rule.trigger_days or 0))) <= today:
            if await _send_avis(db, rule, avis, today):
                sent += 1
    return sent


# ── Rappels / relances d'impayé ───────────────────────────────────────────────

async def _send_reminder(db, rule, payment, today: date) -> bool:
    from app.models.tenant import Tenant
    from app.models.property import Property
    from app.models.lease import Lease

    dedup = f"{rule.rule_type}:{payment.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, payment.tenant_id)
    if tenant is None:
        return False
    lease = await db.get(Lease, payment.lease_id)
    prop = await db.get(Property, lease.property_id) if lease else None

    label = _REMINDER_LABELS.get(rule.rule_type, "Relance")
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": payment.period_label,
        "amount": f"{float(payment.amount_due or 0):.2f} €",
        "balance": f"{float(payment.balance):.2f} €",
        "due_date": payment.due_date.strftime("%d/%m/%Y") if payment.due_date else "",
        "property_name": (prop.name if prop else ""),
    }
    subject = _render(rule.subject, ctx) or f"{label} : loyer {ctx['period']}"
    default_body = (
        f"<p>Bonjour {ctx['tenant_name']},</p>"
        f"<p>Sauf erreur de notre part, le loyer de la période "
        f"<strong>{ctx['period']}</strong> reste impayé (solde dû : "
        f"<strong>{ctx['balance']}</strong>).</p>"
        f"<p>Merci de régulariser dans les meilleurs délais.</p>"
        f"<p>Cordialement,<br>Votre gestionnaire</p>")
    body_html = _render(rule.body_template, ctx) or default_body
    sms_text = (_render(rule.body_template, ctx) if rule.body_template else None) or (
        f"Le Comptoir Immo : {label.lower()}, loyer {ctx['period']} impaye "
        f"(solde {ctx['balance']}). Merci de regulariser.")
    channel = (rule.channel or "email")
    cc = _rule_cc(rule)

    any_sent = False
    last_err = None
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.services.email_service import send_email
            ok = await send_email(to=tenant.email, subject=subject, html_body=body_html, cc=cc)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] relance email échec payment=%s: %r", payment.id, exc)
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms
            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] relance sms échec payment=%s: %r", payment.id, exc)

    if any_sent:
        await _log(db, rule=rule, tenant_id=payment.tenant_id, lease_id=payment.lease_id,
                   channel=channel, recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
                   subject=subject, body=sms_text, status="sent", dedup_key=dedup)
    elif last_err is not None:
        await _log(db, rule=rule, tenant_id=payment.tenant_id, lease_id=payment.lease_id,
                   channel=channel, recipient=getattr(tenant, "email", None),
                   subject=subject, body=sms_text, status="error", dedup_key=dedup, error=last_err)
    return any_sent


async def _run_reminder_rule(db, rule, today: date) -> int:
    from app.models.payment import Payment, PaymentStatus
    lease_ids = await _manager_lease_ids(db, rule.created_by)
    if not lease_ids:
        return 0
    horizon = today - timedelta(days=120)
    pays = (await db.execute(
        select(Payment).where(
            Payment.lease_id.in_(lease_ids),
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIAL, PaymentStatus.LATE]),
            Payment.due_date >= horizon,
        )
    )).scalars().all()
    sent = 0
    delay = int(rule.trigger_days or 0)
    for p in pays:
        if float(p.balance) <= 0.005:
            continue
        if p.due_date and (p.due_date + timedelta(days=delay)) <= today:
            if await _send_reminder(db, rule, p, today):
                sent += 1
    return sent


# ── Quittance (événementiel : déclenché par le paiement) ──────────────────────

async def send_quittance_for_payment(db: AsyncSession, payment) -> bool:
    """Envoie la quittance d'un mois soldé, SI une règle « quittance » active existe
    pour le gestionnaire du bail. Toujours marque la quittance générée (consultable).
    Renvoie True si un envoi a eu lieu."""
    from app.models.lease import Lease
    from app.models.tenant import Tenant
    from app.models.automation import AutomationRule

    if not getattr(payment, "quittance_generated_at", None):
        payment.quittance_generated_at = datetime.now(timezone.utc)
    if getattr(payment, "quittance_sent_at", None):
        return False

    lease = await db.get(Lease, payment.lease_id)
    manager_id = getattr(lease, "created_by", None) if lease else None
    if not manager_id:
        return False
    rule = (await db.execute(
        select(AutomationRule).where(
            AutomationRule.created_by == manager_id,
            AutomationRule.rule_type == "quittance",
            AutomationRule.is_active.is_(True),
        ).limit(1)
    )).scalar_one_or_none()
    if rule is None:
        return False  # pas de règle active → pas d'envoi (aucune boîte noire)

    dedup = f"quittance:{payment.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, payment.tenant_id)
    if tenant is None:
        return False

    amount = float(payment.amount_paid or 0) + float(getattr(payment, "amount_on_plan", 0) or 0)
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": payment.period_label,
        "amount": f"{amount:.2f} €",
    }
    subject = _render(rule.subject, ctx) or f"Quittance de loyer : {ctx['period']}"
    sms_text = _render(rule.body_template, ctx) or (
        f"Le Comptoir Immo : votre quittance {ctx['period']} ({ctx['amount']}) est disponible.")
    channel = (rule.channel or "email")
    cc = _rule_cc(rule)

    any_sent = False
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.api.v1.payments import build_quittance_pdf
            from app.services.email_service import send_quittance as _send_q
            pdf, _fn = await build_quittance_pdf(db, payment)
            ok = await _send_q(to=tenant.email, tenant_name=tenant.full_name or "",
                               period_label=ctx["period"], amount=amount,
                               pdf_bytes=pdf, cc=cc, subject=subject)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            logger.warning("[automation] quittance email échec payment=%s: %r", payment.id, exc)
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms
            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            logger.warning("[automation] quittance sms échec payment=%s: %r", payment.id, exc)

    if any_sent:
        payment.quittance_sent_at = datetime.now(timezone.utc)
        await _log(db, rule=rule, tenant_id=payment.tenant_id, lease_id=payment.lease_id,
                   channel=channel, recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
                   subject=subject, body=sms_text, status="sent", dedup_key=dedup)
    return any_sent


# ── Boucle principale (planifiée quotidiennement) ─────────────────────────────

async def run_all(db: AsyncSession, today: Optional[date] = None, manager_id=None) -> dict:
    """Exécute les règles actives (hors quittance = événementiel, et hors
    communication groupée = manuelle). Si ``manager_id`` est fourni, limite aux
    règles de ce gestionnaire (déclenchement manuel). Renvoie {rule_type: count}."""
    from app.models.automation import AutomationRule
    today = today or date.today()
    q = select(AutomationRule).where(AutomationRule.is_active.is_(True))
    if manager_id is not None:
        q = q.where(AutomationRule.created_by == manager_id)
    rules = (await db.execute(q)).scalars().all()
    summary: dict = {}
    for rule in rules:
        if not rule.created_by:
            continue
        try:
            if rule.rule_type == "avis_echeance":
                n = await _run_avis_rule(db, rule, today)
            elif rule.rule_type in _REMINDER_TYPES:
                n = await _run_reminder_rule(db, rule, today)
            else:
                continue  # quittance (événementiel) / communication_groupee (manuel)
            if n:
                summary[rule.rule_type] = summary.get(rule.rule_type, 0) + n
        except Exception as exc:  # noqa: BLE001 : une règle ne bloque pas les autres
            logger.error("[automation] règle %s (%s) échec: %r", rule.id, rule.rule_type, exc)
    return summary
