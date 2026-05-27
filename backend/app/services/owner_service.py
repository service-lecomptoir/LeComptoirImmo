import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update

from app.models.owner import Owner
from app.models.property import Property
from app.schemas.owner import OwnerCreate, OwnerUpdate
from app.core.exceptions import NotFoundException


class OwnerService:

    @staticmethod
    async def sync_properties(db: AsyncSession, owner: Owner) -> None:
        """Répercute l'identité/RIB/compte de la fiche sur les biens liés.
        `owner_user_id`, `owner_name`, `owner_email`, `owner_phone` sont des copies
        dénormalisées de la fiche (utilisées pour l'isolation et les modèles PDF)."""
        await db.execute(
            update(Property)
            .where(Property.owner_id == owner.id)
            .values(
                owner_user_id=owner.user_id,
                owner_name=owner.full_name,
                owner_email=owner.email,
                owner_phone=owner.phone,
            )
            .execution_options(synchronize_session=False)
        )

    @staticmethod
    async def create(
        db: AsyncSession, data: OwnerCreate, created_by: uuid.UUID
    ) -> Owner:
        owner = Owner(**data.model_dump(), created_by=created_by)
        db.add(owner)
        await db.flush()
        return owner

    @staticmethod
    async def get_by_id(db: AsyncSession, owner_id: uuid.UUID) -> Owner:
        result = await db.execute(select(Owner).where(Owner.id == owner_id))
        owner = result.scalar_one_or_none()
        if not owner:
            raise NotFoundException("Propriétaire", str(owner_id))
        return owner

    @staticmethod
    async def list_all(
        db: AsyncSession,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Owner], int]:
        query = select(Owner)
        count_query = select(func.count(Owner.id))

        if search:
            term = f"%{search.lower()}%"
            filter_expr = or_(
                func.lower(Owner.first_name).like(term),
                func.lower(Owner.last_name).like(term),
                func.lower(Owner.company_name).like(term),
                func.lower(Owner.email).like(term),
                func.lower(Owner.phone).like(term),
            )
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        query = query.order_by(Owner.last_name, Owner.first_name)
        query = query.offset(skip).limit(limit)

        results = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(results.scalars().all()), count_result.scalar_one()

    @staticmethod
    async def update(
        db: AsyncSession, owner_id: uuid.UUID, data: OwnerUpdate
    ) -> Owner:
        owner = await OwnerService.get_by_id(db, owner_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(owner, field, value)
        await db.flush()
        # La fiche est la source de vérité → répercuter sur les biens liés.
        await OwnerService.sync_properties(db, owner)
        await db.flush()
        # Recharge toutes les colonnes dans le contexte async pour éviter un
        # lazy-load pendant la sérialisation de la réponse.
        await db.refresh(owner)
        return owner

    @staticmethod
    async def delete(db: AsyncSession, owner_id: uuid.UUID) -> None:
        owner = await OwnerService.get_by_id(db, owner_id)
        await db.delete(owner)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Owner.id)))
        return result.scalar_one()
