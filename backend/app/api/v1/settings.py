"""API Settings — configuration dynamique du scheduler et paramètres globaux."""
import logging
from datetime import datetime, date
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_gestionnaire
from app.models.user import User
from app.services import settings_service
from app.services import template_layout_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Paramètres"])

TZ = ZoneInfo("Europe/Paris")


class SchedulerConfig(BaseModel):
    day: int = Field(..., ge=1, le=28, description="Jour du mois (1-28)")
    hour: int = Field(7, ge=0, le=23)
    minute: int = Field(30, ge=0, le=59)


class SchedulerConfigOut(SchedulerConfig):
    next_run: Optional[str] = None


def _compute_next_run(day: int, hour: int, minute: int) -> str:
    """Calcule la prochaine exécution (Paris) en ISO 8601."""
    now = datetime.now(TZ)
    year, month = now.year, now.month
    # Est-ce que ce mois est encore possible ?
    try:
        candidate = datetime(year, month, day, hour, minute, tzinfo=TZ)
    except ValueError:
        candidate = None
    if candidate is None or candidate <= now:
        # Passer au mois suivant
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        try:
            candidate = datetime(year, month, day, hour, minute, tzinfo=TZ)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            candidate = datetime(year, month, min(day, last_day), hour, minute, tzinfo=TZ)
    return candidate.isoformat()


@router.get("/scheduler", response_model=SchedulerConfigOut)
async def get_scheduler(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    """Retourne la configuration du scheduler automatique des avis d'échéances."""
    cfg = await settings_service.get_scheduler_config(db)
    return SchedulerConfigOut(
        day=cfg["day"],
        hour=cfg["hour"],
        minute=cfg["minute"],
        next_run=_compute_next_run(cfg["day"], cfg["hour"], cfg["minute"]),
    )


@router.put("/scheduler", response_model=SchedulerConfigOut)
async def update_scheduler(
    body: SchedulerConfig,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    """Met à jour le jour/heure de génération automatique et reschedule le job APScheduler."""
    await settings_service.set_(db, "avis_generation_day", str(body.day))
    await settings_service.set_(db, "avis_generation_hour", str(body.hour))
    await settings_service.set_(db, "avis_generation_minute", str(body.minute))
    await db.commit()

    # Reschedule dynamique du job APScheduler
    try:
        from app.core.scheduler import reschedule_avis_job
        reschedule_avis_job(body.day, body.hour, body.minute)
    except Exception as exc:
        logger.warning("Reschedule APScheduler failed (non bloquant): %s", exc)

    return SchedulerConfigOut(
        day=body.day,
        hour=body.hour,
        minute=body.minute,
        next_run=_compute_next_run(body.day, body.hour, body.minute),
    )


# ── Rappels Telegram quotidiens (équipe d'agents IA) ─────────────────────────

class ReminderConfig(BaseModel):
    enabled: bool = True
    hour: int = Field(8, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)


class ReminderConfigOut(ReminderConfig):
    next_run: Optional[str] = None


def _compute_next_daily(hour: int, minute: int) -> str:
    """Prochaine occurrence quotidienne (Paris) en ISO 8601."""
    from datetime import timedelta
    now = datetime.now(TZ)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate.isoformat()


@router.get("/telegram-reminders", response_model=ReminderConfigOut)
async def get_reminders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    """Config des rappels Telegram quotidiens (point du jour)."""
    cfg = await settings_service.get_reminder_config(db)
    return ReminderConfigOut(
        enabled=cfg["enabled"], hour=cfg["hour"], minute=cfg["minute"],
        next_run=_compute_next_daily(cfg["hour"], cfg["minute"]) if cfg["enabled"] else None,
    )


@router.put("/telegram-reminders", response_model=ReminderConfigOut)
async def update_reminders(
    body: ReminderConfig,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    """Active/désactive et planifie l'heure des rappels Telegram quotidiens."""
    await settings_service.set_(db, "telegram_reminder_enabled", "true" if body.enabled else "false")
    await settings_service.set_(db, "telegram_reminder_hour", str(body.hour))
    await settings_service.set_(db, "telegram_reminder_minute", str(body.minute))
    await db.commit()
    try:
        from app.core.scheduler import reschedule_reminder_job
        reschedule_reminder_job(body.hour, body.minute)
    except Exception as exc:
        logger.warning("Reschedule rappels Telegram échoué (non bloquant): %s", exc)
    return ReminderConfigOut(
        enabled=body.enabled, hour=body.hour, minute=body.minute,
        next_run=_compute_next_daily(body.hour, body.minute) if body.enabled else None,
    )


@router.post("/telegram-reminders/run")
async def run_reminders_now(
    _: User = Depends(get_current_gestionnaire),
):
    """Déclenche immédiatement l'envoi des rappels (test). Sécurisé : no-op si Telegram désactivé."""
    from app.core.scheduler import run_telegram_reminders_now
    await run_telegram_reminders_now()
    return {"status": "ok"}


# ── Mise en page des templates PDF ───────────────────────────────────────────

class TemplateSpacing(BaseModel):
    page_margin: str = "2cm 2.5cm"
    header_mb: int = 14
    section_mb: int = 12
    cell_padding_v: int = 4
    cell_padding_h: int = 10
    line_height: float = 1.55
    font_size: int = 10
    # Personnalisation typographie / couleurs (édition depuis l'aperçu).
    font_family: Optional[str] = "Helvetica, Arial, sans-serif"
    text_color: Optional[str] = "#1f2937"
    heading_color: Optional[str] = None  # vide → reprend la couleur d'accent du template
    heading_scale: Optional[int] = 6     # h1/h2 = font_size + heading_scale
    paragraph_spacing: Optional[int] = 8  # px entre paragraphes


class TemplateLayout(BaseModel):
    header_left: List[str] = ["logo", "sender"]
    header_right: List[str] = ["recipient", "citydate"]
    spacing: TemplateSpacing = Field(default_factory=TemplateSpacing)


@router.get("/template-layout", response_model=TemplateLayout)
async def get_template_layout(
    _: User = Depends(get_current_gestionnaire),
):
    """Retourne la config de mise en page des templates PDF (avis + quittance)."""
    return template_layout_service.get_layout()


@router.put("/template-layout", response_model=TemplateLayout)
async def update_template_layout(
    body: TemplateLayout,
    _: User = Depends(get_current_gestionnaire),
):
    """Enregistre la config de mise en page sur disque."""
    template_layout_service.save_layout(body.model_dump())
    return body


@router.get("/template-preview")
async def preview_template(
    template: str = Query("avis", pattern="^(avis|quittance)$"),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Génère un PDF d'aperçu avec données fictives selon la mise en page courante."""
    _sig_uri = getattr(current_user, "signature", None) or ""
    from types import SimpleNamespace
    from app.services.pdf_service import render_template, html_to_pdf

    _MONTHS_FR = ["janvier","février","mars","avril","mai","juin",
                  "juillet","août","septembre","octobre","novembre","décembre"]
    _d = date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"
    layout = template_layout_service.get_layout()

    mock_property = SimpleNamespace(
        owner_name="Cabinet Durand Immobilier",
        name="Résidence Les Tilleuls",
        full_address="12 avenue des Tilleuls\n75001 Paris",
        city="Paris",
        property_type="appartement",
        floor=2,
        area_sqm=45.0,
    )
    mock_tenant = SimpleNamespace(full_name="Marie Dupont")
    mock_lease = SimpleNamespace(parent_property=mock_property)

    if template == "avis":
        mock_avis = SimpleNamespace(
            tenant=mock_tenant,
            lease=mock_lease,
            period_label="Juin 2026",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            period_range_label="du 01/06/2026 au 30/06/2026",
            amount_rent=800.0,
            amount_charges=80.0,
            amount_apl=0.0,
            amount_total=880.0,
            amount_due=880.0,
            due_date=None,
        )
        html = render_template("avis_echeance.html.j2", {
            "avis": mock_avis,
            "property": mock_property,
            "today": today_fr,
            "layout": layout,
            "signature_uri": _sig_uri,
        })
    else:
        import uuid as _uuid
        from datetime import datetime as _dt, timezone as _tz
        mock_payment = SimpleNamespace(
            id=_uuid.uuid4(),
            tenant=mock_tenant,
            lease=mock_lease,
            period_label="Juin 2026",
            period_year=2026,
            period_month=6,
            amount_rent=800.0,
            amount_charges=80.0,
            amount_apl=None,
            amount_due=880.0,
            amount_paid=880.0,
            balance=0,
            payment_date=_d,
            payment_method="virement",
            status="paid",
            updated_at=_dt.now(_tz.utc),
            quittance_generated_at=_dt.now(_tz.utc),
            quittance_sent_at=None,
        )
        html = render_template("quittance.html.j2", {
            "payment": mock_payment,
            "today": today_fr,
            "layout": layout,
            "signature_uri": _sig_uri,
        })

    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="apercu_{template}.pdf"'},
    )


# ── État + test des canaux de notification (e-mail / SMS) ─────────────────────
class TestNotifyIn(BaseModel):
    channel: str = Field(..., pattern="^(email|sms)$")
    to: str = Field(..., description="Adresse e-mail ou numéro de téléphone destinataire")


@router.get("/notifications-status")
async def notifications_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Indique si l'e-mail (SMTP) et le SMS (Brevo) sont configurés/activés,
    et si le gestionnaire est mis en copie (CC) des e-mails locataires."""
    from app.config import get_settings
    cfg = get_settings()
    cc_manager = (await settings_service.get(db, "cc_manager_emails") or "true").lower() == "true"
    return {
        "email_enabled": cfg.smtp_enabled,
        "sms_enabled": cfg.sms_enabled,
        "smtp_from": cfg.SMTP_FROM_EMAIL,
        "sms_sender": cfg.SMS_SENDER,
        "cc_manager_emails": cc_manager,
    }


class CcManagerIn(BaseModel):
    enabled: bool


@router.put("/cc-manager")
async def set_cc_manager(
    body: CcManagerIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Active/désactive la mise en copie (CC) du gestionnaire sur les e-mails
    envoyés aux locataires (avis, quittances, relances, communications)."""
    await settings_service.set_(db, "cc_manager_emails", "true" if body.enabled else "false")
    await db.commit()
    return {"cc_manager_emails": body.enabled}


@router.post("/test-notification")
async def test_notification(
    body: TestNotifyIn,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Envoie un e-mail ou un SMS de test (pour valider la configuration Brevo)."""
    if body.channel == "email":
        from app.services.email_service import send_email
        ok = await send_email(
            to=body.to,
            subject="Le Comptoir Immo : e-mail de test",
            html_body="<p>Ceci est un e-mail de test. Votre configuration SMTP fonctionne ✅</p>",
        )
        return {"channel": "email", "to": body.to, "sent": ok,
                "detail": "Envoyé" if ok else "Désactivé (SMTP non configuré) ou erreur — voir logs"}
    from app.services.sms_service import send_sms
    ok = await send_sms(body.to, "Le Comptoir Immo : SMS de test. Configuration OK.")
    return {"channel": "sms", "to": body.to, "sent": ok,
            "detail": "Envoyé" if ok else "Désactivé (BREVO_API_KEY absente), numéro invalide, ou erreur — voir logs"}
