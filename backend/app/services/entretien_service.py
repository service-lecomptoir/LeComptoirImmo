import uuid
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entretien import (
    Prestataire, Entretien, EntretienStatus, EntretienFrequency,
)
from app.schemas.entretien import PrestataireCreate, PrestataireUpdate, EntretienCreate, EntretienUpdate
from app.core.exceptions import NotFoundException

# Durée indicative (jours) d'une fréquence déclarée — repli quand l'historique est insuffisant.
_FREQ_DAYS = {
    EntretienFrequency.MENSUEL.value: 30,
    EntretienFrequency.TRIMESTRIEL.value: 91,
    EntretienFrequency.SEMESTRIEL.value: 182,
    EntretienFrequency.ANNUEL.value: 365,
}
# Horizon : on ne crée la prochaine occurrence que si elle est due dans ce délai (ou en retard).
_AUTOPLAN_HORIZON_DAYS = 90
# Préfixe de note marquant un entretien créé par la planification automatique.
AUTOPLAN_TAG = "[auto]"


def _median(values: list[int]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _days_to_frequency(days: float) -> str:
    if days <= 45:
        return EntretienFrequency.MENSUEL.value
    if days <= 135:
        return EntretienFrequency.TRIMESTRIEL.value
    if days <= 270:
        return EntretienFrequency.SEMESTRIEL.value
    return EntretienFrequency.ANNUEL.value


class PrestataireService:

    @staticmethod
    async def create(db: AsyncSession, data: PrestataireCreate) -> Prestataire:
        p = Prestataire(**data.model_dump())
        db.add(p)
        await db.flush()
        await db.refresh(p)
        return p

    @staticmethod
    async def get(db: AsyncSession, prestataire_id: uuid.UUID) -> Prestataire:
        result = await db.execute(select(Prestataire).where(Prestataire.id == prestataire_id))
        p = result.scalar_one_or_none()
        if not p:
            raise NotFoundException("Prestataire", str(prestataire_id))
        return p

    @staticmethod
    async def list_all(db: AsyncSession, active_only: bool = True) -> list[Prestataire]:
        q = select(Prestataire)
        if active_only:
            q = q.where(Prestataire.is_active == True)
        q = q.order_by(Prestataire.name)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, prestataire_id: uuid.UUID, data: PrestataireUpdate) -> Prestataire:
        p = await PrestataireService.get(db, prestataire_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(p, field, value)
        await db.flush()
        return p

    @staticmethod
    async def delete(db: AsyncSession, prestataire_id: uuid.UUID) -> None:
        p = await PrestataireService.get(db, prestataire_id)
        await db.delete(p)
        await db.flush()


class EntretienService:

    @staticmethod
    async def create(db: AsyncSession, data: EntretienCreate) -> Entretien:
        e = Entretien(**data.model_dump())
        db.add(e)
        await db.flush()
        await db.refresh(e)
        return e

    @staticmethod
    async def get(db: AsyncSession, entretien_id: uuid.UUID) -> Entretien:
        result = await db.execute(
            select(Entretien)
            .options(selectinload(Entretien.prestataire), selectinload(Entretien.property))
            .where(Entretien.id == entretien_id)
        )
        e = result.scalar_one_or_none()
        if not e:
            raise NotFoundException("Entretien", str(entretien_id))
        return e

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        property_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Entretien], int]:
        q = select(Entretien).options(
            selectinload(Entretien.prestataire),
            selectinload(Entretien.property),
        )
        if status:
            q = q.where(Entretien.status == status)
        if property_id:
            q = q.where(Entretien.property_id == property_id)
        q = q.order_by(Entretien.scheduled_date.asc())

        count_q = select(func.count(Entretien.id))
        if status:
            count_q = count_q.where(Entretien.status == status)
        if property_id:
            count_q = count_q.where(Entretien.property_id == property_id)

        total = (await db.execute(count_q)).scalar_one()
        items = list((await db.execute(q.offset(offset).limit(limit))).scalars().all())
        return items, total

    @staticmethod
    async def update(db: AsyncSession, entretien_id: uuid.UUID, data: EntretienUpdate) -> Entretien:
        e = await EntretienService.get(db, entretien_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(e, field, value)
        await db.flush()
        return e

    @staticmethod
    async def delete(db: AsyncSession, entretien_id: uuid.UUID) -> None:
        e = await EntretienService.get(db, entretien_id)
        await db.delete(e)
        await db.flush()

    # ── Planification automatique d'après l'historique ───────────────────────
    @staticmethod
    async def autoplan(
        db: AsyncSession,
        *,
        allowed_props: Optional[set] = None,
        excluded_props: Optional[set] = None,
        today: Optional[date] = None,
    ) -> list[dict]:
        """Crée automatiquement la prochaine maintenance pour chaque « série »
        d'entretiens récurrents, en déduisant la cadence de l'HISTORIQUE des
        entretiens terminés (repli sur la fréquence déclarée si une seule
        occurrence). Idempotent : ne crée rien si une occurrence postérieure au
        dernier entretien terminé existe déjà dans la série.

        Une série = (bien, intitulé normalisé). Retourne la liste des entretiens créés.
        """
        today = today or date.today()
        q = select(Entretien).options(selectinload(Entretien.property))
        rows = list((await db.execute(q)).scalars().all())

        # Filtrage de périmètre (isolation rôle)
        def in_scope(e: Entretien) -> bool:
            if allowed_props is not None and e.property_id not in allowed_props:
                return False
            if excluded_props is not None and e.property_id in excluded_props:
                return False
            return True

        rows = [e for e in rows if in_scope(e)]

        # Groupage par (bien, intitulé normalisé)
        groups: dict[tuple, list[Entretien]] = {}
        for e in rows:
            key = (e.property_id, " ".join((e.title or "").lower().split()))
            groups.setdefault(key, []).append(e)

        created: list[dict] = []
        for (prop_id, _norm), series in groups.items():
            active = [e for e in series if e.status != EntretienStatus.ANNULE.value]
            done = [e for e in active if e.status == EntretienStatus.TERMINE.value]
            if not done:
                continue  # pas d'historique réel → on ne planifie pas

            def eff_date(e: Entretien) -> date:
                return e.completed_date or e.scheduled_date

            done_dates = sorted({eff_date(e) for e in done})
            last_done = done_dates[-1]

            # Idempotence : une occurrence postérieure au dernier terminé existe déjà ?
            if any(e.scheduled_date > last_done for e in active):
                continue

            # Cadence : médiane des intervalles observés, sinon fréquence déclarée
            cadence: Optional[float] = None
            if len(done_dates) >= 2:
                diffs = [(done_dates[i] - done_dates[i - 1]).days for i in range(1, len(done_dates))]
                diffs = [d for d in diffs if d > 3]
                if diffs:
                    cadence = _median(diffs)
            if cadence is None:
                last_e = max(done, key=eff_date)
                freq = (last_e.frequency or EntretienFrequency.UNIQUE.value)
                cadence = _FREQ_DAYS.get(freq)
            if not cadence:
                continue  # série non récurrente (fréquence unique, pas d'historique)

            next_due = last_done + timedelta(days=int(round(cadence)))
            if next_due > today + timedelta(days=_AUTOPLAN_HORIZON_DAYS):
                continue  # trop loin dans le futur : on attend

            src = max(done, key=eff_date)
            months = max(1, int(round(cadence / 30)))
            notes = (f"{AUTOPLAN_TAG} Planifié automatiquement d'après l'historique "
                     f"(cadence ~{months} mois). Dernier le {last_done.strftime('%d/%m/%Y')}.")
            e_new = Entretien(
                title=src.title,
                description=src.description,
                type=src.type,
                status=EntretienStatus.PLANIFIE.value,
                frequency=_days_to_frequency(cadence),
                scheduled_date=next_due,
                next_date=next_due + timedelta(days=int(round(cadence))),
                property_id=prop_id,
                prestataire_id=src.prestataire_id,
                notes=notes,
            )
            db.add(e_new)
            created.append({
                "title": src.title,
                "property_label": (src.property.address if src.property else None),
                "scheduled_date": next_due.isoformat(),
                "cadence_months": months,
                "overdue": next_due < today,
            })

        if created:
            await db.flush()
        return created
