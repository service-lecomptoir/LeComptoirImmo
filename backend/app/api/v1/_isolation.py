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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.owner import Owner
from app.models.lease import Lease
from app.core.permissions import Role


async def _gp_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """IDs de tous les utilisateurs avec le rôle gestionnaire_proprio."""
    result = await db.execute(
        select(User.id).where(User.role == Role.GESTIONNAIRE_PROPRIO.value)
    )
    return list(result.scalars().all())


async def gp_user_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs (set) de tous les gestionnaire_proprio — utile pour filtrer created_by."""
    return set(await _gp_user_ids(db))


async def gp_property_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des propriétés créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Property.id).where(Property.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_tenant_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des Tenant créés par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Tenant.id).where(Tenant.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_owner_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des fiches propriétaire créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Owner.id).where(Owner.created_by.in_(gp_ids))
    )
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
    result = await db.execute(
        select(Lease.id).where(or_(*conditions))
    )
    return set(result.scalars().all())


async def assert_manager_scope(db: AsyncSession, user: User, created_by, label: str = "cette ressource") -> None:
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
    if role == Role.GESTIONNAIRE_PROPRIO:
        if created_by is None or str(created_by) != str(user.id):
            raise ForbiddenException(f"Accès refusé à {label}.")
        return
    if role == Role.GESTIONNAIRE:
        gp_ids = await gp_user_ids(db)
        if created_by in gp_ids:
            raise ForbiddenException(f"Accès refusé à {label}.")
        return
    raise ForbiddenException(f"Accès refusé à {label}.")


async def assert_payment_access(db: AsyncSession, user: User, payment, *, write: bool = False) -> None:
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
    if created_by is None and lease is not None:
        created_by = getattr(lease, "created_by", None)

    # Rôles de gestion (mandataire + legacy lecture/comptable) : hors GP
    if role in (Role.GESTIONNAIRE, Role.LECTURE, Role.COMPTABLE):
        gp_ids = await gp_user_ids(db)
        if created_by not in gp_ids:
            return
        raise ForbiddenException("Accès refusé à ce paiement.")

    if role == Role.GESTIONNAIRE_PROPRIO:
        if created_by is not None and str(created_by) == str(user.id):
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

    if role in (Role.GESTIONNAIRE, Role.LECTURE, Role.COMPTABLE):
        gp_ids = await gp_user_ids(db)
        if created_by not in gp_ids:
            return
        raise ForbiddenException("Accès refusé à cet avis d'échéance.")

    if role == Role.GESTIONNAIRE_PROPRIO:
        if created_by is not None and str(created_by) == str(user.id):
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
