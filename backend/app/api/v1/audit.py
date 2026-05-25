"""API Audit — journal des actions critiques (admin uniquement)."""
import uuid
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import get_current_active_admin
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_id: Optional[uuid.UUID]
    user_email: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    details: Optional[Any]
    ip_address: Optional[str]

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogOut], summary="Journal d'audit")
async def list_audit_logs(
    action: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
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
