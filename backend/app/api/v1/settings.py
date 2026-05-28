"""API Settings — configuration dynamique du scheduler et paramètres globaux."""
import logging
from datetime import datetime, date
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


# ── Mise en page des templates PDF ───────────────────────────────────────────

class TemplateSpacing(BaseModel):
    page_margin: str = "2cm 2.5cm"
    header_mb: int = 14
    section_mb: int = 12
    cell_padding_v: int = 4
    cell_padding_h: int = 10
    line_height: float = 1.55
    font_size: int = 10


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
    _: User = Depends(get_current_gestionnaire),
):
    """Génère un PDF d'aperçu avec données fictives selon la mise en page courante."""
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
        full_address="12 avenue des Tilleuls, 75001 Paris",
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
        })

    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="apercu_{template}.pdf"'},
    )
