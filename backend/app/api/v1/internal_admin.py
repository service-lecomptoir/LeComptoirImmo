"""Contrat interne unifié `/internal` (Alice → LeCI).

Même structure que l'API interne de Le Comptoir Séjour, pour qu'Alice pilote les
deux produits de façon identique. Router monté À LA RACINE (hors `/api`) : il
n'est donc PAS proxifié publiquement par nginx (location `/api/` seulement) →
joignable uniquement par Alice sur le réseau Docker interne.

Protégé par l'en-tête `X-Internal-Key` == `ALICE_INTERNAL_KEY` (clé partagée).
"""

import hmac
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import Role
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.property import Property
from app.models.user import User
from app.schemas.user import UserCreate, UserRoleUpdate, UserUpdate
from app.services.user_service import UserService

_ALLOWED_ROLES = {"gestionnaire", "gestionnaire_proprio"}

router = APIRouter(prefix="/internal", tags=["internal-admin"])

_MANAGER_ROLES = [Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value]


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    cfg = get_settings()
    # Comparaison constant-time (anti timing-attack) — clé partagée inter-services.
    if (
        not x_internal_key
        or not cfg.ALICE_INTERNAL_KEY
        or not hmac.compare_digest(x_internal_key, cfg.ALICE_INTERNAL_KEY)
    ):
        raise HTTPException(status_code=401, detail="Clé interne invalide.")


# ── Schémas du contrat (identiques côté Séjour) ───────────────────────────────
class ManagerOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    phone: str | None = None
    role: str
    is_active: bool
    created_at: datetime | None = None
    property_count: int = 0

    model_config = {"from_attributes": True}


class PropertyOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None

    model_config = {"from_attributes": True}


class ManagerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field("", max_length=255)
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    phone: str | None = None
    address: str | None = None
    role: str = "gestionnaire"
    password: str = Field(..., min_length=8, max_length=128)


class ManagerUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    phone: str | None = None
    address: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class Stats(BaseModel):
    managers: int
    active_managers: int
    users: int


class BlockResult(BaseModel):
    blocked_user_ids: list[str]


class UnblockRequest(BaseModel):
    user_ids: list[str] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────
async def _property_counts(db: AsyncSession) -> dict[uuid.UUID, int]:
    """Nb de biens par créateur (gestionnaire), en une requête."""
    rows = await db.execute(
        select(Property.created_by, func.count(Property.id)).group_by(Property.created_by)
    )
    return {cb: n for cb, n in rows.all() if cb is not None}


def _manager_out(user: User, property_count: int = 0) -> ManagerOut:
    return ManagerOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        owner_kind=getattr(user, "owner_kind", None),
        owner_full_name=getattr(user, "owner_full_name", None),
        owner_company=getattr(user, "owner_company", None),
        owner_national_id=getattr(user, "owner_national_id", None),
        phone=getattr(user, "phone", None),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=getattr(user, "created_at", None),
        property_count=property_count,
    )


@router.get("/managers", response_model=list[ManagerOut])
async def list_managers(
    _: None = Depends(require_internal_key), db: AsyncSession = Depends(get_db)
):
    rows = (
        (
            await db.execute(
                select(User).where(User.role.in_(_MANAGER_ROLES)).order_by(User.full_name)
            )
        )
        .scalars()
        .all()
    )
    counts = await _property_counts(db)
    return [_manager_out(u, counts.get(u.id, 0)) for u in rows]


@router.get("/managers/{manager_id}", response_model=ManagerOut)
async def get_manager(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, manager_id)
    if user is None or user.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    count = (
        await db.scalar(select(func.count(Property.id)).where(Property.created_by == manager_id))
        or 0
    )
    return _manager_out(user, count)


@router.get("/managers/{manager_id}/properties", response_model=list[PropertyOut])
async def manager_properties(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(Property).where(Property.created_by == manager_id).order_by(Property.name)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.post("/managers", response_model=ManagerOut, status_code=201)
async def create_manager(
    data: ManagerCreate,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    if data.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=422, detail="Rôle de gestionnaire invalide.")
    user = await UserService.create(
        db,
        UserCreate(
            email=data.email, password=data.password, full_name=data.full_name, role=Role(data.role)
        ),
        created_by=None,  # compte principal (agence), créé par la plateforme
    )
    if data.owner_kind in ("personne", "societe"):
        user.owner_kind = data.owner_kind
    if data.owner_full_name is not None:
        user.owner_full_name = data.owner_full_name
    if data.owner_company is not None:
        user.owner_company = data.owner_company
    if data.owner_national_id is not None:
        user.owner_national_id = data.owner_national_id
    if data.phone is not None:
        user.phone = data.phone
    if data.address is not None:
        user.address = data.address
    # Mot de passe provisoire défini par Alice : le gestionnaire devra le
    # changer à sa première connexion (LeComptoir Immo / Séjour).
    user.must_change_password = True
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/managers/{manager_id}", response_model=ManagerOut)
async def update_manager(
    manager_id: uuid.UUID,
    data: ManagerUpdate,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    if data.role is not None:
        if data.role not in _ALLOWED_ROLES:
            raise HTTPException(status_code=422, detail="Rôle de gestionnaire invalide.")
        await UserService.update_role(db, manager_id, UserRoleUpdate(role=Role(data.role)))
    await UserService.update(
        db,
        manager_id,
        UserUpdate(
            email=data.email,
            full_name=data.full_name,
            owner_kind=data.owner_kind,
            owner_full_name=data.owner_full_name,
            owner_company=data.owner_company,
            owner_national_id=data.owner_national_id,
            phone=data.phone,
            address=data.address,
            is_active=data.is_active,
        ),
    )
    await db.commit()
    refreshed = await db.get(User, manager_id)
    return refreshed


@router.post("/managers/{manager_id}/block", response_model=BlockResult)
async def block_manager(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    """Bloque le gestionnaire et désactive en cascade ses propriétaires et locataires.

    Logique portée verbatim de l'ancien block_service d'Alice (mêmes tables/colonnes),
    mais exécutée ici, dans LeCI (qui possède le graphe d'utilisateurs).
    Renvoie les IDs bloqués en cascade (Alice les stocke pour le déblocage).
    """
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")

    prop_ids = [
        r[0]
        for r in (
            await db.execute(
                text("SELECT id FROM properties WHERE created_by = :g"), {"g": manager_id}
            )
        ).all()
    ]
    owners: list[uuid.UUID] = []
    tenant_db_ids: set[uuid.UUID] = set()
    if prop_ids:
        owners = [
            r[0]
            for r in (
                await db.execute(
                    text(
                        "SELECT owner_user_id FROM properties WHERE id = ANY(:ids) AND owner_user_id IS NOT NULL"
                    ),
                    {"ids": prop_ids},
                )
            ).all()
        ]
        for r in (
            await db.execute(
                text(
                    "SELECT tenant_id FROM leases WHERE property_id = ANY(:ids) AND is_active = true AND tenant_id IS NOT NULL"
                ),
                {"ids": prop_ids},
            )
        ).all():
            tenant_db_ids.add(r[0])
        # Chemin via units (défensif : la table peut ne pas exister selon le schéma).
        try:
            unit_ids = [
                r[0]
                for r in (
                    await db.execute(
                        text("SELECT id FROM units WHERE property_id = ANY(:ids)"),
                        {"ids": prop_ids},
                    )
                ).all()
            ]
            if unit_ids:
                for r in (
                    await db.execute(
                        text(
                            "SELECT tenant_id FROM leases WHERE unit_id = ANY(:ids) AND is_active = true AND tenant_id IS NOT NULL"
                        ),
                        {"ids": unit_ids},
                    )
                ).all():
                    tenant_db_ids.add(r[0])
        except Exception:  # noqa: BLE001
            pass

    tenant_user_ids: list[uuid.UUID] = []
    if tenant_db_ids:
        tenant_user_ids = [
            r[0]
            for r in (
                await db.execute(
                    text(
                        "SELECT user_id FROM tenants WHERE id = ANY(:ids) AND user_id IS NOT NULL"
                    ),
                    {"ids": list(tenant_db_ids)},
                )
            ).all()
        ]
    direct_tenant_user_ids = [
        r[0]
        for r in (
            await db.execute(
                text("SELECT user_id FROM tenants WHERE created_by = :g AND user_id IS NOT NULL"),
                {"g": manager_id},
            )
        ).all()
    ]

    cascade = list(set(owners + tenant_user_ids + direct_tenant_user_ids) - {manager_id})

    await db.execute(text("UPDATE users SET is_active = false WHERE id = :g"), {"g": manager_id})
    if cascade:
        await db.execute(
            text("UPDATE users SET is_active = false WHERE id = ANY(:ids)"), {"ids": cascade}
        )
    await db.commit()
    return BlockResult(blocked_user_ids=[str(u) for u in cascade])


@router.post("/managers/{manager_id}/unblock", status_code=204)
async def unblock_manager(
    manager_id: uuid.UUID,
    data: UnblockRequest,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    """Réactive le gestionnaire et uniquement les users listés (cascade d'origine)."""
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    await db.execute(text("UPDATE users SET is_active = true WHERE id = :g"), {"g": manager_id})
    uids = [uuid.UUID(u) for u in data.user_ids if u]
    if uids:
        await db.execute(
            text("UPDATE users SET is_active = true WHERE id = ANY(:ids)"), {"ids": uids}
        )
    await db.commit()


@router.post("/managers/{manager_id}/reset-password", status_code=204)
async def reset_manager_password(
    manager_id: uuid.UUID,
    data: ResetPassword,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    await UserService.admin_set_password(db, manager_id, data.new_password, temporary=True)
    await db.commit()


@router.delete("/managers/{manager_id}", status_code=200)
async def delete_manager(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    """Suppression DÉFINITIVE et complète d'un gestionnaire et de toutes ses données.

    Suppressions explicites, ordonnées (feuilles → racine), dans une seule
    transaction (atomique : toute contrainte imprévue annule l'ensemble, sans
    suppression partielle). On ne dépend pas des ON DELETE de la base.

    Périmètre : biens du gérant + toute leur chaîne (baux → paiements, inspections,
    révisions, apurements, sorties, avis, régularisations, taxes, signalements,
    candidatures, annonces, créneaux de visite), locataires et propriétaires créés
    par lui (+ leurs comptes de connexion), contenus directs du gérant (templates,
    domaines e-mail, règles, notifications, contacts, documents, messages), et le
    compte gérant. Les fichiers uploadés associés sont supprimés du disque.
    """
    from app.utils.file_handler import delete_file

    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    g = manager_id

    async def ids(sql: str, params: dict) -> list:
        return [r[0] for r in (await db.execute(text(sql), params)).all() if r[0] is not None]

    # ── Collecte du périmètre ──
    prop_ids = await ids("SELECT id FROM properties WHERE created_by = :g", {"g": g})
    lease_ids = (
        await ids("SELECT id FROM leases WHERE property_id = ANY(:ids)", {"ids": prop_ids})
        if prop_ids
        else []
    )
    tenant_ids = await ids("SELECT id FROM tenants WHERE created_by = :g", {"g": g})
    owner_ids = await ids("SELECT id FROM owners WHERE created_by = :g", {"g": g})

    # Comptes de connexion liés (propriétaires + locataires créés par ce gérant).
    linked: set = set()
    for uid in await ids(
        "SELECT user_id FROM owners WHERE created_by = :g AND user_id IS NOT NULL", {"g": g}
    ):
        linked.add(uid)
    for uid in await ids(
        "SELECT user_id FROM tenants WHERE created_by = :g AND user_id IS NOT NULL", {"g": g}
    ):
        linked.add(uid)
    if prop_ids:
        for uid in await ids(
            "SELECT owner_user_id FROM properties WHERE id = ANY(:ids) AND owner_user_id IS NOT NULL",
            {"ids": prop_ids},
        ):
            linked.add(uid)
    linked.discard(g)
    linked_ids = list(linked)

    # Colonnes réellement présentes en base : la création de schéma par
    # `create_all` ne pose pas les colonnes ajoutées après coup (dérive). On
    # n'émet donc une suppression que pour les couples (table, colonne) existants.
    colrows = await db.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'"
        )
    )
    cols: set = {(t, c) for t, c in colrows.all()}

    async def col_ids(sql: str, params: dict, table: str, col: str) -> list:
        """SELECT défensif : ne s'exécute que si la colonne existe."""
        if (table, col) not in cols:
            return []
        return await ids(sql, params)

    # ── Fichiers à supprimer du disque (collecte AVANT suppression) ──
    file_paths: list[str] = []
    file_paths += await col_ids(
        "SELECT file_path FROM documents WHERE uploaded_by = :g AND file_path IS NOT NULL",
        {"g": g},
        "documents",
        "uploaded_by",
    )
    scope_entity_ids = [str(x) for x in (prop_ids + lease_ids + tenant_ids + owner_ids)]
    if scope_entity_ids:
        file_paths += await col_ids(
            "SELECT file_path FROM documents "
            "WHERE entity_id::text = ANY(:ids) AND file_path IS NOT NULL",
            {"ids": scope_entity_ids},
            "documents",
            "entity_id",
        )
    if target.logo_path:
        file_paths.append(target.logo_path)
    if prop_ids:
        file_paths += await col_ids(
            "SELECT photo_path FROM signalements "
            "WHERE property_id = ANY(:ids) AND photo_path IS NOT NULL",
            {"ids": prop_ids},
            "signalements",
            "photo_path",
        )
    if tenant_ids:
        file_paths += await col_ids(
            "SELECT photo_path FROM tickets WHERE tenant_id = ANY(:ids) AND photo_path IS NOT NULL",
            {"ids": tenant_ids},
            "tickets",
            "photo_path",
        )

    async def dele_any(table: str, col: str, id_list: list) -> None:
        if id_list and (table, col) in cols:
            await db.execute(text(f"DELETE FROM {table} WHERE {col} = ANY(:ids)"), {"ids": id_list})

    async def dele_eq(table: str, col: str, val) -> None:
        if (table, col) in cols:
            await db.execute(text(f"DELETE FROM {table} WHERE {col} = :v"), {"v": val})

    # ── A. Enfants des baux ──
    for tbl, col in [
        ("payments", "lease_id"),
        ("inspections", "lease_id"),
        ("lease_rent_revisions", "lease_id"),
        ("apurement_plans", "lease_id"),
        ("lease_exits", "lease_id"),
        ("avis_echeances", "lease_id"),
        ("charge_regularizations", "lease_id"),
        ("taxe_declarations", "lease_id"),
        ("automation_rules", "lease_id"),
        ("lease_tenants", "lease_id"),
    ]:
        await dele_any(tbl, col, lease_ids)

    # ── B. Enfants des biens ──
    for tbl, col in [
        ("candidatures", "property_id"),
        ("property_visit_slots", "property_id"),
        ("inspections", "property_id"),
        ("listings", "property_id"),
        ("signalements", "property_id"),
        ("signalement_alerts", "property_id"),
        ("entretiens", "property_id"),
    ]:
        await dele_any(tbl, col, prop_ids)

    # ── C. Enfants des locataires ──
    if tenant_ids and ("ticket_messages", "ticket_id") in cols and ("tickets", "tenant_id") in cols:
        await db.execute(
            text(
                "DELETE FROM ticket_messages WHERE ticket_id IN "
                "(SELECT id FROM tickets WHERE tenant_id = ANY(:ids))"
            ),
            {"ids": tenant_ids},
        )
    for tbl, col in [
        ("tickets", "tenant_id"),
        ("payments", "tenant_id"),
        ("apurement_plans", "tenant_id"),
        ("avis_echeances", "tenant_id"),
        ("charge_regularizations", "tenant_id"),
        ("taxe_declarations", "tenant_id"),
        ("automation_rules", "tenant_id"),
        ("signalements", "tenant_id"),
    ]:
        await dele_any(tbl, col, tenant_ids)

    # ── D/E. Baux puis biens ──
    await dele_any("leases", "id", lease_ids)
    await dele_any("properties", "id", prop_ids)

    # ── F. Locataires et propriétaires (fiches) ──
    await dele_any("tenants", "id", tenant_ids)
    await dele_any("owners", "id", owner_ids)

    # ── G. Contenus directs du gérant ──
    for tbl, col in [
        ("caf_templates", "gestionnaire_id"),
        ("user_email_domains", "user_id"),
        ("message_templates", "gestionnaire_id"),
        ("document_templates", "gestionnaire_id"),
        ("notifications", "user_id"),
        ("offers", "gestionnaire_id"),
        ("telegram_links", "user_id"),
        ("contacts", "created_by"),
        ("documents", "uploaded_by"),
        ("automation_rules", "created_by"),
        ("ticket_messages", "author_id"),
    ]:
        await dele_eq(tbl, col, g)

    # Messages propriétaire ↔ gestionnaire (du gérant et des propriétaires liés).
    msg_users = list({g, *linked_ids})
    if ("proprietaire_messages", "proprietaire_id") in cols:
        await db.execute(
            text(
                "DELETE FROM proprietaire_messages "
                "WHERE proprietaire_id = ANY(:ids) OR sender_id = ANY(:ids)"
            ),
            {"ids": msg_users},
        )

    # ── H. Comptes de connexion liés (propriétaires/locataires) ──
    await dele_any("users", "id", linked_ids)

    # ── I. Le gérant lui-même ──
    await db.delete(target)
    await db.commit()

    # ── Nettoyage disque (hors transaction : best-effort) ──
    for p in file_paths:
        try:
            delete_file(p)
        except Exception:  # noqa: BLE001
            pass

    return {"status": "deleted"}


@router.get("/stats", response_model=Stats)
async def stats(_: None = Depends(require_internal_key), db: AsyncSession = Depends(get_db)):
    managers = (
        await db.scalar(select(func.count()).select_from(User).where(User.role.in_(_MANAGER_ROLES)))
        or 0
    )
    active = (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role.in_(_MANAGER_ROLES), User.is_active.is_(True))
        )
        or 0
    )
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    return Stats(managers=managers, active_managers=active, users=total)


# ── Journal d'audit (consommé par Portail360 uniquement, jamais par l'app) ──────
class AuditLogOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    details: Any | None
    ip_address: str | None

    model_config = {"from_attributes": True}


@router.get(
    "/audit", response_model=list[AuditLogOut], dependencies=[Depends(require_internal_key)]
)
async def list_audit_logs(
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Journal d'audit Le Comptoir Immo. Réservé à la supervision (Portail360),
    via la clé interne : volontairement HORS de l'API applicative (pas d'accès
    gestionnaire). Renvoie toutes les agences (vue opérateur)."""
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if user_email:
        q = q.where(AuditLog.user_email.ilike(f"%{user_email}%"))
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    q = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()


class _SsoResolveIn(BaseModel):
    token: str


@router.post("/sso/resolve", dependencies=[Depends(require_internal_key)])
async def resolve_boutique_sso(data: _SsoResolveIn, db: AsyncSession = Depends(get_db)):
    """Résout (à usage unique) un jeton SSO « boutique de résidence ». Renvoie
    l'identité du locataire + l'id de la boutique Market. Appelé par Market."""
    from datetime import timezone

    from app.models.sso_token import BoutiqueSsoToken

    tok = (
        await db.execute(select(BoutiqueSsoToken).where(BoutiqueSsoToken.token == data.token))
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    exp = tok.expires_at if tok else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if tok is None or tok.used or (exp is not None and exp < now):
        raise HTTPException(status_code=404, detail="Jeton invalide ou expiré.")
    tok.used = True
    await db.commit()
    return {
        "email": tok.tenant_email,
        "full_name": tok.tenant_full_name,
        "boutique_id": tok.boutique_id,
    }
