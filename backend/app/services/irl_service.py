"""Indice de Référence des Loyers (IRL).

Source : récupération automatique INSEE (best-effort, si configurée) + repli sur
saisie manuelle stockée en base (table irl_indices)."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.irl_index import IrlIndex

logger = logging.getLogger(__name__)

# Série BDM INSEE de l'IRL (indice de référence des loyers, base 100 T4 1998).
INSEE_IRL_SERIES = "001515333"


class IrlService:
    @staticmethod
    async def list_indices(db: AsyncSession) -> list[IrlIndex]:
        rows = (
            (
                await db.execute(
                    select(IrlIndex).order_by(IrlIndex.year.desc(), IrlIndex.quarter.desc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    async def get_index(db: AsyncSession, year: int, quarter: int) -> IrlIndex | None:
        return (
            await db.execute(
                select(IrlIndex).where(IrlIndex.year == year, IrlIndex.quarter == quarter)
            )
        ).scalar_one_or_none()

    @staticmethod
    async def get_latest_for_quarter(db: AsyncSession, quarter: int) -> IrlIndex | None:
        """Indice le plus récent (année max) pour un trimestre donné."""
        return (
            await db.execute(
                select(IrlIndex)
                .where(IrlIndex.quarter == quarter)
                .order_by(IrlIndex.year.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    @staticmethod
    async def upsert(
        db: AsyncSession, year: int, quarter: int, value: float, source: str = "manuel"
    ) -> IrlIndex:
        existing = await IrlService.get_index(db, year, quarter)
        if existing:
            existing.value = value
            existing.source = source
            await db.flush()
            return existing
        idx = IrlIndex(id=uuid.uuid4(), year=year, quarter=quarter, value=value, source=source)
        db.add(idx)
        await db.flush()
        return idx

    @staticmethod
    async def get_by_id(db: AsyncSession, irl_id: uuid.UUID) -> IrlIndex | None:
        return (
            await db.execute(select(IrlIndex).where(IrlIndex.id == irl_id))
        ).scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession, irl_id: uuid.UUID, year: int, quarter: int, value: float
    ) -> IrlIndex | None:
        idx = await IrlService.get_by_id(db, irl_id)
        if not idx:
            return None
        # Conflit éventuel : un autre indice occupe déjà (year, quarter).
        clash = await IrlService.get_index(db, year, quarter)
        if clash and clash.id != irl_id:
            raise ValueError("Un indice existe déjà pour ce trimestre et cette année.")
        idx.year = year
        idx.quarter = quarter
        idx.value = value
        idx.source = "manuel"  # une édition manuelle prime sur l'origine INSEE
        await db.flush()
        return idx

    @staticmethod
    async def delete(db: AsyncSession, irl_id: uuid.UUID) -> bool:
        idx = await IrlService.get_by_id(db, irl_id)
        if not idx:
            return False
        await db.delete(idx)
        await db.flush()
        return True

    @staticmethod
    async def fetch_from_insee(db: AsyncSession) -> dict:
        """Tente de récupérer les indices IRL depuis l'API INSEE BDM.
        Nécessite settings.INSEE_API_KEY. Best-effort : repli manuel si indisponible."""
        key = getattr(get_settings(), "INSEE_API_KEY", "") or ""
        if not key:
            return {
                "fetched": 0,
                "configured": False,
                "message": "Récupération INSEE non configurée : saisie manuelle utilisée.",
            }
        try:
            import httpx

            url = f"https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/{INSEE_IRL_SERIES}"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Accept": "application/json",
                    },
                )
            resp.raise_for_status()
            payload = resp.json()
            fetched = 0
            # Le format BDM varie ; on parcourt défensivement les observations.
            observations = []
            try:
                series = payload["seriesData"]["series"] if isinstance(payload, dict) else []
                for s in series:
                    observations.extend(s.get("observations", []))
            except Exception:
                observations = []
            for obs in observations:
                period = obs.get("TIME_PERIOD") or obs.get("period")  # ex. "2024-Q1"
                val = obs.get("OBS_VALUE") or obs.get("value")
                if not period or val in (None, ""):
                    continue
                try:
                    y, q = period.split("-Q")
                    await IrlService.upsert(db, int(y), int(q), float(val), source="insee")
                    fetched += 1
                except Exception:
                    continue
            await db.flush()
            return {
                "fetched": fetched,
                "configured": True,
                "message": f"{fetched} indice(s) récupéré(s) depuis l'INSEE.",
            }
        except Exception as exc:  # noqa
            logger.warning("Récupération IRL INSEE échouée : %r", exc)
            return {
                "fetched": 0,
                "configured": True,
                "message": "Échec de la récupération INSEE : saisie manuelle conservée.",
            }
