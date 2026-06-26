import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.lease import Lease, lease_tenants
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    @staticmethod
    async def _sync_linked_user_phone(db: AsyncSession, tenant: Tenant) -> None:
        """Aligne le téléphone du compte de connexion lié avec celui de la fiche.

        Source de vérité du n° : la fiche si elle en a un (le gestionnaire le gère),
        sinon on récupère celui du compte (« Mes informations » du locataire). Les
        deux écrans affichent ainsi le même numéro."""
        if not getattr(tenant, "user_id", None):
            return
        from app.models.user import User

        user = await db.get(User, tenant.user_id)
        if user is None:
            return
        t_phone = tenant.phone or None
        u_phone = user.phone or None
        if t_phone == u_phone:
            return
        if t_phone:
            user.phone = t_phone
        elif u_phone:
            tenant.phone = u_phone

    @staticmethod
    async def create(db: AsyncSession, data: TenantCreate, created_by: uuid.UUID) -> Tenant:
        from app.services.reference_service import make_ref

        tenant = Tenant(**data.model_dump(), created_by=created_by)
        tenant.ref_code = await make_ref(db, Tenant.ref_code, "LO")
        db.add(tenant)
        await db.flush()
        await TenantService._sync_linked_user_phone(db, tenant)
        await db.flush()
        return tenant

    @staticmethod
    async def get_by_id(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise NotFoundException("Locataire", str(tenant_id))
        return tenant

    @staticmethod
    async def list_all(
        db: AsyncSession,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Tenant], int]:
        """Retourne (tenants, total_count) avec filtrage optionnel."""
        query = select(Tenant)
        count_query = select(func.count(Tenant.id))

        if search:
            term = f"%{search.lower()}%"
            filter_expr = or_(
                func.lower(Tenant.first_name).like(term),
                func.lower(Tenant.last_name).like(term),
                func.lower(Tenant.email).like(term),
                func.lower(Tenant.phone).like(term),
            )
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        query = query.order_by(Tenant.last_name, Tenant.first_name)
        query = query.offset(skip).limit(limit)

        results = await db.execute(query)
        count_result = await db.execute(count_query)

        return list(results.scalars().all()), count_result.scalar_one()

    @staticmethod
    async def update(db: AsyncSession, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        tenant = await TenantService.get_by_id(db, tenant_id)
        old_partage = bool(getattr(tenant, "partage_partenaires", True))
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        await db.flush()
        # Téléphone lié au compte de connexion (et inversement).
        if "phone" in update_data or "user_id" in update_data:
            await TenantService._sync_linked_user_phone(db, tenant)
            await db.flush()
        # Recharge toutes les colonnes (dont updated_at, server-onupdate, qui est
        # expirée après le flush) dans le contexte async, pour éviter un lazy-load
        # pendant la sérialisation sync de la réponse (→ ResponseValidationError 500).
        await db.refresh(tenant)
        # Exclusion « commerces partenaires » : retrait rétroactif des rattachements
        # Market (best-effort, ne bloque jamais la mise à jour).
        if "partage_partenaires" in update_data and old_partage and not tenant.partage_partenaires:
            try:
                from app.services import alice_client

                email = (tenant.email or "").strip()
                if email:
                    await alice_client.detach_residence_client(email=email)
            except Exception:  # noqa: BLE001
                pass
        return tenant

    @staticmethod
    async def delete(db: AsyncSession, tenant_id: uuid.UUID) -> None:
        tenant = await TenantService.get_by_id(db, tenant_id)

        # Un locataire rattaché à un contrat (titulaire principal ou co-titulaire)
        # ne peut pas être supprimé : la FK des baux est en RESTRICT et la
        # suppression provoquerait une erreur SQL silencieuse (500). On renvoie
        # plutôt un message clair (409).
        as_principal = (
            await db.execute(
                select(func.count()).select_from(Lease).where(Lease.tenant_id == tenant_id)
            )
        ).scalar_one()
        as_cotenant = (
            await db.execute(
                select(func.count())
                .select_from(lease_tenants)
                .where(lease_tenants.c.tenant_id == tenant_id)
            )
        ).scalar_one()
        if (as_principal or 0) + (as_cotenant or 0) > 0:
            raise ConflictException(
                "Ce locataire est rattaché à un ou plusieurs contrats. "
                "Supprimez d'abord les contrats concernés (ou retirez-le des "
                "co-titulaires) avant de supprimer le locataire."
            )

        await db.delete(tenant)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Tenant.id)))
        return result.scalar_one()
