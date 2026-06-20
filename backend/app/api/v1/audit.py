"""API Audit — journal des actions critiques (admin uniquement)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_admin
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    details: Any | None
    ip_address: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogOut], summary="Journal d'audit")
async def list_audit_logs(
    action: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    entity_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    """Liste les entrées du journal d'audit (admin uniquement)."""
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    q = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
