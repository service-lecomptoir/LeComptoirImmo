from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.database import get_db
from app.models.admin import ProxygenAdmin
from app.models.license import ProxygenLicense
from app.models.plan import ProxygenPlan
from app.models.leci import LeciUser
from app.core.deps import get_current_proxygen_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Statistiques globales pour le dashboard ProxyGen."""

    # Total gestionnaires dans LeCI (role = gestionnaire)
    gest_result = await db.execute(
        select(
            func.count(LeciUser.id).label("total"),
            func.count(case((LeciUser.is_active == True, 1))).label("actifs"),
        ).where(LeciUser.role_eq("gestionnaire"))
    )
    gest_row = gest_result.fetchone()
    total_gestionnaires = gest_row.total if gest_row else 0
    total_actifs = gest_row.actifs if gest_row else 0

    # Total gestionnaires bloqués via proxygen_licenses
    blocked_result = await db.execute(
        select(func.count(ProxygenLicense.id)).where(ProxygenLicense.is_blocked == True)
    )
    total_bloques = blocked_result.scalar_one_or_none() or 0

    # Total propriétaires
    prop_result = await db.execute(
        select(func.count(LeciUser.id)).where(LeciUser.role_eq("proprietaire"))
    )
    total_proprietaires = prop_result.scalar_one_or_none() or 0

    # Total locataires
    loc_result = await db.execute(
        select(func.count(LeciUser.id)).where(LeciUser.role_eq("locataire"))
    )
    total_locataires = loc_result.scalar_one_or_none() or 0

    # Distribution plans
    plans_result = await db.execute(
        select(ProxygenPlan.name, func.count(ProxygenLicense.id).label("count"))
        .outerjoin(ProxygenLicense, ProxygenLicense.plan_id == ProxygenPlan.id)
        .where(ProxygenPlan.is_active == True)
        .group_by(ProxygenPlan.id, ProxygenPlan.name)
        .order_by(func.count(ProxygenLicense.id).desc())
    )
    plans_distribution = [
        {"name": row.name, "count": row.count}
        for row in plans_result.fetchall()
    ]

    return {
        "total_gestionnaires": total_gestionnaires,
        "gestionnaires_actifs": total_actifs,
        "gestionnaires_bloques": total_bloques,
        "total_proprietaires": total_proprietaires,
        "total_locataires": total_locataires,
        "plans_distribution": plans_distribution,
    }
