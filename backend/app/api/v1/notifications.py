import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import Role
from app.database import get_db
from app.models.lease import Lease
from app.models.message import ProprietaireMessage
from app.models.property import Property
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await NotificationService.get_unread_count(db, current_user.id)
    return UnreadCountResponse(count=count)


@router.get("/badge")
async def get_badge_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compteur global cloche : notifications + messages non lus + tickets ouverts."""
    role = Role(current_user.role)

    # ── Messages propriétaire ↔ gestionnaire ──────────────────────────────────
    msg_count = 0
    if role == Role.PROPRIETAIRE:
        res = await db.execute(
            select(func.count(ProprietaireMessage.id)).where(
                ProprietaireMessage.proprietaire_id == current_user.id,
                ProprietaireMessage.is_from_gestionnaire.is_(True),
                ProprietaireMessage.is_read.is_(False),
            )
        )
        msg_count = res.scalar_one()
    elif role == Role.ADMIN:
        res = await db.execute(
            select(func.count(ProprietaireMessage.id)).where(
                ProprietaireMessage.is_from_gestionnaire.is_(False),
                ProprietaireMessage.is_read.is_(False),
            )
        )
        msg_count = res.scalar_one()
    elif role == Role.GESTIONNAIRE:
        # Mandataire : messages des propriétaires de SON agence uniquement.
        from app.api.v1._isolation import agency_member_ids
        from app.models.owner import Owner

        members = await agency_member_ids(db, current_user)
        prop_ids = [
            u
            for u in (
                await db.execute(
                    select(Owner.user_id).where(
                        Owner.created_by.in_(members), Owner.user_id.isnot(None)
                    )
                )
            )
            .scalars()
            .all()
        ]
        if prop_ids:
            res = await db.execute(
                select(func.count(ProprietaireMessage.id)).where(
                    ProprietaireMessage.proprietaire_id.in_(prop_ids),
                    ProprietaireMessage.is_from_gestionnaire.is_(False),
                    ProprietaireMessage.is_read.is_(False),
                )
            )
            msg_count = res.scalar_one()

    # ── Tickets / Incidents ───────────────────────────────────────────────────
    inc_count = 0
    if role == Role.ADMIN:
        res = await db.execute(select(func.count(Ticket.id)).where(Ticket.status == "open"))
        inc_count = res.scalar_one()
    elif role == Role.GESTIONNAIRE:
        # Mandataire : incidents ouverts des locataires de SON agence.
        from app.api.v1._isolation import agency_tenant_ids

        allowed = await agency_tenant_ids(db, current_user)
        if allowed:
            res = await db.execute(
                select(func.count(Ticket.id)).where(
                    Ticket.tenant_id.in_(allowed), Ticket.status == "open"
                )
            )
            inc_count = res.scalar_one()
    elif role == Role.GESTIONNAIRE_PROPRIO:
        prop_ids = [
            row[0]
            for row in (
                await db.execute(
                    select(Property.id).where(Property.owner_user_id == current_user.id)
                )
            ).all()
        ]
        if prop_ids:
            tenant_ids = [
                row[0]
                for row in (
                    await db.execute(
                        select(Lease.tenant_id).where(Lease.property_id.in_(prop_ids)).distinct()
                    )
                ).all()
            ]
            if tenant_ids:
                res = await db.execute(
                    select(func.count(Ticket.id)).where(
                        Ticket.tenant_id.in_(tenant_ids),
                        Ticket.status == "open",
                    )
                )
                inc_count = res.scalar_one()
    elif role == Role.PROPRIETAIRE:
        prop_ids = [
            row[0]
            for row in (
                await db.execute(
                    select(Property.id).where(Property.owner_user_id == current_user.id)
                )
            ).all()
        ]
        if prop_ids:
            tenant_ids = [
                row[0]
                for row in (
                    await db.execute(
                        select(Lease.tenant_id).where(Lease.property_id.in_(prop_ids)).distinct()
                    )
                ).all()
            ]
            if tenant_ids:
                res = await db.execute(
                    select(func.count(Ticket.id)).where(
                        Ticket.tenant_id.in_(tenant_ids),
                        Ticket.status == "open",
                    )
                )
                inc_count = res.scalar_one()
    # Locataire : plus de « Mes démarches » → on ne compte plus de tickets pour lui
    # (la cloche ne reflète que ses vraies notifications).

    notif_count = await NotificationService.get_unread_count(db, current_user.id)
    total = msg_count + inc_count + notif_count
    return {
        "total": total,
        "messages": msg_count,
        "incidents": inc_count,
        "notifications": notif_count,
    }


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total, unread_count = await NotificationService.list_for_user(
        db, current_user.id, unread_only=unread_only, limit=limit
    )
    return NotificationListResponse(items=items, total=total, unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = await NotificationService.mark_read(db, notification_id, current_user.id)
    await db.commit()
    return notif


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await NotificationService.mark_all_read(db, current_user.id)
    await db.commit()
    return {"marked_read": count}


@router.post("/generate-alerts")
async def generate_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Déclenche manuellement la génération d'alertes (admin uniquement)."""
    if Role(current_user.role) != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs"
        )
    late = await NotificationService.generate_late_payment_alerts(db)
    expiring = await NotificationService.generate_expiring_lease_alerts(db)
    await db.commit()
    return {"late_payment_alerts": late, "expiring_lease_alerts": expiring}
