import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apurement_plan import ApurementPlan


def compute_summary(installments: list, total: float) -> dict:
    """Résumé d'un plan : payé / restant / en retard, dérivé des échéances."""
    insts = installments or []
    paid_total = round(sum(float(i.get("amount", 0)) for i in insts if i.get("paid")), 2)
    remaining = round(float(total or 0) - paid_total, 2)
    today = date.today().isoformat()
    overdue = any(
        (not i.get("paid")) and i.get("due_date") and str(i["due_date"]) < today
        for i in insts
    )
    return {
        "paid_total": paid_total,
        "remaining": max(0.0, remaining),
        "paid_count": sum(1 for i in insts if i.get("paid")),
        "count": len(insts),
        "overdue": overdue,
    }


def plan_to_dict(plan: ApurementPlan, tenant_name=None, property_name=None) -> dict:
    insts = plan.installments or []
    total = float(plan.total_amount or 0)
    return {
        "id": plan.id,
        "lease_id": plan.lease_id,
        "tenant_id": plan.tenant_id,
        "tenant_name": tenant_name,
        "property_name": property_name,
        "total_amount": total,
        "installments": insts,
        "status": plan.status,
        "label": plan.label,
        "created_at": plan.created_at,
        **compute_summary(insts, total),
    }


class ApurementPlanService:

    @staticmethod
    async def create(db: AsyncSession, *, lease_id, tenant_id, origin_payment_id,
                     total, installments, created_by, label) -> ApurementPlan:
        plan = ApurementPlan(
            lease_id=lease_id, tenant_id=tenant_id, origin_payment_id=origin_payment_id,
            total_amount=total, installments=installments, created_by=created_by,
            label=label, status="active",
        )
        db.add(plan)
        await db.flush()
        return plan

    @staticmethod
    async def get(db: AsyncSession, plan_id: uuid.UUID) -> Optional[ApurementPlan]:
        return (await db.execute(
            select(ApurementPlan).where(ApurementPlan.id == plan_id)
        )).scalar_one_or_none()

    @staticmethod
    async def list_for_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> List[ApurementPlan]:
        return list((await db.execute(
            select(ApurementPlan)
            .where(ApurementPlan.tenant_id == tenant_id)
            .order_by(ApurementPlan.created_at.desc())
        )).scalars().all())

    @staticmethod
    async def mark_installment(db: AsyncSession, plan: ApurementPlan, seq: int,
                               paid: bool, paid_date) -> tuple[ApurementPlan, bool]:
        insts = [dict(i) for i in (plan.installments or [])]
        found = False
        for i in insts:
            if int(i.get("seq", -1)) == int(seq):
                i["paid"] = bool(paid)
                i["paid_date"] = (
                    paid_date.isoformat() if paid_date
                    else (date.today().isoformat() if paid else None)
                )
                if paid:
                    # Validation par le gestionnaire → on retire le drapeau « déclaré ».
                    i["declared"] = False
                    i["declared_date"] = None
                found = True
        plan.installments = insts  # réassignation pour que SQLAlchemy détecte le JSONB
        if plan.status != "cancelled":
            plan.status = "completed" if insts and all(i.get("paid") for i in insts) else "active"
        await db.flush()
        return plan, found

    @staticmethod
    async def declare_installment(db: AsyncSession, plan: ApurementPlan, seq: int,
                                  declared_date=None) -> tuple[ApurementPlan, bool]:
        """Le locataire déclare avoir réglé une échéance (en attente de validation
        du gestionnaire). On pose un drapeau `declared` sans marquer `paid`."""
        insts = [dict(i) for i in (plan.installments or [])]
        found = False
        for i in insts:
            if int(i.get("seq", -1)) == int(seq):
                if not i.get("paid"):
                    i["declared"] = True
                    i["declared_date"] = (declared_date or date.today()).isoformat()
                found = True
        plan.installments = insts
        await db.flush()
        return plan, found

    @staticmethod
    async def list_active_for_tenants(db: AsyncSession, tenant_ids) -> List[ApurementPlan]:
        tenant_ids = list(tenant_ids or [])
        if not tenant_ids:
            return []
        return list((await db.execute(
            select(ApurementPlan)
            .where(ApurementPlan.tenant_id.in_(tenant_ids),
                   ApurementPlan.status == "active")
            .order_by(ApurementPlan.created_at.desc())
        )).scalars().all())

    @staticmethod
    async def delete(db: AsyncSession, plan: ApurementPlan) -> None:
        await db.delete(plan)
        await db.flush()
