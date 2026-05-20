import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.models.property import Property
from app.models.unit import Unit
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.core.exceptions import NotFoundException


class PropertyService:

    @staticmethod
    async def create(
        db: AsyncSession, data: PropertyCreate, created_by: uuid.UUID
    ) -> Property:
        prop = Property(**data.model_dump(), created_by=created_by)
        db.add(prop)
        await db.flush()
        return prop

    @staticmethod
    async def get_by_id(
        db: AsyncSession, property_id: uuid.UUID, load_units: bool = False
    ) -> Property:
        query = select(Property).where(Property.id == property_id)
        if load_units:
            query = query.options(selectinload(Property.units))
        result = await db.execute(query)
        prop = result.scalar_one_or_none()
        if not prop:
            raise NotFoundException("Bien immobilier", str(property_id))
        return prop

    @staticmethod
    async def list_all(
        db: AsyncSession,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Property], int]:
        query = select(Property)
        count_query = select(func.count(Property.id))

        if search:
            term = f"%{search.lower()}%"
            filter_expr = or_(
                func.lower(Property.name).like(term),
                func.lower(Property.city).like(term),
                func.lower(Property.address).like(term),
            )
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        query = query.order_by(Property.name)
        query = query.offset(skip).limit(limit)

        results = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(results.scalars().all()), count_result.scalar_one()

    @staticmethod
    async def update(
        db: AsyncSession, property_id: uuid.UUID, data: PropertyUpdate
    ) -> Property:
        prop = await PropertyService.get_by_id(db, property_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(prop, field, value)
        await db.flush()
        return prop

    @staticmethod
    async def delete(db: AsyncSession, property_id: uuid.UUID) -> None:
        prop = await PropertyService.get_by_id(db, property_id)
        await db.delete(prop)
        await db.flush()

    @staticmethod
    async def get_occupancy(
        db: AsyncSession, property_id: uuid.UUID
    ) -> dict:
        """Retourne le taux d'occupation du bien."""
        result = await db.execute(
            select(
                func.count(Unit.id).label("total"),
                func.sum(
                    func.cast(Unit.is_occupied, db.bind.dialect.colspecs.get(bool, func.cast(Unit.is_occupied, func.Integer)))
                ).label("occupied"),
            ).where(Unit.property_id == property_id)
        )
        row = result.one()
        total = row.total or 0
        occupied = int(row.occupied or 0)
        rate = round((occupied / total * 100), 1) if total > 0 else 0.0
        return {"total": total, "occupied": occupied, "vacant": total - occupied, "rate": rate}
