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


async def _valid_boutique_ids(db: AsyncSession, manager_user_id) -> set[str] | None:
    """Ids des boutiques de résidence existant ENCORE côté Market pour le gestionnaire
    propriétaire du lien. None si Alice est injoignable (réponse non fiable)."""
    mgr = await db.get(User, manager_user_id)
    email = getattr(mgr, "email", None)
    if not email:
        return None
    res = await alice_client.list_manager_boutiques(manager_email=email, source="immo")
    if not res.get("ok"):
        return None
    return {str(b.get("id")) for b in res.get("boutiques", [])}


async def _link_or_heal(db: AsyncSession, link):
    """Renvoie `link` s'il pointe vers une boutique encore existante ; sinon purge le
    lien périmé (compte gérant / boutique supprimé côté Market) et renvoie None. En
    cas d'Alice injoignable, conserve le lien tel quel (pas de purge sur panne)."""
    if link is None:
        return None
    valid = await _valid_boutique_ids(db, link.manager_user_id)
    if valid is None or str(link.boutique_id) in valid:
        return link
    await db.delete(link)
    await db.commit()
    return None


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
    link = await _link_or_heal(db, await _get_link(db, kind, rid))
    return _link_out(link)


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


async def _manager_residences(db: AsyncSession, user: User) -> list[dict]:
    """Biens + copropriétés du gestionnaire (pour rattacher à une boutique)."""
    props = (
        (await db.execute(select(Property).where(Property.created_by == user.id))).scalars().all()
    )
    copros = (
        (await db.execute(select(Copropriete).where(Copropriete.created_by == user.id)))
        .scalars()
        .all()
    )
    out = [{"kind": "property", "id": str(p.id), "name": p.name} for p in props]
    out += [{"kind": "copropriete", "id": str(c.id), "name": c.name} for c in copros]
    return out


@router.get("/boutiques/overview")
async def boutiques_overview(
    current_user: User = Depends(get_current_gestionnaire),
):
    """Données de la page « Boutique associée » : roster des gérants rattachés + liste
    (lecture seule) de toutes leurs boutiques. Les gérants créent leurs boutiques
    eux-mêmes dans Le Comptoir Market."""
    res = await alice_client.list_manager_boutiques(manager_email=current_user.email, source="immo")
    boutiques = [
        {
            "id": str(b.get("id")),
            "nom": b.get("nom"),
            "slug": b.get("slug"),
            "url": _boutique_url(b.get("slug")),
            "gerant_email": b.get("gerant_email"),
            "gerant_name": b.get("gerant_name"),
        }
        for b in res.get("boutiques", [])
    ]
    roster = await alice_client.list_residence_gerants(manager_email=current_user.email)
    return {
        "market_enabled": bool(res.get("market_enabled")),
        "boutiques": boutiques,
        "gerants": roster.get("gerants", []),
    }


class BoutiqueNameIn(BaseModel):
    nom: str | None = None


@router.post("/boutiques")
async def create_boutique(
    payload: BoutiqueNameIn | None = None,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Crée une nouvelle boutique de résidence (autonome) pour le gestionnaire."""
    payload = payload or BoutiqueNameIn()
    res = await alice_client.create_standalone_boutique(
        manager_email=current_user.email, nom=(payload.nom or "").strip() or None
    )
    if not res["ok"]:
        if res["status"] == 409 and res.get("detail") == "market_not_enabled":
            raise HTTPException(status_code=409, detail="market_not_enabled")
        if res["status"] == 403 and res.get("detail") == "plan_limit_reached":
            raise HTTPException(status_code=403, detail="plan_limit_reached")
        raise HTTPException(status_code=502, detail=res.get("detail") or "Création impossible.")
    return res["data"]


@router.patch("/boutiques/{boutique_id}")
async def rename_boutique(
    boutique_id: str,
    payload: BoutiqueNameIn,
    current_user: User = Depends(get_current_gestionnaire),
):
    nom = (payload.nom or "").strip()
    if not nom:
        raise HTTPException(status_code=422, detail="Nom requis.")
    ok = await alice_client.rename_boutique(
        manager_email=current_user.email, boutique_id=boutique_id, nom=nom
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Renommage impossible.")
    return {"status": "ok"}


@router.delete("/boutiques/{boutique_id}")
async def delete_boutique(
    boutique_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    ok = await alice_client.delete_boutique(
        manager_email=current_user.email, boutique_id=boutique_id
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Suppression impossible.")
    links = (
        (
            await db.execute(
                select(ResidenceBoutiqueLink).where(
                    ResidenceBoutiqueLink.manager_user_id == current_user.id,
                    ResidenceBoutiqueLink.boutique_id == boutique_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for link in links:
        await db.delete(link)
    await db.commit()
    return {"status": "deleted"}


class ResidenceRef(BaseModel):
    kind: str
    id: uuid.UUID


class SetResidencesIn(BaseModel):
    items: list[ResidenceRef] = []


@router.put("/boutiques/{boutique_id}/residences")
async def set_boutique_residences(
    boutique_id: str,
    payload: SetResidencesIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Synchronise les biens rattachés à une boutique (rattacher/détacher)."""
    res = await alice_client.list_manager_boutiques(manager_email=current_user.email, source="immo")
    match = next(
        (b for b in res.get("boutiques", []) if str(b.get("id")) == str(boutique_id)), None
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Boutique introuvable pour votre compte.")
    slug = match.get("slug")
    url = _boutique_url(slug)
    desired = {(it.kind, it.id) for it in payload.items if it.kind in _KINDS}

    current_links = (
        (
            await db.execute(
                select(ResidenceBoutiqueLink).where(
                    ResidenceBoutiqueLink.manager_user_id == current_user.id,
                    ResidenceBoutiqueLink.boutique_id == str(boutique_id),
                )
            )
        )
        .scalars()
        .all()
    )
    for link in current_links:
        if (link.residence_kind, link.residence_id) not in desired:
            await db.delete(link)

    for kind, rid in desired:
        link = await _get_link(db, kind, rid)
        if link is None:
            db.add(
                ResidenceBoutiqueLink(
                    residence_kind=kind,
                    residence_id=rid,
                    manager_user_id=current_user.id,
                    boutique_id=str(boutique_id),
                    boutique_slug=slug,
                    boutique_url=url,
                )
            )
        else:
            link.boutique_id = str(boutique_id)
            link.boutique_slug = slug
            link.boutique_url = url
            link.manager_user_id = current_user.id
    await db.commit()
    return {"status": "ok"}


class MarketLoginIn(BaseModel):
    gerant_email: str | None = None


@router.post("/market-login")
async def market_login(
    payload: MarketLoginIn | None = None,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Lien SSO à usage unique pour ouvrir Le Comptoir Market (compte gérant) sans
    identifiants. Cible le gérant `gerant_email` (rattaché) si fourni, sinon le
    premier. 409 market_not_enabled si pas de compte gérant."""
    payload = payload or MarketLoginIn()
    res = await alice_client.manager_login_link(
        manager_email=current_user.email, gerant_email=(payload.gerant_email or None)
    )
    if not res["ok"]:
        if res["status"] == 409 and res.get("detail") == "market_not_enabled":
            raise HTTPException(status_code=409, detail="market_not_enabled")
        raise HTTPException(status_code=502, detail=res.get("detail") or "Ouverture impossible.")
    token = (res.get("data") or {}).get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Ouverture impossible.")
    cfg = get_settings()
    return {"url": f"{cfg.MARKET_PUBLIC_URL.rstrip('/')}/g/sso/{token}/"}


class ActivateMarketIn(BaseModel):
    plan_id: str | None = None


@router.post("/activate-market")
async def activate_market(
    payload: ActivateMarketIn | None = None,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Crée le compte gérant Le Comptoir Market depuis le compte Immo + plan choisi."""
    payload = payload or ActivateMarketIn()
    res = await alice_client.activate_boutique(
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        address=current_user.full_address,
        plan_id=payload.plan_id,
    )
    if not res["ok"]:
        raise HTTPException(status_code=502, detail=res.get("detail") or "Activation impossible.")
    return res["data"]


class GerantEmailIn(BaseModel):
    gerant_email: str


@router.post("/boutiques/gerants")
async def add_residence_gerant(
    payload: GerantEmailIn,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Rattache un compte gérant Le Comptoir Market au gestionnaire (e-mail identique
    ou différent du sien). Si ce compte n'existe pas encore, il est créé et ses
    identifiants lui sont envoyés par e-mail. Le gestionnaire peut rattacher autant de
    gérants qu'il veut ; chaque gérant gère ses propres boutiques."""
    email = (payload.gerant_email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="E-mail du gérant invalide.")
    res = await alice_client.add_residence_gerant(
        gestionnaire_email=current_user.email,
        gerant_email=email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        address=current_user.full_address,
    )
    if not res["ok"]:
        raise HTTPException(
            status_code=502, detail=res.get("detail") or "Impossible de rattacher ce gérant."
        )
    return res["data"]


@router.delete("/boutiques/gerants")
async def remove_residence_gerant(
    gerant_email: str,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Retire un gérant du roster du gestionnaire (ne supprime ni le compte gérant ni
    ses boutiques : il peut servir d'autres gestionnaires)."""
    ok = await alice_client.remove_residence_gerant(
        gestionnaire_email=current_user.email, gerant_email=(gerant_email or "").strip()
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Retrait du gérant impossible.")
    return {"status": "removed"}


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
            if res["status"] == 403 and res.get("detail") == "plan_limit_reached":
                raise HTTPException(status_code=403, detail="plan_limit_reached")
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


async def _tenant_gestionnaire(db: AsyncSession, user: User) -> User | None:
    """Gestionnaire du locataire courant (via bail actif → bien → créateur)."""
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
    prop = await db.get(Property, lease.property_id)
    if prop is None or prop.created_by is None:
        return None
    return await db.get(User, prop.created_by)


async def _tenant_gestionnaire_email(db: AsyncSession, user: User) -> str | None:
    mgr = await _tenant_gestionnaire(db, user)
    return (getattr(mgr, "email", None) or "").strip() or None if mgr else None


async def _tenant_boutiques(db: AsyncSession, user: User) -> list[dict]:
    """Toutes les boutiques du gestionnaire du locataire (tous gérants confondus)."""
    email = await _tenant_gestionnaire_email(db, user)
    if not email:
        return []
    res = await alice_client.list_manager_boutiques(manager_email=email, source="immo")
    return [
        {
            "id": str(b.get("id")),
            "nom": b.get("nom"),
            "slug": b.get("slug"),
            "url": _boutique_url(b.get("slug")),
        }
        for b in res.get("boutiques", [])
    ]


async def _tenant_email(db: AsyncSession, user: User) -> str:
    from app.models.tenant import Tenant

    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == user.id))
    ).scalar_one_or_none()
    return (getattr(tenant, "email", None) or user.email or "").strip()


@router.get("/my-boutiques")
async def my_residence_boutiques(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste de toutes les boutiques accessibles au locataire (celles de son
    gestionnaire, tous gérants confondus)."""
    return {"boutiques": await _tenant_boutiques(db, current_user)}


@router.get("/my-boutique")
async def my_residence_boutique(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le locataire a-t-il au moins une boutique accessible ? (compat)."""
    return {"available": len(await _tenant_boutiques(db, current_user)) > 0}


class MyBoutiqueSsoIn(BaseModel):
    boutique_id: str | None = None


@router.post("/my-boutique/sso")
async def my_residence_boutique_sso(
    payload: MyBoutiqueSsoIn | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Émet un lien SSO à usage unique vers une boutique accessible au locataire
    (`boutique_id`, sinon la première)."""
    import secrets
    from datetime import datetime, timedelta

    from app.models.sso_token import BoutiqueSsoToken
    from app.models.tenant import Tenant

    payload = payload or MyBoutiqueSsoIn()
    boutiques = await _tenant_boutiques(db, current_user)
    if not boutiques:
        raise HTTPException(status_code=404, detail="Aucune boutique accessible.")
    target = (payload.boutique_id or boutiques[0]["id"]).strip()
    if target not in {b["id"] for b in boutiques}:
        raise HTTPException(status_code=404, detail="Boutique introuvable.")
    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    ).scalar_one_or_none()
    email = (getattr(tenant, "email", None) or current_user.email or "").strip()
    full_name = getattr(tenant, "full_name", None) or None
    mgr = await _tenant_gestionnaire(db, current_user)
    ges_nom = (getattr(mgr, "full_name", None) or "").strip() or None
    token = secrets.token_urlsafe(24)
    db.add(
        BoutiqueSsoToken(
            token=token,
            tenant_email=email,
            tenant_full_name=full_name,
            gestionnaire_nom=ges_nom,
            boutique_id=target,
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
    """Commandes du locataire, agrégées sur toutes les boutiques de son gestionnaire."""
    boutiques = await _tenant_boutiques(db, current_user)
    if not boutiques:
        return []
    email = await _tenant_email(db, current_user)
    if not email:
        return []
    out: list[dict] = []
    for b in boutiques:
        rows = await alice_client.get_residence_orders(
            source="immo", residence_id="", kind="", email=email, boutique_id=b["id"]
        )
        for o in rows:
            out.append({**o, "boutique_nom": b["nom"]})
    return out
