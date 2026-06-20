"""
Helpers d'isolation des données par rôle.

Un gestionnaire mandataire (Role.GESTIONNAIRE) ne doit jamais voir les données
appartenant à un gestionnaire_proprio (Role.GESTIONNAIRE_PROPRIO).

Règle d'identification : on utilise TOUJOURS `created_by` pour identifier
à qui appartient une ressource. C'est le seul champ fiable car il est
automatiquement rempli avec l'ID de l'utilisateur connecté au moment de
la création (voir PropertyService.create, TenantService.create).

  - Propriétés dont created_by est un gestionnaire_proprio
  - Locataires (Tenant) dont created_by est un gestionnaire_proprio
  - Baux portant sur ces propriétés ou liés à ces locataires
  - Paiements, tickets, avis, entretiens qui en dépendent
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.lease import Lease
from app.models.owner import Owner
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User


async def _gp_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """IDs de tous les utilisateurs avec le rôle gestionnaire_proprio."""
    result = await db.execute(select(User.id).where(User.role == Role.GESTIONNAIRE_PROPRIO.value))
    return list(result.scalars().all())


async def gp_user_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs (set) de tous les gestionnaire_proprio — utile pour filtrer created_by."""
    return set(await _gp_user_ids(db))


async def gp_property_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des propriétés créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(select(Property.id).where(Property.created_by.in_(gp_ids)))
    return set(result.scalars().all())


async def gp_tenant_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des Tenant créés par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(select(Tenant.id).where(Tenant.created_by.in_(gp_ids)))
    return set(result.scalars().all())


async def gp_owner_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des fiches propriétaire créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(select(Owner.id).where(Owner.created_by.in_(gp_ids)))
    return set(result.scalars().all())


async def gp_lease_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des baux liés aux propriétés OU aux locataires de gestionnaire_proprio."""
    prop_ids = await gp_property_ids(db)
    tenant_ids = await gp_tenant_ids(db)
    if not prop_ids and not tenant_ids:
        return set()
    conditions = []
    if prop_ids:
        conditions.append(Lease.property_id.in_(prop_ids))
    if tenant_ids:
        conditions.append(Lease.tenant_id.in_(tenant_ids))
    from sqlalchemy import or_

    result = await db.execute(select(Lease.id).where(or_(*conditions)))
    return set(result.scalars().all())


# ── Isolation par AGENCE (multi-tenant) ──────────────────────────────────────
# Une agence = un compte principal (created_by NULL) + tous ses sous-comptes.
# Périmètre effectif d'un utilisateur : COALESCE(agency_id, id). Un manager ne voit
# QUE les ressources dont `created_by` appartient à sa propre agence.


def agency_root(user: User) -> uuid.UUID:
    return getattr(user, "agency_id", None) or user.id


async def agency_member_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """IDs des utilisateurs de la même agence que `user` (principal + sous-comptes)."""
    root = agency_root(user)
    rows = await db.execute(select(User.id).where(func.coalesce(User.agency_id, User.id) == root))
    return set(rows.scalars().all())


async def agency_property_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    members = await agency_member_ids(db, user)
    if not members:
        return set()
    rows = await db.execute(select(Property.id).where(Property.created_by.in_(members)))
    return set(rows.scalars().all())


async def agency_tenant_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    members = await agency_member_ids(db, user)
    if not members:
        return set()
    rows = await db.execute(select(Tenant.id).where(Tenant.created_by.in_(members)))
    return set(rows.scalars().all())


async def agency_owner_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    members = await agency_member_ids(db, user)
    if not members:
        return set()
    rows = await db.execute(select(Owner.id).where(Owner.created_by.in_(members)))
    return set(rows.scalars().all())


async def agency_lease_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """Baux de l'agence : créés par un membre, OU liés à un bien/locataire de l'agence."""
    members = await agency_member_ids(db, user)
    prop_ids = await agency_property_ids(db, user)
    tenant_ids = await agency_tenant_ids(db, user)
    from sqlalchemy import or_

    conds = [Lease.created_by.in_(members)] if members else []
    if prop_ids:
        conds.append(Lease.property_id.in_(prop_ids))
    if tenant_ids:
        conds.append(Lease.tenant_id.in_(tenant_ids))
    if not conds:
        return set()
    rows = await db.execute(select(Lease.id).where(or_(*conds)))
    return set(rows.scalars().all())


_MANAGER_ROLES_ISO = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO, Role.LECTURE, Role.COMPTABLE)


async def _manager_in_agency(db: AsyncSession, user: User, created_by) -> bool:
    """Vrai si `created_by` appartient à l'agence du manager `user`."""
    if created_by is None:
        return False
    members = await agency_member_ids(db, user)
    return created_by in members


async def _manager_in_agency_any(db: AsyncSession, user: User, *created_bys) -> bool:
    """Vrai si AU MOINS UN des `created_by` candidats appartient à l'agence.

    Utilisé pour les ressources « dérivées » (bail/paiement/avis) dont le created_by
    propre peut être NULL (ex. créateur supprimé) mais qui restent rattachées à un
    bien/locataire de l'agence."""
    cands = {c for c in created_bys if c is not None}
    if not cands:
        return False
    members = await agency_member_ids(db, user)
    return bool(cands & members)


async def assert_manager_scope(
    db: AsyncSession, user: User, created_by, label: str = "cette ressource"
) -> None:
    """Garde-fou d'isolation pour les endpoints de gestion identifiés par `created_by`.

    - admin : accès total ;
    - gestionnaire_proprio (GP) : uniquement SES ressources (created_by == lui) ;
    - gestionnaire mandataire : tout SAUF les ressources appartenant à un GP ;
    - autres rôles (propriétaire/locataire) : pas d'accès à ces ressources de gestion
      (ils disposent d'endpoints dédiés et filtrés).

    Lève ForbiddenException si l'accès n'est pas autorisé.
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return
    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency(db, user, created_by):
            return
        raise ForbiddenException(f"Accès refusé à {label}.")
    raise ForbiddenException(f"Accès refusé à {label}.")


async def assert_lease_access(db: AsyncSession, user: User, lease, *, write: bool = False) -> None:
    """Isolation par rôle d'un bail (chargé avec `parent_property` et `tenant`).

    - admin : tout ;
    - gestionnaire mandataire / lecture / comptable : tout SAUF baux d'un GP ;
    - gestionnaire_proprio : uniquement les siens (created_by) ;
    - propriétaire (lecture) : baux sur ses biens (parent_property.owner_user_id) ;
    - locataire (lecture) : uniquement son bail (tenant.user_id).
    `write=True` interdit propriétaire et locataire.
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return
    created_by = getattr(lease, "created_by", None)
    _prop = getattr(lease, "parent_property", None)
    _tenant = getattr(lease, "tenant", None)

    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency_any(
            db,
            user,
            created_by,
            getattr(_prop, "created_by", None),
            getattr(_tenant, "created_by", None),
        ):
            return
        raise ForbiddenException("Accès refusé à ce contrat.")

    if not write:
        if role == Role.PROPRIETAIRE:
            prop = getattr(lease, "parent_property", None)
            if prop is not None and str(getattr(prop, "owner_user_id", None)) == str(user.id):
                return
        if role == Role.LOCATAIRE:
            tenant = getattr(lease, "tenant", None)
            if tenant is not None and str(getattr(tenant, "user_id", None)) == str(user.id):
                return

    raise ForbiddenException("Accès refusé à ce contrat.")


async def assert_ticket_access(
    db: AsyncSession, user: User, ticket, *, manager_only: bool = False
) -> None:
    """Isolation par rôle d'une démarche (ticket), via le locataire rattaché.

    - admin : tout ;
    - gestionnaire_proprio : tickets de SES locataires (tenant.created_by==lui) ;
    - mandataire / lecture / comptable : tout SAUF locataires d'un GP ;
    - locataire : uniquement SES tickets (tenant.user_id==lui) ;
    - propriétaire (lecture) : tickets des locataires de SES biens.
    `manager_only=True` (actions de gestion) interdit locataire et propriétaire.
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return
    tenant = await db.get(Tenant, ticket.tenant_id)
    created_by = getattr(tenant, "created_by", None) if tenant else None

    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency(db, user, created_by):
            return
        raise ForbiddenException("Accès refusé à cette démarche.")

    if not manager_only:
        if role == Role.LOCATAIRE:
            if tenant is not None and str(getattr(tenant, "user_id", None)) == str(user.id):
                return
        if role == Role.PROPRIETAIRE:
            owners = (
                (
                    await db.execute(
                        select(Property.owner_user_id)
                        .join(Lease, Lease.property_id == Property.id)
                        .where(Lease.tenant_id == ticket.tenant_id)
                    )
                )
                .scalars()
                .all()
            )
            if any(str(o) == str(user.id) for o in owners):
                return

    raise ForbiddenException("Accès refusé à cette démarche.")


async def assert_payment_access(
    db: AsyncSession, user: User, payment, *, write: bool = False
) -> None:
    """Isolation par rôle d'un paiement (chargé avec `load_relations=True`).

    Périmètre :
      - admin : tout ;
      - gestionnaire mandataire / lecture / comptable : tout SAUF paiements d'un GP ;
      - gestionnaire_proprio : uniquement les siens (created_by) ;
      - propriétaire (lecture seule) : paiements des biens dont il est propriétaire ;
      - locataire (lecture seule) : uniquement ses propres paiements.

    `write=True` interdit propriétaire et locataire (actions réservées à la gestion).
    Lève ForbiddenException sinon.
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return

    created_by = getattr(payment, "created_by", None)
    lease = getattr(payment, "lease", None)
    _prop = getattr(lease, "parent_property", None) if lease is not None else None
    _tenant = getattr(payment, "tenant", None)

    # Rôles de gestion : uniquement les paiements de leur agence
    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency_any(
            db,
            user,
            created_by,
            getattr(lease, "created_by", None),
            getattr(_prop, "created_by", None),
            getattr(_tenant, "created_by", None),
        ):
            return
        raise ForbiddenException("Accès refusé à ce paiement.")

    if not write:
        if role == Role.PROPRIETAIRE:
            prop = getattr(lease, "parent_property", None) if lease is not None else None
            if prop is not None and str(getattr(prop, "owner_user_id", None)) == str(user.id):
                return
        if role == Role.LOCATAIRE:
            tenant = getattr(payment, "tenant", None)
            if tenant is not None and str(getattr(tenant, "user_id", None)) == str(user.id):
                return

    raise ForbiddenException("Accès refusé à ce paiement.")


async def assert_avis_access(db: AsyncSession, user: User, avis, *, write: bool = False) -> None:
    """Isolation par rôle d'un avis d'échéance (chargé avec ses relations
    `tenant` et `lease.parent_property`).

    Mêmes règles que les paiements (l'avis n'a pas de `created_by` propre :
    on s'appuie sur `lease.created_by`).
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return

    lease = getattr(avis, "lease", None)
    created_by = getattr(lease, "created_by", None) if lease is not None else None
    _prop = getattr(lease, "parent_property", None) if lease is not None else None
    _tenant = getattr(avis, "tenant", None)

    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency_any(
            db,
            user,
            created_by,
            getattr(_prop, "created_by", None),
            getattr(_tenant, "created_by", None),
        ):
            return
        raise ForbiddenException("Accès refusé à cet avis d'échéance.")

    if not write:
        if role == Role.PROPRIETAIRE:
            prop = getattr(lease, "parent_property", None) if lease is not None else None
            if prop is not None and str(getattr(prop, "owner_user_id", None)) == str(user.id):
                return
        if role == Role.LOCATAIRE:
            tenant = getattr(avis, "tenant", None)
            if tenant is not None and str(getattr(tenant, "user_id", None)) == str(user.id):
                return

    raise ForbiddenException("Accès refusé à cet avis d'échéance.")


async def assert_document_access(
    db: AsyncSession, user: User, document, *, write: bool = False
) -> None:
    """Isolation par rôle d'un document, selon son entité de rattachement
    (`entity_type` ∈ tenant / lease / property / owner : autres types = gestion seule).

    On résout les clés d'appartenance depuis l'entité liée, puis on applique la
    même matrice que paiements/avis. Aligné sur l'isolation des LISTES de documents.
    """
    from app.core.exceptions import ForbiddenException
    from app.models.document import EntityType

    role = Role(user.role)
    if role == Role.ADMIN:
        return

    _et = getattr(document, "entity_type", None)
    et = _et.value if hasattr(_et, "value") else str(_et or "")
    eid = getattr(document, "entity_id", None)
    created_by = owner_user_id = tenant_user_id = None

    if et == EntityType.TENANT.value and eid is not None:
        t = await db.get(Tenant, eid)
        if t is not None:
            created_by, tenant_user_id = t.created_by, getattr(t, "user_id", None)
    elif et == EntityType.PROPERTY.value and eid is not None:
        p = await db.get(Property, eid)
        if p is not None:
            created_by, owner_user_id = p.created_by, getattr(p, "owner_user_id", None)
    elif et == EntityType.OWNER.value and eid is not None:
        o = await db.get(Owner, eid)
        if o is not None:
            created_by, owner_user_id = o.created_by, getattr(o, "user_id", None)
    elif et == EntityType.LEASE.value and eid is not None:
        le = await db.get(Lease, eid)
        if le is not None:
            created_by = le.created_by
            if le.tenant_id:
                t = await db.get(Tenant, le.tenant_id)
                tenant_user_id = getattr(t, "user_id", None) if t else None
            if le.property_id:
                p = await db.get(Property, le.property_id)
                owner_user_id = getattr(p, "owner_user_id", None) if p else None

    if role in _MANAGER_ROLES_ISO:
        if await _manager_in_agency(db, user, created_by):
            return
        raise ForbiddenException("Accès refusé à ce document.")

    if not write:
        if (
            role == Role.PROPRIETAIRE
            and owner_user_id is not None
            and str(owner_user_id) == str(user.id)
        ):
            return
        if (
            role == Role.LOCATAIRE
            and tenant_user_id is not None
            and str(tenant_user_id) == str(user.id)
        ):
            return

    raise ForbiddenException("Accès refusé à ce document.")
