"""API Automatisation — règles d'envoi automatique et communications groupées."""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.automation import AutomationRule, CommunicationLog, RuleType
from app.models.tenant import Tenant
from app.models.lease import Lease
from app.schemas.automation import (
    AutomationRuleCreate, AutomationRuleUpdate, AutomationRuleResponse,
    CommunicationLogResponse, GroupCommunicationRequest,
)

router = APIRouter(prefix="/automation", tags=["Automatisation"])


# ── Règles d'automatisation ───────────────────────────────────────────────────

@router.get("/rules", response_model=List[AutomationRuleResponse])
async def list_rules(
    rule_type: Optional[RuleType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    q = select(AutomationRule)
    if rule_type:
        q = q.where(AutomationRule.rule_type == rule_type)
    q = q.order_by(AutomationRule.rule_type, AutomationRule.trigger_days)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    rule = AutomationRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    return rule


@router.patch("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    await db.delete(rule)
    await db.commit()


@router.post("/rules/{rule_id}/toggle", response_model=AutomationRuleResponse)
async def toggle_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    rule.is_active = not rule.is_active
    await db.commit()
    await db.refresh(rule)
    return rule


# ── Logs de communication ─────────────────────────────────────────────────────

@router.get("/logs", response_model=List[CommunicationLogResponse])
async def list_logs(
    tenant_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    q = select(CommunicationLog)
    if tenant_id:
        q = q.where(CommunicationLog.tenant_id == tenant_id)
    q = q.order_by(CommunicationLog.sent_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Communication groupée ─────────────────────────────────────────────────────

@router.post("/send-group", status_code=status.HTTP_200_OK)
async def send_group_communication(
    data: GroupCommunicationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    """Envoie une communication groupée à tous les locataires (ou filtrée)."""
    # Récupérer les locataires cibles
    q = select(Tenant).join(Lease, Lease.tenant_id == Tenant.id).where(Lease.is_active.is_(True))
    if data.tenant_ids:
        q = q.where(Tenant.id.in_(data.tenant_ids))
    if data.property_ids:
        q = q.where(Lease.property_id.in_(data.property_ids))

    result = await db.execute(q)
    tenants = list(result.scalars().all())

    sent_count = 0
    errors = []

    for tenant in tenants:
        recipient = None
        if data.channel.value in ("email", "email_sms"):
            recipient = tenant.email
        elif data.channel.value == "sms":
            recipient = tenant.phone

        if not recipient:
            continue

        # Enregistrer le log (simulé — intégration réelle à connecter)
        log = CommunicationLog(
            tenant_id=tenant.id,
            channel=data.channel.value,
            recipient=recipient,
            subject=data.subject,
            body=data.body,
            status="simulated",
            sent_at=datetime.utcnow(),
        )
        db.add(log)
        sent_count += 1

    await db.commit()

    return {
        "sent_count": sent_count,
        "total_targets": len(tenants),
        "errors": errors,
        "message": f"Communication envoyée à {sent_count} destinataire(s)"
    }
