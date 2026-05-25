"""Service AppSettings — lecture/écriture des paramètres dynamiques."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text as sa_text

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "avis_generation_day": "1",
    "avis_generation_hour": "7",
    "avis_generation_minute": "30",
}


async def get(db: AsyncSession, key: str) -> str:
    """Lit un paramètre. Retourne la valeur par défaut si absent."""
    try:
        from app.models.app_setting import AppSetting
        row = (await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )).scalar_one_or_none()
        return row.value if row else _DEFAULTS.get(key, "")
    except Exception as exc:
        logger.warning("settings_service.get(%s) failed: %s", key, exc)
        return _DEFAULTS.get(key, "")


async def set_(db: AsyncSession, key: str, value: str) -> None:
    """Écrit ou met à jour un paramètre."""
    await db.execute(
        sa_text(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (:k, :v, now()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
        ).bindparams(k=key, v=value)
    )
    await db.flush()


async def get_scheduler_config(db: AsyncSession) -> dict:
    """Retourne la config du scheduler avis d'échéances."""
    day = int(await get(db, "avis_generation_day") or "1")
    hour = int(await get(db, "avis_generation_hour") or "7")
    minute = int(await get(db, "avis_generation_minute") or "30")
    return {"day": day, "hour": hour, "minute": minute}
