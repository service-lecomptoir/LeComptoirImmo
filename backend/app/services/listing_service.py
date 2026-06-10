# -*- coding: utf-8 -*-
"""Diffusion des annonces : contenu/photos pré-enregistrés par bien, publication
sur une page d'annonce hébergée + partage, et programmation de la publication.

Le canal de diffusion est une PAGE D'ANNONCE PUBLIQUE (URL à jeton non devinable)
servie par Le Comptoir ; les « plateformes » sont des cibles de partage libres
définies par le gestionnaire. La programmation s'appuie sur le scheduler APScheduler
(job `publish_scheduled_listings`).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.document import Document
from app.models.publishing import Listing


def build_photo_url(file_path: Optional[str]) -> Optional[str]:
    """URL servie pour un document uploadé (mount StaticFiles « /uploads »).

    `file_path` est stocké sous la forme « uploads/property/<id>/<fichier> » ;
    le fichier est exposé à « /uploads/property/<id>/<fichier> »."""
    if not file_path:
        return None
    p = str(file_path).replace("\\", "/").lstrip("/")
    return "/" + p


def _token() -> str:
    """Jeton d'URL publique court et non devinable."""
    return secrets.token_urlsafe(12)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ListingService:
    @staticmethod
    async def get_or_create(db: AsyncSession, property_id, user_id) -> Listing:
        listing = (await db.execute(
            select(Listing).where(Listing.property_id == property_id)
        )).scalar_one_or_none()
        if listing is None:
            listing = Listing(property_id=property_id, status="draft", created_by=user_id)
            db.add(listing)
            await db.flush()
        return listing

    @staticmethod
    async def update(
        db: AsyncSession,
        listing: Listing,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price=None,
        photo_ids: Optional[list] = None,
        platform_ids: Optional[list] = None,
    ) -> Listing:
        if title is not None:
            listing.title = title.strip() or None
        if description is not None:
            listing.description = description.strip() or None
        if price is not None:
            listing.price = price
        if photo_ids is not None:
            listing.photo_ids = [str(x) for x in photo_ids]
        if platform_ids is not None:
            listing.platform_ids = [str(x) for x in platform_ids]
        await db.flush()
        return listing

    @staticmethod
    async def publish(db: AsyncSession, listing: Listing) -> Listing:
        if not listing.public_token:
            listing.public_token = _token()
        listing.status = "published"
        listing.published_at = _now()
        listing.scheduled_at = None
        await db.flush()
        return listing

    @staticmethod
    async def schedule(db: AsyncSession, listing: Listing, when: datetime) -> Listing:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when <= _now():
            raise BadRequestException("La date de publication doit être dans le futur.")
        if not listing.public_token:
            listing.public_token = _token()
        listing.status = "scheduled"
        listing.scheduled_at = when
        await db.flush()
        return listing

    @staticmethod
    async def unpublish(db: AsyncSession, listing: Listing) -> Listing:
        listing.status = "unpublished"
        listing.scheduled_at = None
        await db.flush()
        return listing

    @staticmethod
    async def publish_due(db: AsyncSession) -> int:
        """Publie les annonces programmées dont l'échéance est atteinte (scheduler)."""
        now = _now()
        rows = (await db.execute(
            select(Listing).where(
                Listing.status == "scheduled",
                Listing.scheduled_at.isnot(None),
                Listing.scheduled_at <= now,
            )
        )).scalars().all()
        for listing in rows:
            listing.status = "published"
            listing.published_at = now
        return len(rows)

    @staticmethod
    async def property_photos(db: AsyncSession, property_id) -> list[dict]:
        """Documents-images rattachés au bien, candidats pour l'annonce."""
        docs = (await db.execute(
            select(Document).where(
                Document.entity_type == "property",
                Document.entity_id == property_id,
            ).order_by(Document.created_at)
        )).scalars().all()
        out = []
        for d in docs:
            mime = (d.mime_type or "").lower()
            if not mime.startswith("image/"):
                continue
            out.append({
                "id": str(d.id),
                "url": build_photo_url(d.file_path),
                "label": d.label or d.file_name,
            })
        return out
