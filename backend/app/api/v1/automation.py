"""API Automatisation — règles d'envoi automatique et communications groupées."""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.models.automation import AutomationRule, CommunicationLog, RuleType
from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.user import User
from app.schemas.automation import (
    AutomationRuleCreate, AutomationRuleUpdate, AutomationRuleResponse,
    CommunicationLogResponse, GroupCommunicationRequest,
)

router = APIRouter(prefix="/automation", tags=["Automatisation"])


async def _check_rule_access(rule: AutomationRule, current_user: User, db: AsyncSession) -> None:
    """Vérifie que l'utilisateur a le droit d'accéder à cette règle."""
    role = Role(current_user.role)
    if role == Role.ADMIN:
        return
    if role == Role.GESTIONNAIRE_PROPRIO:
        if rule.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Accès refusé")
    elif role == Role.GESTIONNAIRE:
        from app.api.v1._isolation import gp_user_ids
        gp_ids = await gp_user_ids(db)
        if rule.created_by in gp_ids:
            raise HTTPException(status_code=403, detail="Accès refusé")


# ── Règles d'automatisation ───────────────────────────────────────────────────

@router.get("/rules", response_model=List[AutomationRuleResponse])
async def list_rules(
    rule_type: Optional[RuleType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    role = Role(current_user.role)
    q = select(AutomationRule)

    # ── Scope par rôle ────────────────────────────────────────────────────────
    if role == Role.GESTIONNAIRE_PROPRIO:
        q = q.where(AutomationRule.created_by == current_user.id)
    elif role == Role.GESTIONNAIRE:
        from app.api.v1._isolation import gp_user_ids
        gp_ids = await gp_user_ids(db)
        if gp_ids:
            q = q.where(
                or_(AutomationRule.created_by.not_in(gp_ids), AutomationRule.created_by.is_(None))
            )
    # Admin : pas de filtre

    if rule_type:
        q = q.where(AutomationRule.rule_type == rule_type)
    q = q.order_by(AutomationRule.rule_type, AutomationRule.trigger_days)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    rule = AutomationRule(**data.model_dump(), created_by=current_user.id)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    await _check_rule_access(rule, current_user, db)
    return rule


@router.patch("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    await _check_rule_access(rule, current_user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    await _check_rule_access(rule, current_user, db)
    await db.delete(rule)
    await db.commit()


@router.post("/rules/{rule_id}/toggle", response_model=AutomationRuleResponse)
async def toggle_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    await _check_rule_access(rule, current_user, db)
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
    current_user: User = Depends(get_current_gestionnaire),
):
    role = Role(current_user.role)
    q = select(CommunicationLog)

    # ── Scope par rôle ────────────────────────────────────────────────────────
    if role == Role.GESTIONNAIRE_PROPRIO:
        from app.api.v1._isolation import gp_tenant_ids as _gp_tenant_ids
        from app.models.property import Property
        # Logs liés aux locataires du GP
        my_tenant_ids = (await db.execute(
            select(Tenant.id).where(Tenant.created_by == current_user.id)
        )).scalars().all()
        if my_tenant_ids:
            q = q.where(CommunicationLog.tenant_id.in_(my_tenant_ids))
        else:
            return []
    elif role == Role.GESTIONNAIRE:
        from app.api.v1._isolation import gp_tenant_ids
        excl_tenants = await gp_tenant_ids(db)
        if excl_tenants:
            q = q.where(
                or_(
                    CommunicationLog.tenant_id.not_in(excl_tenants),
                    CommunicationLog.tenant_id.is_(None),
                )
            )

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
    current_user: User = Depends(get_current_gestionnaire),
):
    """Envoie une communication groupée aux locataires du gestionnaire (isolé par rôle)."""
    role = Role(current_user.role)

    q = select(Tenant).join(Lease, Lease.tenant_id == Tenant.id).where(Lease.is_active.is_(True))

    # ── Scope isolation ───────────────────────────────────────────────────────
    if role == Role.GESTIONNAIRE_PROPRIO:
        # Seulement les locataires créés par ce GP
        q = q.where(Tenant.created_by == current_user.id)
    elif role == Role.GESTIONNAIRE:
        # Exclure les locataires GP
        from app.api.v1._isolation import gp_tenant_ids
        excl = await gp_tenant_ids(db)
        if excl:
            q = q.where(Tenant.id.not_in(excl))

    # ── Filtres utilisateur ───────────────────────────────────────────────────
    if data.tenant_ids:
        q = q.where(Tenant.id.in_(data.tenant_ids))
    if data.property_ids:
        q = q.where(Lease.property_id.in_(data.property_ids))

    result = await db.execute(q)
    tenants = list(result.scalars().all())

    from app.services.email_service import send_group_message

    sent_count = 0
    errors = []

    for tenant in tenants:
        recipient = None
        is_email = data.channel.value in ("email", "email_sms")
        if is_email:
            recipient = tenant.email
        elif data.channel.value == "sms":
            recipient = tenant.phone

        if not recipient:
            continue

        # Envoi réel si SMTP configuré, sinon log "simulated"
        email_sent = False
        if is_email and recipient:
            email_sent = await send_group_message(recipient, data.subject, data.body)

        log = CommunicationLog(
            tenant_id=tenant.id,
            channel=data.channel.value,
            recipient=recipient,
            subject=data.subject,
            body=data.body,
            status="sent" if email_sent else "simulated",
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
