import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import require_role, Role
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    count = await NotificationService.get_unread_count(db, current_user.id)
    return UnreadCountResponse(count=count)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    items, total, unread_count = await NotificationService.list_for_user(
        db, current_user.id, unread_only=unread_only, limit=limit
    )
    return NotificationListResponse(items=items, total=total, unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    notif = await NotificationService.mark_read(db, notification_id)
    await db.commit()
    return notif


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    count = await NotificationService.mark_all_read(db, current_user.id)
    await db.commit()
    return {"marked_read": count}


@router.post("/generate-alerts")
async def generate_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Déclenche manuellement la génération d'alertes (admin uniquement)."""
    late = await NotificationService.generate_late_payment_alerts(db)
    expiring = await NotificationService.generate_expiring_lease_alerts(db)
    await db.commit()
    return {"late_payment_alerts": late, "expiring_lease_alerts": expiring}
