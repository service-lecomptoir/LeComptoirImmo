"""Endpoint de performance par bien — loyer théorique vs perçu, par mois."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.property import Property
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus

router = APIRouter(prefix="/proprietaire-performance", tags=["Propriétaire Performance"])


@router.get("/{year}")
async def get_proprietaire_performance(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Performance des biens du propriétaire : loyer théorique vs perçu, par mois."""
    from app.core.permissions import Role as R
    from fastapi import HTTPException
    role = R(current_user.role)

    if role not in (R.PROPRIETAIRE, R.GESTIONNAIRE, R.GESTIONNAIRE_PROPRIO, R.ADMIN):
        raise HTTPException(status_code=403, detail="Accès refusé")

    proprietaire_id = current_user.id

    props_res = await db.execute(
        select(Property).where(Property.owner_user_id == proprietaire_id)
    )
    properties = list(props_res.scalars().all())

    today = date.today()
    months_elapsed = today.month if today.year == year else 12

    result_props = []
    for prop in properties:
        prop_id = prop.id

        # Loyer mensuel théorique = somme des baux actifs
        leases_res = await db.execute(
            select(
                func.coalesce(func.sum(Lease.rent_amount + Lease.charges_amount), 0.0)
            ).where(
                Lease.property_id == prop_id,
                Lease.is_active.is_(True),
            )
        )
        monthly_expected = float(leases_res.scalar_one() or 0)
        ytd_theoretical = monthly_expected * months_elapsed

        # Encaissé YTD (period_year == year, PAID ou PARTIAL)
        ytd_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop_id,
                Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                Payment.period_year == year,
            )
        )
        ytd_received = float(ytd_res.scalar_one() or 0)

        # Détail mensuel
        monthly_breakdown = []
        for month in range(1, months_elapsed + 1):
            m_res = await db.execute(
                select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
                .join(Lease, Payment.lease_id == Lease.id)
                .where(
                    Lease.property_id == prop_id,
                    Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                    Payment.period_year == year,
                    Payment.period_month == month,
                )
            )
            monthly_breakdown.append({
                "month": month,
                "expected": round(monthly_expected, 2),
                "received": round(float(m_res.scalar_one() or 0), 2),
            })

        collection_rate = round(
            (ytd_received / ytd_theoretical * 100) if ytd_theoretical > 0 else 0, 1
        )

        result_props.append({
            "property_id": str(prop_id),
            "property_name": prop.name,
            "monthly_expected": round(monthly_expected, 2),
            "ytd_theoretical": round(ytd_theoretical, 2),
            "ytd_received": round(ytd_received, 2),
            "collection_rate": collection_rate,
            "months_elapsed": months_elapsed,
            "monthly_breakdown": monthly_breakdown,
        })

    total_theoretical = sum(p["ytd_theoretical"] for p in result_props)
    total_received = sum(p["ytd_received"] for p in result_props)
    global_rate = round(
        (total_received / total_theoretical * 100) if total_theoretical > 0 else 0, 1
    )

    return {
        "year": year,
        "months_elapsed": months_elapsed,
        "total_theoretical": round(total_theoretical, 2),
        "total_received": round(total_received, 2),
        "global_collection_rate": global_rate,
        "properties": result_props,
    }
