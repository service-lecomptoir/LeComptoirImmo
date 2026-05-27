import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import ProxygenAdmin
from app.models.subscription_request import ProxygenSubscriptionRequest
from app.schemas.subscription_request import SubscriptionRequestOut, SubscriptionRequestUpdate
from app.core.deps import get_current_proxygen_admin

router = APIRouter(prefix="/subscription-requests", tags=["Demandes de souscription"])


@router.get("", response_model=List[SubscriptionRequestOut])
async def list_requests(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Liste les demandes de souscription (les plus récentes d'abord)."""
    q = select(ProxygenSubscriptionRequest)
    if status:
        q = q.where(ProxygenSubscriptionRequest.status == status)
    q = q.order_by(ProxygenSubscriptionRequest.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def requests_stats(
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Compteurs par statut (pour badge / pastilles)."""
    result = await db.execute(
        select(ProxygenSubscriptionRequest.status, func.count(ProxygenSubscriptionRequest.id))
        .group_by(ProxygenSubscriptionRequest.status)
    )
    counts = {status: count for status, count in result.all()}
    return {
        "nouveau": counts.get("nouveau", 0),
        "en_cours": counts.get("en_cours", 0),
        "traite": counts.get("traite", 0),
        "rejete": counts.get("rejete", 0),
        "total": sum(counts.values()),
    }


@router.patch("/{request_id}", response_model=SubscriptionRequestOut)
async def update_request(
    request_id: uuid.UUID,
    data: SubscriptionRequestUpdate,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Met à jour le statut / les notes d'une demande."""
    result = await db.execute(
        select(ProxygenSubscriptionRequest).where(ProxygenSubscriptionRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    if data.status is not None:
        req.status = data.status
        if data.status in ("traite", "rejete") and req.processed_at is None:
            # Colonne TIMESTAMP WITHOUT TIME ZONE → datetime naïf (convention du projet)
            req.processed_at = datetime.utcnow()
    if data.notes is not None:
        req.notes = data.notes

    await db.flush()
    return req
