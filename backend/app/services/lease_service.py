import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.lease import Lease
from app.models.property import Property
from app.schemas.lease import LeaseCreate, LeaseListItem, LeaseTerminate, LeaseUpdate


class LeaseService:
    @staticmethod
    async def create(db: AsyncSession, data: LeaseCreate, created_by: uuid.UUID) -> Lease:
        # Vérifier que le bien existe et est disponible
        prop = await db.get(Property, data.property_id)
        if not prop:
            raise NotFoundException("Bien immobilier introuvable")
        if prop.is_occupied:
            raise ConflictException("Ce bien est déjà loué (un contrat actif existe)")

        # Vérifier que le locataire n'a pas déjà un bail actif
        existing_lease = await db.execute(
            select(Lease).where(
                Lease.tenant_id == data.tenant_id,
                Lease.is_active.is_(True),
            )
        )
        if existing_lease.scalar_one_or_none():
            raise ConflictException("Ce locataire a déjà un contrat de bail actif")

        payload = data.model_dump()
        secondary_ids = payload.pop("secondary_tenant_ids", None) or []
        # Exclure le principal d'éventuels doublons dans les co-titulaires
        secondary_ids = [tid for tid in secondary_ids if str(tid) != str(data.tenant_id)]

        lease = Lease(
            **payload,
            is_active=True,
            created_by=created_by,
        )
        db.add(lease)

        # Rattacher les co-titulaires secondaires
        if secondary_ids:
            from app.models.tenant import Tenant

            res = await db.execute(select(Tenant).where(Tenant.id.in_(secondary_ids)))
            lease.co_tenants = list(res.scalars().all())

        # Marquer le bien comme occupé
        prop.is_occupied = True
        prop.is_available = False

        # L'annonce du bien passe automatiquement en « loué » (retirée de la
        # diffusion publique) dès qu'un bail est signé.
        from app.models.publishing import Listing

        listing = (
            await db.execute(select(Listing).where(Listing.property_id == data.property_id))
        ).scalar_one_or_none()
        if listing and listing.status in ("published", "scheduled"):
            listing.status = "loue"

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
                    selectinload(Lease.co_tenants),
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
        search: str | None = None,
        tenant_id: uuid.UUID | None = None,
        property_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Lease], int]:
        from app.models.property import Property
        from app.models.tenant import Tenant

        base_q = (
            select(Lease)
            .join(Tenant, Lease.tenant_id == Tenant.id)
            .join(Property, Lease.property_id == Property.id)
            .options(
                selectinload(Lease.tenant),
                selectinload(Lease.parent_property),
            )
        )

        filters = []
        if is_active is not None:
            filters.append(Lease.is_active == is_active)
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
                    func.lower(Property.name).like(s),
                    func.lower(Property.address).like(s),
                )
            )

        if filters:
            base_q = base_q.where(and_(*filters))

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await db.execute(count_q)).scalar_one()

        items = (
            (await db.execute(base_q.order_by(Lease.start_date.desc()).offset(skip).limit(limit)))
            .scalars()
            .all()
        )

        return list(items), total

    @staticmethod
    def to_list_item(lease: Lease) -> LeaseListItem:
        """Construit un LeaseListItem depuis un Lease avec relations chargées."""
        return LeaseListItem(
            id=lease.id,
            property_id=lease.property_id,
            tenant_id=lease.tenant_id,
            tenant_full_name=(lease.tenant.full_name if lease.tenant else str(lease.tenant_id)),
            property_name=(
                lease.parent_property.name if lease.parent_property else str(lease.property_id)
            ),
            owner_name=(lease.parent_property.owner_name if lease.parent_property else None),
            lease_type=lease.lease_type,
            start_date=lease.start_date,
            end_date=lease.end_date,
            rent_amount=float(lease.rent_amount),
            charges_amount=float(lease.charges_amount),
            is_active=lease.is_active,
            apl_tiers_payant=lease.apl_tiers_payant,
            apl_amount=float(lease.apl_amount) if lease.apl_amount is not None else None,
        )

    @staticmethod
    async def update(db: AsyncSession, lease_id: uuid.UUID, data: LeaseUpdate) -> Lease:
        # Charger avec co_tenants pour pouvoir réassigner la collection (async-safe)
        result = await db.execute(
            select(Lease).options(selectinload(Lease.co_tenants)).where(Lease.id == lease_id)
        )
        lease = result.scalar_one_or_none()
        if not lease:
            raise NotFoundException("Contrat introuvable")

        payload = data.model_dump(exclude_unset=True)
        secondary_ids = payload.pop("secondary_tenant_ids", None)
        # Loyer/charges : ne pas écraser directement. Toute évolution passe par une
        # révision datée (le mois courant reste figé, l'ancien montant est conservé).
        rent_eff = payload.pop("rent_effective_date", None)
        new_rent = payload.pop("rent_amount", None)
        new_charges = payload.pop("charges_amount", None)
        for field, value in payload.items():
            setattr(lease, field, value)

        # Cohérence des dates : l'entrée ne peut pas être après la sortie.
        if lease.end_date and lease.start_date and lease.start_date > lease.end_date:
            raise ConflictException(
                "La date d'entrée ne peut pas être postérieure à la date de fin du bail."
            )

        cur_rent = float(lease.rent_amount)
        cur_charges = float(lease.charges_amount)
        want_rent = float(new_rent) if new_rent is not None else cur_rent
        want_charges = float(new_charges) if new_charges is not None else cur_charges
        if round(want_rent, 2) != round(cur_rent, 2) or round(want_charges, 2) != round(
            cur_charges, 2
        ):
            from datetime import date

            from app.services.rent_revision_service import RentRevisionService, first_of_next_month

            eff = rent_eff or first_of_next_month(date.today())
            if round(want_rent, 2) != round(cur_rent, 2):
                await RentRevisionService.schedule(
                    db,
                    lease,
                    kind="rent",
                    new_amount=want_rent,
                    effective_date=eff,
                    source="manuel",
                    reason="Modification du contrat",
                )
            if round(want_charges, 2) != round(cur_charges, 2):
                await RentRevisionService.schedule(
                    db,
                    lease,
                    kind="charges",
                    new_amount=want_charges,
                    effective_date=eff,
                    source="manuel",
                    reason="Modification du contrat",
                )

        # Remplacer les co-titulaires si la liste est fournie
        if secondary_ids is not None:
            secondary_ids = [tid for tid in secondary_ids if str(tid) != str(lease.tenant_id)]
            if secondary_ids:
                from app.models.tenant import Tenant

                res = await db.execute(select(Tenant).where(Tenant.id.in_(secondary_ids)))
                lease.co_tenants = list(res.scalars().all())
            else:
                lease.co_tenants = []

        await db.flush()
        await db.refresh(lease)
        return lease

    @staticmethod
    async def terminate(db: AsyncSession, lease_id: uuid.UUID, data: LeaseTerminate) -> Lease:
        lease = await LeaseService.get_by_id(db, lease_id)
        if not lease.is_active:
            raise BadRequestException("Ce contrat est déjà résilié")

        lease.is_active = False
        lease.end_date = data.end_date
        if data.notice_date:
            lease.notice_date = data.notice_date

        # Libérer le bien
        prop = await db.get(Property, lease.property_id)
        if prop:
            prop.is_occupied = False
            prop.is_available = True

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
