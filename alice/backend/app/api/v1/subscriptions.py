import uuid
import calendar
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import AliceAdmin
from app.models.subscription_request import AliceSubscriptionRequest
from app.models.leci import LeciUser
from app.models.license import AliceLicense
from app.schemas.subscription_request import SubscriptionRequestOut, SubscriptionRequestUpdate
from app.core.deps import get_current_alice_admin
from app.services.block_service import unblock_gestionnaire

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


@router.post("/{request_id}/deactivate-account")
async def deactivate_account_from_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Traite une demande de résiliation : programme la désactivation du compte
    gestionnaire à la fin du mois de facturation en cours (accès maintenu jusque-là,
    puis blocage appliqué automatiquement). Sans licence/compte trouvé : demande
    simplement marquée traitée."""
    req = (await db.execute(
        select(AliceSubscriptionRequest).where(AliceSubscriptionRequest.id == request_id)
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    user = (await db.execute(
        select(LeciUser).where(func.lower(LeciUser.email) == (req.email or "").lower())
    )).scalar_one_or_none()

    scheduled_until: Optional[datetime] = None
    blocked_now = False
    if user is not None:
        lic = (await db.execute(
            select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user.id)
        )).scalar_one_or_none()
        if lic is not None and not lic.is_blocked:
            now = datetime.utcnow()
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_of_month = datetime(now.year, now.month, last_day, 23, 59, 59)
            if end_of_month > now:
                lic.access_until = end_of_month
                scheduled_until = end_of_month
            else:
                lic.is_blocked = True
                blocked_now = True

    req.status = "traite"
    if req.processed_at is None:
        req.processed_at = datetime.utcnow()
    await db.flush()
    return {
        "found_account": user is not None,
        "scheduled_until": scheduled_until.isoformat() if scheduled_until else None,
        "blocked_now": blocked_now,
    }


@router.post("/{request_id}/reactivate-account")
async def reactivate_account_from_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Annule la désactivation programmée d'un compte (suite à une demande de
    résiliation) : efface access_until et débloque le compte s'il était déjà
    bloqué. Sans licence/compte trouvé, ou si rien n'était programmé, renvoie
    simplement l'état (reactivated=False)."""
    req = (await db.execute(
        select(AliceSubscriptionRequest).where(AliceSubscriptionRequest.id == request_id)
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    user = (await db.execute(
        select(LeciUser).where(func.lower(LeciUser.email) == (req.email or "").lower())
    )).scalar_one_or_none()

    was_scheduled = False
    was_blocked = False
    reactivated = False
    if user is not None:
        lic = (await db.execute(
            select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user.id)
        )).scalar_one_or_none()
        if lic is not None:
            was_scheduled = lic.access_until is not None
            was_blocked = lic.is_blocked
            if was_scheduled:
                lic.access_until = None
            if was_blocked:
                await unblock_gestionnaire(db, lic, user.id)
            reactivated = was_scheduled or was_blocked

    await db.flush()
    return {
        "found_account": user is not None,
        "reactivated": reactivated,
        "was_scheduled": was_scheduled,
        "was_blocked": was_blocked,
    }


@router.delete("/{request_id}", status_code=204)
async def delete_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Supprime définitivement une demande (souscription ou résiliation)."""
    req = (await db.execute(
        select(AliceSubscriptionRequest).where(AliceSubscriptionRequest.id == request_id)
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    await db.delete(req)
    return Response(status_code=204)
