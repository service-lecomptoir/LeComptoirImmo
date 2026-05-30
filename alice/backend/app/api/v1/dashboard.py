from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, or_

from app.database import get_db
from app.models.admin import AliceAdmin
from app.models.license import AliceLicense
from app.models.plan import AlicePlan
from app.models.leci import LeciUser, LeciProperty
from app.core.deps import get_current_alice_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Statistiques globales enrichies pour le dashboard Alice."""

    # ── Gestionnaires ─────────────────────────────────────────────────────────
    gest_result = await db.execute(
        select(
            func.count(LeciUser.id).label("total"),
            func.count(case((LeciUser.is_active == True, 1))).label("actifs"),
        ).where(or_(LeciUser.role_eq("gestionnaire"), LeciUser.role_eq("gestionnaire_proprio")))
    )
    gest_row = gest_result.fetchone()
    total_gestionnaires = gest_row.total if gest_row else 0
    total_actifs = gest_row.actifs if gest_row else 0

    blocked_result = await db.execute(
        select(func.count(AliceLicense.id)).where(AliceLicense.is_blocked == True)
    )
    total_bloques = blocked_result.scalar_one_or_none() or 0

    # Biens "gérés" = biens rattachés à un gestionnaire (on exclut les orphelins
    # sans créateur ou créés par un non-gestionnaire) pour rester cohérent avec
    # la répartition par gestionnaire affichée plus bas.
    total_biens = (await db.execute(
        select(func.count(LeciProperty.id))
        .join(LeciUser, LeciUser.id == LeciProperty.created_by)
        .where(or_(LeciUser.role_eq("gestionnaire"), LeciUser.role_eq("gestionnaire_proprio")))
    )).scalar_one_or_none() or 0

    # ── MRR (Monthly Recurring Revenue) ──────────────────────────────────────
    # Pour chaque licence active non bloquée : override si présent, sinon prix du plan
    licenses_result = await db.execute(
        select(
            AliceLicense.monthly_price_override,
            AlicePlan.monthly_price,
        )
        .outerjoin(AlicePlan, AlicePlan.id == AliceLicense.plan_id)
        .where(AliceLicense.is_blocked == False)
    )
    mrr = 0.0
    for row in licenses_result.fetchall():
        price = float(row.monthly_price_override or row.monthly_price or 0)
        mrr += price

    # ── Distribution plans ────────────────────────────────────────────────────
    plans_result = await db.execute(
        select(
            AlicePlan.name,
            AlicePlan.monthly_price,
            func.count(AliceLicense.id).label("count"),
        )
        .outerjoin(AliceLicense, AliceLicense.plan_id == AlicePlan.id)
        .where(AlicePlan.is_active == True)
        .group_by(AlicePlan.id, AlicePlan.name, AlicePlan.monthly_price)
        .order_by(func.count(AliceLicense.id).desc())
    )
    plans_distribution = [
        {"name": row.name, "count": row.count, "monthly_price": float(row.monthly_price)}
        for row in plans_result.fetchall()
    ]

    # ── Alertes quota : gestionnaires proches de la limite ───────────────────
    # (utilisation biens >= 80% de la limite effective)
    quota_alerts = await _compute_quota_alerts(db)

    # ── Top gestionnaires par nb biens ────────────────────────────────────────
    top_result = await db.execute(
        select(
            LeciUser.id,
            LeciUser.email,
            LeciUser.full_name,
            func.count(LeciProperty.id).label("property_count"),
        )
        .outerjoin(LeciProperty, LeciProperty.created_by == LeciUser.id)
        .where(or_(LeciUser.role_eq("gestionnaire"), LeciUser.role_eq("gestionnaire_proprio")))
        .group_by(LeciUser.id, LeciUser.email, LeciUser.full_name)
        .order_by(func.count(LeciProperty.id).desc())
        .limit(5)
    )
    top_gestionnaires = [
        {"id": str(row.id), "email": row.email, "full_name": row.full_name, "property_count": row.property_count}
        for row in top_result.fetchall()
    ]

    return {
        "total_gestionnaires": total_gestionnaires,
        "gestionnaires_actifs": total_actifs,
        "gestionnaires_bloques": total_bloques,
        "total_biens": total_biens,
        "mrr": round(mrr, 2),
        "plans_distribution": plans_distribution,
        "quota_alerts": quota_alerts,
        "top_gestionnaires": top_gestionnaires,
    }


async def _compute_quota_alerts(db: AsyncSession) -> List[Dict[str, Any]]:
    """Gestionnaires utilisant >= 80% de leur quota de biens."""
    licenses_result = await db.execute(
        select(
            AliceLicense.gestionnaire_user_id,
            AliceLicense.property_limit_override,
            AlicePlan.property_limit,
            LeciUser.email,
            LeciUser.full_name,
        )
        .outerjoin(AlicePlan, AlicePlan.id == AliceLicense.plan_id)
        .outerjoin(LeciUser, LeciUser.id == AliceLicense.gestionnaire_user_id)
        .where(AliceLicense.is_blocked == False)
    )
    rows = licenses_result.fetchall()
    alerts = []
    for row in rows:
        effective_limit = row.property_limit_override if row.property_limit_override is not None else row.property_limit
        if effective_limit is None:
            continue  # illimité
        prop_count = (await db.execute(
            select(func.count(LeciProperty.id)).where(LeciProperty.created_by == row.gestionnaire_user_id)
        )).scalar_one_or_none() or 0
        usage_pct = (prop_count / effective_limit * 100) if effective_limit > 0 else 0
        if usage_pct >= 80:
            alerts.append({
                "user_id": str(row.gestionnaire_user_id),
                "email": row.email,
                "full_name": row.full_name,
                "property_count": prop_count,
                "property_limit": effective_limit,
                "usage_pct": round(usage_pct, 1),
            })
    return sorted(alerts, key=lambda x: x["usage_pct"], reverse=True)
