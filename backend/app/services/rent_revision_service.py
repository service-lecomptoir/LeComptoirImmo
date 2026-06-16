import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease
from app.models.rent_revision import RentRevision


def first_of_next_month(d: Optional[date] = None) -> date:
    """1er jour du mois qui suit `d` (par défaut aujourd'hui). Date d'effet par
    défaut d'une révision : jamais le mois en cours."""
    d = d or date.today()
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


class RentRevisionService:
    """Gère les révisions de loyer/charges avec date d'effet (point d'entrée unique
    pour l'édition manuelle, l'IRL, la régularisation de charges et l'amiable)."""

    @staticmethod
    async def list_for_lease(db: AsyncSession, lease_id: uuid.UUID) -> list[RentRevision]:
        rows = (await db.execute(
            select(RentRevision)
            .where(RentRevision.lease_id == lease_id)
            .order_by(RentRevision.effective_date.desc(), RentRevision.created_at.desc())
        )).scalars().all()
        return list(rows)

    @staticmethod
    def effective_amounts(
        lease: Lease, revisions: list[RentRevision], on_date: date
    ) -> tuple[float, float]:
        """Loyer + charges applicables à `on_date` = dernière révision dont la date
        d'effet précède (ou égale) `on_date`. À défaut, les montants du bail."""
        applicable = [r for r in revisions if r.effective_date <= on_date]
        if applicable:
            best = max(applicable, key=lambda r: (r.effective_date, r.created_at or datetime.min))
            return float(best.rent_amount), float(best.charges_amount)
        return float(lease.rent_amount), float(lease.charges_amount)

    @staticmethod
    async def schedule(
        db: AsyncSession,
        lease: Lease,
        *,
        new_rent: float,
        new_charges: float,
        effective_date: date,
        source: str,
        reason: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> RentRevision:
        """Enregistre une révision. Le montant précédent (rappel) est celui en
        vigueur aujourd'hui. Si la date d'effet est déjà atteinte, le bail est mis à
        jour immédiatement ; sinon la révision reste « programmée »."""
        revisions = await RentRevisionService.list_for_lease(db, lease.id)
        prev_rent, prev_charges = RentRevisionService.effective_amounts(lease, revisions, date.today())
        today = date.today()
        rev = RentRevision(
            lease_id=lease.id,
            effective_date=effective_date,
            rent_amount=round(float(new_rent), 2),
            charges_amount=round(float(new_charges), 2),
            prev_rent_amount=round(prev_rent, 2),
            prev_charges_amount=round(prev_charges, 2),
            source=source,
            reason=reason,
            created_by=created_by,
            applied=effective_date <= today,
        )
        db.add(rev)
        if effective_date <= today:
            lease.rent_amount = round(float(new_rent), 2)
            lease.charges_amount = round(float(new_charges), 2)
        await db.flush()
        return rev

    @staticmethod
    async def sync_lease_current(db: AsyncSession, lease: Lease) -> bool:
        """Bascule lease.rent_amount/charges_amount sur les montants en vigueur
        aujourd'hui (applique les révisions arrivées à échéance). Retourne True si
        un changement a été appliqué."""
        revisions = await RentRevisionService.list_for_lease(db, lease.id)
        if not revisions:
            return False
        rent, charges = RentRevisionService.effective_amounts(lease, revisions, date.today())
        changed = False
        if round(float(lease.rent_amount), 2) != round(rent, 2):
            lease.rent_amount = round(rent, 2)
            changed = True
        if round(float(lease.charges_amount), 2) != round(charges, 2):
            lease.charges_amount = round(charges, 2)
            changed = True
        for r in revisions:
            if not r.applied and r.effective_date <= date.today():
                r.applied = True
                changed = True
        if changed:
            await db.flush()
        return changed
