import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entretien import Prestataire, Entretien
from app.schemas.entretien import PrestataireCreate, PrestataireUpdate, EntretienCreate, EntretienUpdate
from app.core.exceptions import NotFoundException


class PrestataireService:

    @staticmethod
    async def create(db: AsyncSession, data: PrestataireCreate) -> Prestataire:
        p = Prestataire(**data.model_dump())
        db.add(p)
        await db.flush()
        await db.refresh(p)
        return p

    @staticmethod
    async def get(db: AsyncSession, prestataire_id: uuid.UUID) -> Prestataire:
        result = await db.execute(select(Prestataire).where(Prestataire.id == prestataire_id))
        p = result.scalar_one_or_none()
        if not p:
            raise NotFoundException("Prestataire", str(prestataire_id))
        return p

    @staticmethod
    async def list_all(db: AsyncSession, active_only: bool = True) -> list[Prestataire]:
        q = select(Prestataire)
        if active_only:
            q = q.where(Prestataire.is_active == True)
        q = q.order_by(Prestataire.name)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, prestataire_id: uuid.UUID, data: PrestataireUpdate) -> Prestataire:
        p = await PrestataireService.get(db, prestataire_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(p, field, value)
        await db.flush()
        return p

    @staticmethod
    async def delete(db: AsyncSession, prestataire_id: uuid.UUID) -> None:
        p = await PrestataireService.get(db, prestataire_id)
        await db.delete(p)
        await db.flush()


class EntretienService:

    @staticmethod
    async def create(db: AsyncSession, data: EntretienCreate) -> Entretien:
        e = Entretien(**data.model_dump())
        db.add(e)
        await db.flush()
        await db.refresh(e)
        return e

    @staticmethod
    async def get(db: AsyncSession, entretien_id: uuid.UUID) -> Entretien:
        result = await db.execute(
            select(Entretien)
            .options(selectinload(Entretien.prestataire), selectinload(Entretien.property), selectinload(Entretien.unit))
            .where(Entretien.id == entretien_id)
        )
        e = result.scalar_one_or_none()
        if not e:
            raise NotFoundException("Entretien", str(entretien_id))
        return e

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        property_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Entretien], int]:
        q = select(Entretien).options(
            selectinload(Entretien.prestataire),
            selectinload(Entretien.property),
            selectinload(Entretien.unit),
        )
        if status:
            q = q.where(Entretien.status == status)
        if property_id:
            q = q.where(Entretien.property_id == property_id)
        q = q.order_by(Entretien.scheduled_date.asc())

        count_q = select(func.count(Entretien.id))
        if status:
            count_q = count_q.where(Entretien.status == status)
        if property_id:
            count_q = count_q.where(Entretien.property_id == property_id)

        total = (await db.execute(count_q)).scalar_one()
        items = list((await db.execute(q.offset(offset).limit(limit))).scalars().all())
        return items, total

    @staticmethod
    async def update(db: AsyncSession, entretien_id: uuid.UUID, data: EntretienUpdate) -> Entretien:
        e = await EntretienService.get(db, entretien_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(e, field, value)
        await db.flush()
        return e

    @staticmethod
    async def delete(db: AsyncSession, entretien_id: uuid.UUID) -> None:
        e = await EntretienService.get(db, entretien_id)
        await db.delete(e)
        await db.flush()
