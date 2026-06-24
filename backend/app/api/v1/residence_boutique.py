"""Pont Le Comptoir Immo ↔ Le Comptoir Market : boutique de résidence.

Le gestionnaire relie une résidence (un bien « property » ou une copropriété
« copropriete ») à une boutique Market. Le provisionnement est orchestré par
Alice (qui rapproche le gestionnaire de son gérant Market par e-mail). Le lien
est mémorisé localement (table residence_boutique_links).
"""

import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager, get_current_user
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


def _residence_address(kind: str, obj) -> str:
    if kind == "copropriete":
        return obj.full_address or ""
    loc = " ".join(p for p in [(obj.zip_code or "").strip(), (obj.city or "").strip()] if p)
    return ", ".join(p for p in [(obj.address or "").strip(), loc] if p)


async def _load_residence(db: AsyncSession, kind: str, rid: uuid.UUID):
    """Charge la résidence (bien ou copropriété) → (objet, nom, adresse, created_by)."""
    obj = await db.get(Property if kind == "property" else Copropriete, rid)
    if obj is None:
        raise HTTPException(status_code=404, detail="Résidence introuvable.")
    return obj, obj.name, _residence_address(kind, obj), obj.created_by


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
    _, _, _, created_by = await _load_residence(db, kind, rid)
    await assert_manager_scope(db, current_user, created_by, "cette résidence")
    return _link_out(await _get_link(db, kind, rid))


def _boutique_url(slug: str | None) -> str | None:
    if not slug:
        return None
    return f"{get_settings().MARKET_PUBLIC_URL.rstrip('/')}/boutique/{slug}/"


@router.get("/my-manager-boutiques")
async def my_manager_boutiques(
    current_user: User = Depends(get_current_gestionnaire),
):
    """Boutiques de résidence déjà créées par le gestionnaire (rapproché par e-mail
    de son gérant Market) : permet de rattacher un bien à une boutique existante au
    lieu d'en créer une par appartement. {market_enabled, boutiques: [{id, slug, nom, url}]}."""
    res = await alice_client.list_manager_boutiques(manager_email=current_user.email, source="immo")
    boutiques = [
        {
            "id": str(b.get("id")),
            "slug": b.get("slug"),
            "nom": b.get("nom"),
            "url": _boutique_url(b.get("slug")),
        }
        for b in res.get("boutiques", [])
    ]
    return {"market_enabled": bool(res.get("market_enabled")), "boutiques": boutiques}


class LinkBoutiqueIn(BaseModel):
    """Corps du déploiement : soit rattacher à une boutique existante (`boutique_id`),
    soit en créer une nouvelle (avec un `nom` optionnel)."""

    boutique_id: str | None = None
    nom: str | None = None


@router.post("/{kind}/{rid}/boutique")
async def link_residence_boutique(
    kind: str,
    rid: uuid.UUID,
    payload: LinkBoutiqueIn | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    if kind not in _KINDS:
        raise HTTPException(status_code=422, detail="Type de résidence invalide.")
    _, name, address, created_by = await _load_residence(db, kind, rid)
    await assert_manager_scope(db, current_user, created_by, "cette résidence")
    payload = payload or LinkBoutiqueIn()

    if payload.boutique_id:
        # Rattacher à une boutique existante du gestionnaire (vérif d'appartenance
        # via la liste de son gérant Market, rapproché par e-mail).
        res = await alice_client.list_manager_boutiques(
            manager_email=current_user.email, source="immo"
        )
        match = next(
            (b for b in res.get("boutiques", []) if str(b.get("id")) == str(payload.boutique_id)),
            None,
        )
        if match is None:
            raise HTTPException(status_code=404, detail="Boutique introuvable pour votre compte.")
        boutique_id = str(match.get("id"))
        slug = match.get("slug")
    else:
        # Créer une nouvelle boutique de résidence.
        res = await alice_client.provision_residence_boutique(
            manager_email=current_user.email,
            immo_manager_id=current_user.id,
            residence_id=rid,
            residence_kind=kind,
            residence_name=(payload.nom or "").strip() or name,
            residence_address=address,
        )
        if not res["ok"]:
            if res["status"] == 409 and res.get("detail") == "market_not_enabled":
                # Le gestionnaire n'a pas de gérant Market : l'app affiche la CTA.
                raise HTTPException(status_code=409, detail="market_not_enabled")
            raise HTTPException(
                status_code=502,
                detail=res.get("detail") or "Provisionnement de la boutique impossible.",
            )
        data = res["data"]
        boutique_id = str(data["id"])
        slug = data.get("slug")

    url = _boutique_url(slug)
    link = await _get_link(db, kind, rid)
    if link is None:
        link = ResidenceBoutiqueLink(
            residence_kind=kind,
            residence_id=rid,
            manager_user_id=current_user.id,
            boutique_id=boutique_id,
            boutique_slug=slug,
            boutique_url=url,
        )
        db.add(link)
    else:
        link.boutique_id = boutique_id
        link.boutique_slug = slug
        link.boutique_url = url
        link.manager_user_id = current_user.id
    await db.commit()
    return _link_out(link)


async def _tenant_boutique_link(db: AsyncSession, user: User):
    """Lien boutique de la résidence du locataire courant (via bail actif), ou None."""
    from app.models.lease import Lease
    from app.models.tenant import Tenant

    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == user.id))
    ).scalar_one_or_none()
    if tenant is None:
        return None
    lease = (
        (
            await db.execute(
                select(Lease)
                .where(Lease.tenant_id == tenant.id, Lease.is_active.is_(True))
                .order_by(Lease.start_date.desc())
            )
        )
        .scalars()
        .first()
    )
    if lease is None or lease.property_id is None:
        return None
    return await _get_link(db, "property", lease.property_id)


@router.get("/my-boutique")
async def my_residence_boutique(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le locataire connecté a-t-il une boutique de résidence accessible ?"""
    link = await _tenant_boutique_link(db, current_user)
    return {"available": link is not None}


@router.post("/my-boutique/sso")
async def my_residence_boutique_sso(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Émet un lien SSO à usage unique vers la boutique de la résidence du locataire."""
    import secrets
    from datetime import datetime, timedelta

    from app.models.sso_token import BoutiqueSsoToken
    from app.models.tenant import Tenant

    link = await _tenant_boutique_link(db, current_user)
    if link is None:
        raise HTTPException(status_code=404, detail="Aucune boutique pour votre résidence.")
    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    ).scalar_one_or_none()
    email = (getattr(tenant, "email", None) or current_user.email or "").strip()
    full_name = getattr(tenant, "full_name", None) or None
    token = secrets.token_urlsafe(24)
    db.add(
        BoutiqueSsoToken(
            token=token,
            tenant_email=email,
            tenant_full_name=full_name,
            boutique_id=link.boutique_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    await db.commit()
    cfg = get_settings()
    return {"url": f"{cfg.MARKET_PUBLIC_URL.rstrip('/')}/r/sso/{token}/?src=immo"}


@router.get("/my-boutique/orders")
async def my_residence_boutique_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Commandes du locataire à la boutique de sa résidence (statut visible)."""
    from app.models.tenant import Tenant

    link = await _tenant_boutique_link(db, current_user)
    if link is None:
        return []
    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    ).scalar_one_or_none()
    email = (getattr(tenant, "email", None) or current_user.email or "").strip()
    if not email:
        return []
    return await alice_client.get_residence_orders(
        source="immo",
        residence_id=link.residence_id,
        kind=link.residence_kind,
        email=email,
        boutique_id=link.boutique_id,
    )
