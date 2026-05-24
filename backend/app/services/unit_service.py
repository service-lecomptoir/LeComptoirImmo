import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.unit import Unit
from app.models.property import Property
from app.schemas.unit import UnitCreate, UnitUpdate
from app.core.exceptions import NotFoundException, BadRequestException


class UnitService:

    @staticmethod
    async def create(db: AsyncSession, data: UnitCreate) -> Unit:
        # Vérifie que le bien parent existe
        prop_result = await db.execute(
            select(Property).where(Property.id == data.property_id)
        )
        property_obj = prop_result.scalar_one_or_none()
        if not property_obj:
            raise NotFoundException("Bien immobilier", str(data.property_id))

        # Seuls les immeubles peuvent avoir plusieurs logements
        if property_obj.property_type != 'immeuble':
            count_result = await db.execute(
                select(func.count(Unit.id)).where(Unit.property_id == data.property_id)
            )
            if (count_result.scalar() or 0) >= 1:
                raise BadRequestException(
                    "Ce type de bien ne peut contenir qu'un seul logement. "
                    "Seuls les immeubles peuvent avoir plusieurs logements."
                )

        # Vérifie l'unicité de la référence au sein du bien
        existing = await db.execute(
            select(Unit).where(
                Unit.property_id == data.property_id,
                Unit.unit_ref == data.unit_ref,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException(
                f"La référence '{data.unit_ref}' est déjà utilisée dans ce bien"
            )

        unit = Unit(**data.model_dump())
        db.add(unit)
        await db.flush()
        return unit

    @staticmethod
    async def get_by_id(db: AsyncSession, unit_id: uuid.UUID) -> Unit:
        result = await db.execute(select(Unit).where(Unit.id == unit_id))
        unit = result.scalar_one_or_none()
        if not unit:
            raise NotFoundException("Logement", str(unit_id))
        return unit

    @staticmethod
    async def list_by_property(
        db: AsyncSession, property_id: uuid.UUID
    ) -> List[Unit]:
        result = await db.execute(
            select(Unit)
            .where(Unit.property_id == property_id)
            .order_by(Unit.floor, Unit.unit_ref)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_all(
        db: AsyncSession,
        property_id: Optional[uuid.UUID] = None,
        only_available: bool = False,
    ) -> List[Unit]:
        query = select(Unit)
        if property_id:
            query = query.where(Unit.property_id == property_id)
        if only_available:
            query = query.where(Unit.is_occupied.is_(False), Unit.is_available.is_(True))
        query = query.order_by(Unit.property_id, Unit.floor, Unit.unit_ref)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession, unit_id: uuid.UUID, data: UnitUpdate
    ) -> Unit:
        unit = await UnitService.get_by_id(db, unit_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(unit, field, value)
        await db.flush()
        return unit

    @staticmethod
    async def delete(db: AsyncSession, unit_id: uuid.UUID) -> None:
        unit = await UnitService.get_by_id(db, unit_id)
        if unit.is_occupied:
            raise BadRequestException(
                "Impossible de supprimer un logement occupé. "
                "Résiliez d'abord le contrat de bail."
            )
        await db.delete(unit)
        await db.flush()
