import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.core.exceptions import NotFoundException


class TenantService:

    @staticmethod
    async def create(
        db: AsyncSession, data: TenantCreate, created_by: uuid.UUID
    ) -> Tenant:
        tenant = Tenant(**data.model_dump(), created_by=created_by)
        db.add(tenant)
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
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Tenant], int]:
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
    async def update(
        db: AsyncSession, tenant_id: uuid.UUID, data: TenantUpdate
    ) -> Tenant:
        tenant = await TenantService.get_by_id(db, tenant_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        await db.flush()
        # Recharge toutes les colonnes (dont updated_at, server-onupdate, qui est
        # expirée après le flush) dans le contexte async, pour éviter un lazy-load
        # pendant la sérialisation sync de la réponse (→ ResponseValidationError 500).
        await db.refresh(tenant)
        return tenant

    @staticmethod
    async def delete(db: AsyncSession, tenant_id: uuid.UUID) -> None:
        tenant = await TenantService.get_by_id(db, tenant_id)
        await db.delete(tenant)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Tenant.id)))
        return result.scalar_one()
