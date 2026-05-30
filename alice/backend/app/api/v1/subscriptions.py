import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import AliceAdmin
from app.models.subscription_request import AliceSubscriptionRequest
from app.schemas.subscription_request import SubscriptionRequestOut, SubscriptionRequestUpdate
from app.core.deps import get_current_alice_admin

router = APIRouter(prefix="/subscription-requests", tags=["Demandes de souscription"])


@router.get("", response_model=List[SubscriptionRequestOut])
async def list_requests(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Liste les demandes de souscription (les plus récentes d'abord)."""
    q = select(AliceSubscriptionRequest)
    if status:
        q = q.where(AliceSubscriptionRequest.status == status)
    q = q.order_by(AliceSubscriptionRequest.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def requests_stats(
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Compteurs par statut (pour badge / pastilles)."""
    result = await db.execute(
        select(AliceSubscriptionRequest.status, func.count(AliceSubscriptionRequest.id))
        .group_by(AliceSubscriptionRequest.status)
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
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Met à jour le statut / les notes d'une demande."""
    result = await db.execute(
        select(AliceSubscriptionRequest).where(AliceSubscriptionRequest.id == request_id)
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
