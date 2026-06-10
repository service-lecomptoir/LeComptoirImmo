"""
Endpoints publics (sans authentification) — page d'accueil Le Comptoir Immo.

Les plans et les demandes de souscription/démo proviennent d'Alice (source de
vérité, base dédiée) via son API /internal (app.services.alice_client) — plus
aucune lecture/écriture directe des tables alice_*.
"""
import logging
import uuid
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import alice_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Public"])


class PublicPlanOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    property_limit: Optional[int] = None
    monthly_price: float
    features: Optional[List[str]] = None


@router.get("/plans", response_model=List[PublicPlanOut], summary="Plans tarifaires publics")
async def list_public_plans():
    """Plans actifs pour la page Tarification publique (via l'API Alice).
    `features = null` ⇒ toutes les fonctionnalités. Fail-soft → [] si Alice KO."""
    plans = await alice_client.list_plans()
    return [
        PublicPlanOut(
            id=str(p.get("id")),
            name=p.get("name"),
            description=p.get("description"),
            property_limit=p.get("property_limit"),
            monthly_price=float(p.get("monthly_price") or 0),
            features=p.get("features") if isinstance(p.get("features"), list) else None,
        )
        for p in plans
    ]


async def _notify_team(data: "SubscriptionRequestIn") -> None:
    """Best-effort : notifie l'équipe par email (n'échoue jamais la requête)."""
    try:
        from app.config import get_settings
        from app.services.email_service import send_subscription_lead_notification
        cfg = get_settings()
        recipient = cfg.LEADS_NOTIFY_EMAIL or cfg.FIRST_ADMIN_EMAIL
        await send_subscription_lead_notification(
            to=recipient,
            full_name=data.full_name.strip(),
            email=str(data.email).lower(),
            phone=data.phone,
            company=data.company,
            message=data.message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification de souscription non envoyée : %s", exc)


class SubscriptionRequestIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=30)
    company: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)


@router.post("/subscription-requests", status_code=201, summary="Demande de souscription / démo")
async def create_subscription_request(
    data: SubscriptionRequestIn,
    background: BackgroundTasks,
):
    """Enregistre une demande publique côté Alice (à traiter dans « Demandes »)."""
    await alice_client.create_lead(
        full_name=data.full_name.strip(),
        email=str(data.email).lower(),
        phone=data.phone,
        company=data.company,
        message=data.message,
        source="site_lecomptoir",
    )
    background.add_task(_notify_team, data)
    return {"status": "received"}


@router.get("/listings/{token}", summary="Page d'annonce publique (sans authentification)")
async def public_listing(token: str, db: AsyncSession = Depends(get_db)):
    """Annonce publiée d'un bien, accessible par son jeton. 404 si introuvable ou
    non publiée (brouillon / programmée / dépubliée)."""
    from app.models.publishing import Listing
    from app.models.property import Property
    from app.models.document import Document
    from app.models.user import User
    from app.services.listing_service import build_photo_url

    listing = (await db.execute(
        select(Listing).where(Listing.public_token == token)
    )).scalar_one_or_none()
    if not listing or listing.status != "published":
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    prop = await db.get(Property, listing.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    # Photos sélectionnées (ordre conservé) ; repli sur toutes les images du bien.
    photos: list[str] = []
    ids = [uuid.UUID(x) for x in (listing.photo_ids or []) if x]
    if ids:
        docs = (await db.execute(
            select(Document).where(Document.id.in_(ids))
        )).scalars().all()
        by_id = {str(d.id): d for d in docs}
        for x in (listing.photo_ids or []):
            d = by_id.get(str(x))
            if d and (d.mime_type or "").lower().startswith("image/"):
                photos.append(build_photo_url(d.file_path))

    contact_name = None
    if listing.created_by:
        mgr = await db.get(User, listing.created_by)
        contact_name = getattr(mgr, "full_name", None) if mgr else None

    return {
        "title": listing.title or prop.name,
        "description": listing.description or prop.description,
        "price": float(listing.price) if listing.price is not None else None,
        "photos": photos,
        "published_at": listing.published_at,
        "contact_name": contact_name,
        "property": {
            "city": prop.city,
            "zip_code": prop.zip_code,
            "property_type": prop.property_type,
            "typology": prop.typology,
            "area_sqm": float(prop.area_sqm) if prop.area_sqm is not None else None,
            "floor": prop.floor,
            "bathrooms": prop.bathrooms,
            "energy_class": prop.energy_class,
            "heating_type": prop.heating_type,
            "furnished": prop.furnished,
            "features": {
                "elevator": prop.has_elevator, "balcony": prop.has_balcony,
                "terrace": prop.has_terrace, "garden": prop.has_garden,
                "parking": prop.has_parking, "cellar": prop.has_cellar,
                "fiber": prop.has_fiber, "air_conditioning": prop.has_air_conditioning,
            },
        },
    }
