"""API Settings — configuration dynamique du scheduler et paramètres globaux."""
import logging
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_gestionnaire
from app.models.user import User
from app.services import settings_service

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
