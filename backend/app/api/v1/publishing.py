# -*- coding: utf-8 -*-
"""Diffusion d'annonces (gestionnaire) : plateformes de partage + annonce par bien.

- Plateformes : cibles de partage libres, définies au préalable et réutilisables.
- Annonce : contenu/photos pré-enregistrés par bien, actualisables, puis publication
  immédiate ou programmée sur une page d'annonce publique partageable.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import Role
from app.database import get_db
from app.models.property import Property
from app.models.publishing import Listing, PublishPlatform
from app.models.user import User
from app.services.listing_service import ListingService, build_photo_url, generate_listing_draft

router = APIRouter(prefix="/publishing", tags=["Diffusion"])


# ── Schémas ────────────────────────────────────────────────────────────────────
class PlatformIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    kind: str = Field("lien", pattern="^(reseau|site|email|lien|autre)$")
    target: Optional[str] = Field(None, max_length=400)
    is_active: bool = True


class PlatformOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    target: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ListingIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    photo_ids: Optional[list[str]] = None
    platform_ids: Optional[list[str]] = None


class ScheduleIn(BaseModel):
    scheduled_at: datetime


# ── Helpers d'isolation ──────────────────────────────────────────────────────
async def _own_platform(db: AsyncSession, user: User, platform_id: uuid.UUID) -> PublishPlatform:
    p = await db.get(PublishPlatform, platform_id)
    if not p or (Role(user.role) != Role.ADMIN and p.owner_user_id != user.id):
        raise NotFoundException("Plateforme", str(platform_id))
    return p


async def _accessible_property(db: AsyncSession, user: User, property_id: uuid.UUID) -> Property:
    prop = await db.get(Property, property_id)
    if not prop:
        raise NotFoundException("Bien", str(property_id))
    role = Role(user.role)
    if role == Role.ADMIN or prop.created_by == user.id or prop.owner_user_id == user.id:
        return prop
    from app.api.v1._isolation import agency_property_ids
    if prop.id in await agency_property_ids(db, user):
        return prop
    raise ForbiddenException("Ce bien n'est pas dans votre périmètre.")


async def _listing_out(db: AsyncSession, listing: Listing) -> dict:
    available = await ListingService.property_photos(db, listing.property_id)
    return {
        "id": listing.id,
        "property_id": listing.property_id,
        "title": listing.title,
        "description": listing.description,
        "price": float(listing.price) if listing.price is not None else None,
        "photo_ids": listing.photo_ids or [],
        "platform_ids": listing.platform_ids or [],
        "status": listing.status,
        "public_token": listing.public_token,
        "public_path": f"/annonce/{listing.public_token}" if listing.public_token else None,
        "scheduled_at": listing.scheduled_at,
        "published_at": listing.published_at,
        "views_count": int(listing.views_count or 0),
        "last_viewed_at": listing.last_viewed_at,
        "available_photos": available,
    }


# ── Plateformes de diffusion ───────────────────────────────────────────────────
@router.get("/platforms", response_model=list[PlatformOut], summary="Mes plateformes de diffusion")
async def list_platforms(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    rows = (await db.execute(
        select(PublishPlatform).where(PublishPlatform.owner_user_id == user.id)
        .order_by(PublishPlatform.created_at)
    )).scalars().all()
    return rows


@router.post("/platforms", response_model=PlatformOut, status_code=201, summary="Ajouter une plateforme")
async def create_platform(
    data: PlatformIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    p = PublishPlatform(
        owner_user_id=user.id, name=data.name.strip(), kind=data.kind,
        target=(data.target or "").strip() or None, is_active=data.is_active,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.put("/platforms/{platform_id}", response_model=PlatformOut, summary="Modifier une plateforme")
async def update_platform(
    platform_id: uuid.UUID,
    data: PlatformIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    p = await _own_platform(db, user, platform_id)
    p.name = data.name.strip()
    p.kind = data.kind
    p.target = (data.target or "").strip() or None
    p.is_active = data.is_active
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/platforms/{platform_id}", status_code=204, summary="Supprimer une plateforme")
async def delete_platform(
    platform_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    p = await _own_platform(db, user, platform_id)
    await db.delete(p)
    await db.commit()


# ── Vue d'ensemble des annonces (suivi des performances) ─────────────────────
@router.get("/listings", summary="Mes annonces — statut et performances")
async def list_listings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Statut + statistiques (vues) de chaque annonce du périmètre du gestionnaire,
    indexés par bien — alimente la vue d'ensemble de la page Publication."""
    role = Role(user.role)
    if role == Role.ADMIN:
        prop_ids = None
    elif role == Role.GESTIONNAIRE_PROPRIO:
        prop_ids = set((await db.execute(
            select(Property.id).where(
                (Property.created_by == user.id) | (Property.owner_user_id == user.id)
            )
        )).scalars().all())
    else:
        from app.api.v1._isolation import agency_property_ids
        prop_ids = await agency_property_ids(db, user)

    q = select(Listing)
    if prop_ids is not None:
        if not prop_ids:
            return []
        q = q.where(Listing.property_id.in_(prop_ids))
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "property_id": l.property_id,
            "status": l.status,
            "public_path": f"/annonce/{l.public_token}" if l.public_token and l.status == "published" else None,
            "scheduled_at": l.scheduled_at,
            "published_at": l.published_at,
            "views_count": int(l.views_count or 0),
            "last_viewed_at": l.last_viewed_at,
        }
        for l in rows
    ]


# ── Annonce d'un bien ───────────────────────────────────────────────────────────
@router.get("/properties/{property_id}/listing", summary="Annonce d'un bien")
async def get_listing(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await db.commit()
    return await _listing_out(db, listing)


@router.put("/properties/{property_id}/listing", summary="Enregistrer le contenu de l'annonce")
async def save_listing(
    property_id: uuid.UUID,
    data: ListingIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await ListingService.update(db, listing, data.model_dump(exclude_unset=True))
    await db.commit()
    return await _listing_out(db, listing)


@router.delete("/properties/{property_id}/photos/{document_id}", status_code=204,
               summary="Supprimer définitivement une photo du bien")
async def delete_property_photo(
    property_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Supprime la photo (fichier + document) et la retire de l'annonce si présente."""
    from app.models.document import Document
    from app.services.document_service import DocumentService

    await _accessible_property(db, user, property_id)
    doc = await db.get(Document, document_id)
    et = getattr(doc.entity_type, "value", doc.entity_type) if doc else None
    if not doc or et != "property" or doc.entity_id != property_id:
        raise NotFoundException("Photo", str(document_id))
    await DocumentService.delete(db, document_id)

    listing = (await db.execute(
        select(Listing).where(Listing.property_id == property_id)
    )).scalar_one_or_none()
    if listing and listing.photo_ids:
        kept = [x for x in listing.photo_ids if str(x) != str(document_id)]
        if kept != listing.photo_ids:
            listing.photo_ids = kept
    await db.commit()


@router.post("/properties/{property_id}/listing/generate", summary="Rédiger l'annonce avec l'IA")
async def generate_listing(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Propose un titre + une description rédigés à partir des caractéristiques
    connues du bien (LLM si configuré, sinon modèle). Non enregistré : à éditer
    puis sauvegarder."""
    prop = await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await db.commit()
    draft = await generate_listing_draft(prop, listing.price)
    return draft


@router.post("/properties/{property_id}/listing/publish", summary="Publier maintenant")
async def publish_listing(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await ListingService.publish(db, listing)
    await db.commit()
    return await _listing_out(db, listing)


@router.post("/properties/{property_id}/listing/schedule", summary="Programmer la publication")
async def schedule_listing(
    property_id: uuid.UUID,
    data: ScheduleIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await ListingService.schedule(db, listing, data.scheduled_at)
    await db.commit()
    return await _listing_out(db, listing)


@router.post("/properties/{property_id}/listing/unpublish", summary="Dépublier l'annonce")
async def unpublish_listing(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    await _accessible_property(db, user, property_id)
    listing = await ListingService.get_or_create(db, property_id, user.id)
    await ListingService.unpublish(db, listing)
    await db.commit()
    return await _listing_out(db, listing)
