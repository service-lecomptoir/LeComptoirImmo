import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inspection import Inspection
from app.schemas.inspection import InspectionCreate, InspectionUpdate
from app.core.exceptions import NotFoundException


class InspectionService:

    @staticmethod
    async def create(
        db: AsyncSession, data: InspectionCreate, created_by: uuid.UUID
    ) -> Inspection:
        inspection = Inspection(**data.model_dump(), created_by=created_by)
        db.add(inspection)
        await db.flush()
        await db.refresh(inspection)
        return inspection

    @staticmethod
    async def get_by_id(
        db: AsyncSession, inspection_id: uuid.UUID
    ) -> Inspection:
        inspection = await db.get(Inspection, inspection_id)
        if not inspection:
            raise NotFoundException("État des lieux introuvable")
        return inspection

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        lease_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Inspection], int]:
        query = select(Inspection)
        if lease_id:
            query = query.where(Inspection.lease_id == lease_id)
        if property_id:
            query = query.where(Inspection.property_id == property_id)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar_one()

        items = (
            await db.execute(
                query.order_by(Inspection.inspection_date.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        return list(items), total

    @staticmethod
    async def update(
        db: AsyncSession, inspection_id: uuid.UUID, data: InspectionUpdate
    ) -> Inspection:
        inspection = await InspectionService.get_by_id(db, inspection_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(inspection, field, value)
        await db.flush()
        await db.refresh(inspection)
        return inspection

    @staticmethod
    async def delete(db: AsyncSession, inspection_id: uuid.UUID) -> None:
        inspection = await InspectionService.get_by_id(db, inspection_id)
        await db.delete(inspection)
        await db.flush()
