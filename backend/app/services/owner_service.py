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
    async def get_finances(db: AsyncSession, owner_id: uuid.UUID, year: int) -> dict:
        """Agrège revenus, performance par bien et synthèse fiscale d'un propriétaire/année."""
        from sqlalchemy.orm import selectinload
        from app.models.lease import Lease
        from app.models.payment import Payment

        owner = await db.get(Owner, owner_id)
        if not owner:
            raise NotFoundException("Propriétaire introuvable")

        props = (await db.execute(
            select(Property).where(Property.owner_id == owner_id)
        )).scalars().all()
        prop_ids = [p.id for p in props]

        leases = []
        if prop_ids:
            leases = (await db.execute(
                select(Lease).where(Lease.property_id.in_(prop_ids))
            )).scalars().all()
        lease_ids = [l.id for l in leases]

        payments = []
        if lease_ids:
            payments = (await db.execute(
                select(Payment)
                .options(
                    selectinload(Payment.tenant),
                    selectinload(Payment.lease).selectinload(Lease.parent_property),
                )
                .where(Payment.lease_id.in_(lease_ids), Payment.period_year == year)
                .order_by(Payment.period_month)
            )).scalars().all()

        lignes = []
        total_du = total_percu = loyers = charges = apl = 0.0
        for p in payments:
            total_du += float(p.amount_due)
            total_percu += float(p.amount_paid)
            loyers += float(p.amount_rent or 0)
            charges += float(p.amount_charges or 0)
            apl += float(p.amount_apl or 0)
            lignes.append({
                "period_label": p.period_label,
                "period_month": p.period_month,
                "property_name": p.lease.parent_property.name if p.lease and p.lease.parent_property else "",
                "tenant_full_name": p.tenant.full_name if p.tenant else "",
                "amount_due": float(p.amount_due),
                "amount_paid": float(p.amount_paid),
                "status": p.status,
                "payment_date": p.payment_date,
            })

        biens = []
        for prop in props:
            active = next((l for l in leases if l.property_id == prop.id and l.is_active), None)
            pp = [p for p in payments if p.lease and p.lease.property_id == prop.id]
            biens.append({
                "property_id": prop.id,
                "property_name": prop.name,
                "city": prop.city,
                "rent": float(active.rent_amount) if active else 0.0,
                "charges": float(active.charges_amount) if active else 0.0,
                "total_du": round(sum(float(x.amount_due) for x in pp), 2),
                "total_percu": round(sum(float(x.amount_paid) for x in pp), 2),
                "is_occupied": bool(prop.is_occupied),
            })

        return {
            "owner_id": owner.id,
            "owner_name": owner.full_name,
            "year": year,
            "revenus": {
                "total_du": round(total_du, 2),
                "total_percu": round(total_percu, 2),
                "lignes": lignes,
            },
            "biens": biens,
            "fiscal": {
                "loyers": round(loyers, 2),
                "charges": round(charges, 2),
                "apl": round(apl, 2),
                "total_du": round(total_du, 2),
                "total_percu": round(total_percu, 2),
            },
        }

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
