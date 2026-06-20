"""API Offres & Services — gestion et consultation."""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.database import get_db
from app.models.lease import Lease
from app.models.offer import Offer
from app.models.user import User
from app.schemas.offer import OfferCreate, OfferResponse, OfferUpdate

router = APIRouter(prefix="/offers", tags=["Offres & Services"])

UPLOAD_DIR = "uploads/offers"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _is_gestionnaire(user: User) -> bool:
    return Role(user.role) in (Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO)


def _check_ownership(offer: Offer, user: User) -> None:
    if Role(user.role) == Role.ADMIN:
        return
    if offer.gestionnaire_id is None or str(offer.gestionnaire_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Cette offre ne vous appartient pas")


# ── Locataire : voir les offres de son gestionnaire ───────────────────────────


@router.get("/me", response_model=list[OfferResponse])
async def list_offers_for_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Offres actives visibles pour le locataire connecté."""
    # Trouver le bail actif → gestionnaire (created_by)
    lease_result = await db.execute(
        select(Lease).where(
            Lease.tenant_id == current_user.id,
            Lease.is_active.is_(True),
        )
    )
    lease = lease_result.scalar_one_or_none()
    if not lease or not lease.created_by:
        return []

    result = await db.execute(
        select(Offer)
        .where(
            Offer.gestionnaire_id == lease.created_by,
            Offer.is_active.is_(True),
        )
        .order_by(Offer.created_at.desc())
    )
    return list(result.scalars().all())


# ── Gestionnaire : CRUD offres ────────────────────────────────────────────────


@router.get("", response_model=list[OfferResponse])
async def list_offers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if Role(current_user.role) == Role.ADMIN:
        result = await db.execute(select(Offer).order_by(Offer.created_at.desc()))
    else:
        result = await db.execute(
            select(Offer)
            .where(Offer.gestionnaire_id == current_user.id)
            .order_by(Offer.created_at.desc())
        )
    return list(result.scalars().all())


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    data: OfferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    offer = Offer(**data.model_dump(), gestionnaire_id=current_user.id)
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    return offer


@router.patch("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: uuid.UUID,
    data: OfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    _check_ownership(offer, current_user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offer, field, value)
    await db.commit()
    await db.refresh(offer)
    return offer


@router.post("/{offer_id}/upload-image", response_model=OfferResponse)
async def upload_offer_image(
    offer_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    _check_ownership(offer, current_user)
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        raise HTTPException(status_code=400, detail="Format non supporté (PNG, JPG, WebP, GIF)")
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"offer_{offer_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    offer.image_url = f"/uploads/offers/{filename}"
    await db.commit()
    await db.refresh(offer)
    return offer


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    _check_ownership(offer, current_user)
    await db.delete(offer)
    await db.commit()
