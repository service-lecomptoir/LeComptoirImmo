"""Journal d'audit PAR AGENCE (applicatif).

À la différence du journal interne (`internal_admin.py`, réservé à la supervision
Portail360 et qui voit toutes les agences), cet endpoint est destiné au
GESTIONNAIRE : il ne renvoie que les actions des comptes de SA propre agence
(lui-même, ses comptables, ses propriétaires, ses locataires). L'isolation
repose sur `agency_member_ids` (périmètre `COALESCE(agency_id, id)`), garantissant
qu'un gestionnaire ne voit jamais les autres agences.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_manager
from app.api.v1._isolation import agency_member_ids
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogOut(BaseModel):
    id: Any
    created_at: datetime
    user_id: Any | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: Any | None
    details: Any | None
    ip_address: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogOut])
async def list_agency_audit(
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
):
    """Journal d'audit de l'agence du gestionnaire courant (lecture). Le comptable
    a le même périmètre que son gestionnaire. Filtre sur l'acteur ∈ agence."""
    member_ids = await agency_member_ids(db, current_user)
    if not member_ids:
        return []
    q = select(AuditLog).where(AuditLog.user_id.in_(member_ids))
    if action:
        q = q.where(AuditLog.action == action)
    if user_email:
        q = q.where(AuditLog.user_email.ilike(f"%{user_email}%"))
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    q = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()
