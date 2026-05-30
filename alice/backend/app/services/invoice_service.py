import uuid
from datetime import datetime, date
from typing import Optional, Tuple

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import AliceInvoice
from app.models.license import AliceLicense
from app.models.plan import AlicePlan
from app.models.leci import LeciUser


def current_period() -> Tuple[int, int]:
    today = date.today()
    return today.year, today.month


async def generate_invoices_for_period(
    db: AsyncSession, year: int, month: int
) -> int:
    """Génère (idempotent) une facture par gestionnaire actif non bloqué pour la
    période donnée, du montant de sa formule. Retourne le nombre de factures créées."""
    # Factures déjà émises pour cette période
    existing_result = await db.execute(
        select(AliceInvoice.gestionnaire_user_id).where(
            AliceInvoice.period_year == year,
            AliceInvoice.period_month == month,
        )
    )
    already_billed = {row[0] for row in existing_result.all()}

    # Licences non bloquées + plan + user gestionnaire (rôles gestionnaire uniquement)
    licenses_result = await db.execute(
        select(
            AliceLicense.gestionnaire_user_id,
            AliceLicense.monthly_price_override,
            AlicePlan.name,
            AlicePlan.monthly_price,
        )
        .join(LeciUser, LeciUser.id == AliceLicense.gestionnaire_user_id)
        .outerjoin(AlicePlan, AlicePlan.id == AliceLicense.plan_id)
        .where(
            AliceLicense.is_blocked == False,
            or_(LeciUser.role_eq("gestionnaire"), LeciUser.role_eq("gestionnaire_proprio")),
        )
    )

    created = 0
    now = datetime.utcnow()
    for row in licenses_result.fetchall():
        if row.gestionnaire_user_id in already_billed:
            continue
        amount = row.monthly_price_override
        if amount is None:
            amount = row.monthly_price
        amount = float(amount or 0)
        # On ne facture pas un montant nul (gestionnaire sans formule assignée)
        if amount <= 0:
            continue
        invoice = AliceInvoice(
            id=uuid.uuid4(),
            gestionnaire_user_id=row.gestionnaire_user_id,
            period_year=year,
            period_month=month,
            amount=amount,
            plan_name=row.name,
            status="unpaid",
            paid_at=None,
            created_at=now,
        )
        db.add(invoice)
        created += 1

    if created:
        await db.flush()
    return created
