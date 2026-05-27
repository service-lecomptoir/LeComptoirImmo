import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.core.exceptions import NotFoundException


class PropertyService:

    @staticmethod
    async def _enrich_owner(db: AsyncSession, data_dict: dict) -> dict:
        """Synchronise les champs dénormalisés du propriétaire depuis la fiche Owner.

        La fiche (`owner_id`) est la source de vérité : on en dérive `owner_user_id`
        (compte de connexion), `owner_name`, `owner_email`, `owner_phone` — utilisés
        pour l'isolation et les modèles PDF. À défaut de fiche, on retombe sur l'ancien
        comportement (compte lié `owner_user_id`)."""
        from sqlalchemy import select
        from app.models.owner import Owner

        owner_id = data_dict.get("owner_id")
        # Pas de fiche fournie mais un compte propriétaire (cas gestionnaire-propriétaire
        # ou flux historique) : rattacher à la fiche de ce compte si elle existe.
        if not owner_id:
            owner_user_id = data_dict.get("owner_user_id")
            if owner_user_id:
                owner = (await db.execute(
                    select(Owner).where(Owner.user_id == owner_user_id)
                )).scalars().first()
                if owner:
                    data_dict["owner_id"] = owner.id
                    owner_id = owner.id

        if owner_id:
            owner = await db.get(Owner, owner_id)
            if owner:
                data_dict["owner_user_id"] = owner.user_id
                data_dict["owner_name"] = owner.full_name
                data_dict["owner_email"] = owner.email
                data_dict["owner_phone"] = owner.phone
            return data_dict

        # Aucun propriétaire identifiable — comportement historique (compte direct).
        owner_user_id = data_dict.get("owner_user_id")
        if owner_user_id:
            from app.models.user import User
            user = await db.get(User, owner_user_id)
            if user:
                if not data_dict.get("owner_name"):
                    data_dict["owner_name"] = user.full_name
                if not data_dict.get("owner_email"):
                    data_dict["owner_email"] = user.email
        return data_dict

    @staticmethod
    async def create(
        db: AsyncSession, data: PropertyCreate, created_by: uuid.UUID
    ) -> Property:
        data_dict = await PropertyService._enrich_owner(db, data.model_dump())
        prop = Property(**data_dict, created_by=created_by)
        db.add(prop)
        await db.flush()
        await db.refresh(prop)
        return prop

    @staticmethod
    async def get_by_id(
        db: AsyncSession, property_id: uuid.UUID, load_units: bool = False
    ) -> Property:
        result = await db.execute(select(Property).where(Property.id == property_id))
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

        query = query.order_by(Property.name).offset(skip).limit(limit)

        results = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(results.scalars().all()), count_result.scalar_one()

    @staticmethod
    async def update(
        db: AsyncSession, property_id: uuid.UUID, data: PropertyUpdate
    ) -> Property:
        prop = await PropertyService.get_by_id(db, property_id)
        update_data = data.model_dump(exclude_unset=True)
        update_data = await PropertyService._enrich_owner(db, update_data)
        for field, value in update_data.items():
            setattr(prop, field, value)
        await db.flush()
        await db.refresh(prop)
        return prop

    @staticmethod
    async def delete(db: AsyncSession, property_id: uuid.UUID) -> None:
        prop = await PropertyService.get_by_id(db, property_id)
        await db.delete(prop)
        await db.flush()

    @staticmethod
    async def get_occupancy(db: AsyncSession, property_id: uuid.UUID) -> dict:
        """Occupation du bien (un bien = un logement)."""
        prop = await PropertyService.get_by_id(db, property_id)
        occupied = 1 if prop.is_occupied else 0
        return {
            "total": 1,
            "occupied": occupied,
            "vacant": 1 - occupied,
            "rate": 100.0 if occupied else 0.0,
        }
