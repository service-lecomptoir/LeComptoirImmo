"""Pont Le Comptoir Immo ↔ Le Comptoir Market : boutique de résidence.

Le gestionnaire relie une résidence (un bien « property » ou une copropriété
« copropriete ») à une boutique Market. Le provisionnement est orchestré par
Alice (qui rapproche le gestionnaire de son gérant Market par e-mail). Le lien
est mémorisé localement (table residence_boutique_links).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager
from app.api.v1._isolation import assert_manager_scope
from app.config import get_settings
from app.database import get_db
from app.models.copropriete import Copropriete
from app.models.property import Property
from app.models.residence_boutique import ResidenceBoutiqueLink
from app.models.user import User
from app.services import alice_client

router = APIRouter(prefix="/residences", tags=["residence-boutique"])

_KINDS = ("property", "copropriete")


async def _load_residence(db: AsyncSession, kind: str, rid: uuid.UUID):
    """Charge la résidence (bien ou copropriété) et renvoie (objet, nom, created_by)."""
    obj = await db.get(Property if kind == "property" else Copropriete, rid)
    if obj is None:
        raise HTTPException(status_code=404, detail="Résidence introuvable.")
    return obj, obj.name, obj.created_by


async def _get_link(db: AsyncSession, kind: str, rid: uuid.UUID):
    return (
        await db.execute(
            select(ResidenceBoutiqueLink).where(
                ResidenceBoutiqueLink.residence_kind == kind,
                ResidenceBoutiqueLink.residence_id == rid,
            )
        )
    ).scalar_one_or_none()


def _link_out(link: ResidenceBoutiqueLink | None) -> dict:
    if link is None:
        return {"linked": False}
    return {
        "linked": True,
        "boutique_id": link.boutique_id,
        "boutique_slug": link.boutique_slug,
        "boutique_url": link.boutique_url,
    }


@router.get("/{kind}/{rid}/boutique")
async def get_residence_boutique(
    kind: str,
    rid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    if kind not in _KINDS:
        raise HTTPException(status_code=422, detail="Type de résidence invalide.")
    _, _, created_by = await _load_residence(db, kind, rid)
    await assert_manager_scope(db, current_user, created_by, "cette résidence")
    return _link_out(await _get_link(db, kind, rid))


@router.post("/{kind}/{rid}/boutique")
async def link_residence_boutique(
    kind: str,
    rid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    if kind not in _KINDS:
        raise HTTPException(status_code=422, detail="Type de résidence invalide.")
    _, name, created_by = await _load_residence(db, kind, rid)
    await assert_manager_scope(db, current_user, created_by, "cette résidence")

    res = await alice_client.provision_residence_boutique(
        manager_email=current_user.email,
        immo_manager_id=current_user.id,
        residence_id=rid,
        residence_kind=kind,
        residence_name=name,
    )
    if not res["ok"]:
        if res["status"] == 409 and res.get("detail") == "market_not_enabled":
            # Le gestionnaire n'a pas de gérant Market : l'app affiche la CTA.
            raise HTTPException(status_code=409, detail="market_not_enabled")
        raise HTTPException(
            status_code=502, detail=res.get("detail") or "Provisionnement de la boutique impossible."
        )

    data = res["data"]
    cfg = get_settings()
    slug = data.get("slug")
    url = f"{cfg.MARKET_PUBLIC_URL.rstrip('/')}/boutique/{slug}/" if slug else None

    link = await _get_link(db, kind, rid)
    if link is None:
        link = ResidenceBoutiqueLink(
            residence_kind=kind,
            residence_id=rid,
            manager_user_id=current_user.id,
            boutique_id=str(data["id"]),
            boutique_slug=slug,
            boutique_url=url,
        )
        db.add(link)
    else:
        link.boutique_id = str(data["id"])
        link.boutique_slug = slug
        link.boutique_url = url
        link.manager_user_id = current_user.id
    await db.commit()
    return _link_out(link)
