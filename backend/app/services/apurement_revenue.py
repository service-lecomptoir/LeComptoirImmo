"""Revenu d'apurement (modèle A) : utilitaires partagés.

Un mois reporté sur un plan d'apurement passe en statut « annulé » (settled_by_plan) :
sa part déjà payée doit toujours compter comme encaissée. Le reste reporté est
ensuite reconnu au fil des échéances réellement payées du plan. Ces utilitaires
centralisent ces deux règles pour le tableau de bord, la performance et le fiscal.
"""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apurement_plan import ApurementPlan
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus


def received_status():
    """Filtre SQL des paiements comptés comme « encaissé » : payé / partiel, ET
    les mois reportés sur un plan d'apurement (leur part déjà payée compte)."""
    return or_(
        Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
        Payment.settled_by_plan.is_(True),
    )


async def apurement_installments(db: AsyncSession, prop_ids, *, year=None, month=None):
    """Échéances d'apurement réellement encaissées sur la période, avec contexte.

    `prop_ids=None` => tout le périmètre. Retourne une liste de dicts :
    { plan, seq, amount, date }.
    """
    q = select(ApurementPlan)
    if prop_ids is not None:
        if not prop_ids:
            return []
        q = q.join(Lease, ApurementPlan.lease_id == Lease.id).where(
            Lease.property_id.in_(list(prop_ids))
        )
    plans = (await db.execute(q)).scalars().all()
    rows = []
    for pl in plans:
        for it in pl.installments or []:
            if not it.get("paid"):
                continue
            raw = it.get("paid_date") or it.get("due_date")
            try:
                d = date.fromisoformat(raw) if raw else None
            except Exception:
                d = None
            if not d:
                continue
            if year is not None and d.year != year:
                continue
            if month is not None and d.month != month:
                continue
            rows.append(
                {
                    "plan": pl,
                    "seq": it.get("seq"),
                    "amount": float(it.get("amount", 0) or 0),
                    "date": d,
                }
            )
    return rows


async def apurement_received(db: AsyncSession, prop_ids, *, year=None, month=None) -> float:
    """Somme des échéances d'apurement encaissées sur la période."""
    rows = await apurement_installments(db, prop_ids, year=year, month=month)
    return round(sum(r["amount"] for r in rows), 2)
