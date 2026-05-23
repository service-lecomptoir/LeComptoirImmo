import uuid
from typing import Optional
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lease import Lease
from app.models.unit import Unit
from app.schemas.lease import LeaseCreate, LeaseUpdate, LeaseTerminate, LeaseListItem
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException


class LeaseService:

    @staticmethod
    async def create(
        db: AsyncSession, data: LeaseCreate, created_by: uuid.UUID
    ) -> Lease:
        # Vérifier que le logement existe et appartient au bien
        unit = await db.get(Unit, data.unit_id)
        if not unit:
            raise NotFoundException("Logement introuvable")
        if str(unit.property_id) != str(data.property_id):
            raise BadRequestException("Ce logement n'appartient pas à ce bien")
        if unit.is_occupied:
            raise ConflictException("Ce logement est déjà occupé")

        lease = Lease(
            **data.model_dump(),
            is_active=True,
            created_by=created_by,
        )
        db.add(lease)

        # Marquer le logement comme occupé
        unit.is_occupied = True
        unit.is_available = False

        await db.flush()
        await db.refresh(lease)
        return lease

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        lease_id: uuid.UUID,
        load_relations: bool = False,
    ) -> Lease:
        if load_relations:
            result = await db.execute(
                select(Lease)
                .options(
                    selectinload(Lease.tenant),
                    selectinload(Lease.unit),
                    selectinload(Lease.parent_property),
                    selectinload(Lease.inspections),
                )
                .where(Lease.id == lease_id)
            )
            lease = result.scalar_one_or_none()
        else:
            lease = await db.get(Lease, lease_id)
        if not lease:
            raise NotFoundException("Contrat introuvable")
        return lease

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        search: Optional[str] = None,
        unit_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Lease], int]:
        from app.models.tenant import Tenant
        from app.models.unit import Unit as UnitModel
        from app.models.property import Property

        base_q = (
            select(Lease)
            .join(Tenant, Lease.tenant_id == Tenant.id)
            .join(UnitModel, Lease.unit_id == UnitModel.id)
            .join(Property, Lease.property_id == Property.id)
            .options(
                selectinload(Lease.tenant),
                selectinload(Lease.unit),
                selectinload(Lease.parent_property),
            )
        )

        filters = []
        if is_active is not None:
            filters.append(Lease.is_active == is_active)
        if unit_id:
            filters.append(Lease.unit_id == unit_id)
        if tenant_id:
            filters.append(Lease.tenant_id == tenant_id)
        if property_id:
            filters.append(Lease.property_id == property_id)
        if search:
            s = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(Tenant.first_name).like(s),
                    func.lower(Tenant.last_name).like(s),
                    func.lower(UnitModel.unit_ref).like(s),
                    func.lower(Property.name).like(s),
                )
            )

        if filters:
            base_q = base_q.where(and_(*filters))

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await db.execute(count_q)).scalar_one()

        items = (
            await db.execute(
                base_q.order_by(Lease.start_date.desc()).offset(skip).limit(limit)
            )
        ).scalars().all()

        return list(items), total

    @staticmethod
    def to_list_item(lease: Lease) -> LeaseListItem:
        """Construit un LeaseListItem depuis un Lease avec relations chargées."""
        return LeaseListItem(
            id=lease.id,
            property_id=lease.property_id,
            unit_id=lease.unit_id,
            tenant_id=lease.tenant_id,
            tenant_full_name=(
                lease.tenant.full_name if lease.tenant else str(lease.tenant_id)
            ),
            unit_ref=lease.unit.unit_ref if lease.unit else str(lease.unit_id),
            property_name=(
                lease.parent_property.name
                if lease.parent_property
                else str(lease.property_id)
            ),
            lease_type=lease.lease_type,
            start_date=lease.start_date,
            end_date=lease.end_date,
            rent_amount=float(lease.rent_amount),
            charges_amount=float(lease.charges_amount),
            is_active=lease.is_active,
            apl_tiers_payant=lease.apl_tiers_payant,
        )

    @staticmethod
    async def update(
        db: AsyncSession, lease_id: uuid.UUID, data: LeaseUpdate
    ) -> Lease:
        lease = await LeaseService.get_by_id(db, lease_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(lease, field, value)
        await db.flush()
        await db.refresh(lease)
        return lease

    @staticmethod
    async def terminate(
        db: AsyncSession, lease_id: uuid.UUID, data: LeaseTerminate
    ) -> Lease:
        lease = await LeaseService.get_by_id(db, lease_id)
        if not lease.is_active:
            raise BadRequestException("Ce contrat est déjà résilié")

        lease.is_active = False
        lease.end_date = data.end_date
        if data.notice_date:
            lease.notice_date = data.notice_date

        # Libérer le logement
        unit = await db.get(Unit, lease.unit_id)
        if unit:
            unit.is_occupied = False
            unit.is_available = True

        await db.flush()
        await db.refresh(lease)
        return lease

    @staticmethod
    async def delete(db: AsyncSession, lease_id: uuid.UUID) -> None:
        lease = await LeaseService.get_by_id(db, lease_id)
        if lease.is_active:
            raise BadRequestException(
                "Impossible de supprimer un contrat actif. Résiliez-le d'abord."
            )
        await db.delete(lease)
        await db.flush()
