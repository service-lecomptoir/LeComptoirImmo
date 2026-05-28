import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import Payment, PaymentStatus
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.property import Property
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentRecordIn,
    PaymentListItem,
    MonthlyStats,
    DashboardStats,
)
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException


class PaymentService:

    @staticmethod
    def _compute_due_date(year: int, month: int, payment_day: int) -> date:
        """Calcule la date d'échéance."""
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        day = min(payment_day, max_day)
        return date(year, month, day)

    @staticmethod
    async def generate_for_lease(
        db: AsyncSession,
        lease: Lease,
        year: int,
        month: int,
        created_by: Optional[uuid.UUID] = None,
    ) -> Payment:
        """Génère un enregistrement de loyer pour un bail et une période.

        La période couvre N mois selon `lease.payment_frequency` (1 = mensuel), avec
        prorata d'entrée/sortie pour la règle calendaire. (year, month) peut être
        n'importe quel mois de la période ; la clé retenue est le premier mois couvert.
        """
        from app.services.billing_period import compute_period

        bp = compute_period(lease, year, month)
        if bp is None:
            raise BadRequestException(
                f"Le bail ne couvre pas la période {month:02d}/{year}."
            )

        # Vérifier unicité sur la clé de période (premier mois couvert)
        existing = (
            await db.execute(
                select(Payment).where(
                    Payment.lease_id == lease.id,
                    Payment.period_year == bp.key_year,
                    Payment.period_month == bp.key_month,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictException(
                f"Un loyer existe déjà pour ce bail ({bp.key_year}-{bp.key_month:02d})"
            )

        year, month = bp.key_year, bp.key_month
        amount_rent = round(float(lease.rent_amount) * bp.factor_sum, 2)
        amount_charges = round(float(lease.charges_amount) * bp.factor_sum, 2)
        amount_apl = (
            round(float(lease.apl_amount) * bp.covered_count, 2)
            if lease.apl_tiers_payant and lease.apl_amount else None
        )
        # amount_due = montant brut total (loyer + charges), avant déduction APL
        amount_due = amount_rent + amount_charges

        due_date = PaymentService._compute_due_date(year, month, lease.payment_day)

        # Si tiers-payant CAF : la CAF verse sa part dès la génération de l'avis
        if amount_apl and amount_apl > 0:
            initial_paid = min(amount_apl, amount_due)
            initial_status = PaymentStatus.PAID if initial_paid >= amount_due else PaymentStatus.PARTIAL
            initial_payment_date = due_date
            initial_method = "virement"
            initial_notes = "Aide personnelle au logement – tiers-payant CAF – versement automatique"
        else:
            initial_paid = 0.0
            initial_status = PaymentStatus.PENDING
            initial_payment_date = None
            initial_method = None
            initial_notes = None

        payment = Payment(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=year,
            period_month=month,
            period_start=bp.period_start,
            period_end=bp.period_end,
            due_date=due_date,
            amount_rent=amount_rent,
            amount_charges=amount_charges,
            amount_apl=amount_apl,
            amount_due=amount_due,
            amount_paid=initial_paid,
            status=initial_status,
            payment_date=initial_payment_date,
            payment_method=initial_method,
            notes=initial_notes,
            created_by=created_by,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def generate_monthly(
        db: AsyncSession,
        year: int,
        month: int,
        created_by: Optional[uuid.UUID] = None,
        property_ids: list | None = None,
    ) -> int:
        """Génère les loyers pour tous les baux actifs d'une période. Retourne le nombre créé.

        Ne génère que pour les baux dont (year, month) est le mois de déclenchement de
        leur période (fréquence + règle d'appel) → un seul loyer par période de N mois.
        """
        from app.services.billing_period import is_trigger_month

        q = select(Lease).where(
            Lease.is_active == True,
            or_(Lease.end_date == None, Lease.end_date >= date(year, month, 1)),
        )
        if property_ids is not None:
            q = q.where(Lease.property_id.in_(property_ids))
        leases = (await db.execute(q)).scalars().all()

        created = 0
        for lease in leases:
            if not is_trigger_month(lease, year, month):
                continue
            try:
                await PaymentService.generate_for_lease(db, lease, year, month, created_by)
                created += 1
            except ConflictException:
                pass  # déjà existant, on skip
            except BadRequestException:
                pass  # le bail ne couvre pas ce mois
        return created

    @staticmethod
    async def record_payment(
        db: AsyncSession, payment_id: uuid.UUID, data: PaymentRecordIn
    ) -> Payment:
        payment = await PaymentService.get_by_id(db, payment_id)
        if payment.status == PaymentStatus.CANCELLED:
            raise BadRequestException("Ce loyer est annulé")
        if payment.status == PaymentStatus.PAID:
            raise BadRequestException("Ce loyer est déjà intégralement payé")

        new_total = float(payment.amount_paid) + data.amount_paid
        amount_due = float(payment.amount_due)

        payment.amount_paid = min(new_total, amount_due)
        payment.payment_date = data.payment_date
        if data.payment_method:
            payment.payment_method = data.payment_method
        if data.notes:
            payment.notes = data.notes

        if payment.amount_paid >= amount_due:
            payment.status = PaymentStatus.PAID
            # Quittance auto-générée dès que le loyer est intégralement payé
            if not payment.quittance_generated_at:
                payment.quittance_generated_at = datetime.now(timezone.utc)
        else:
            payment.status = PaymentStatus.PARTIAL

        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def update_late_statuses(db: AsyncSession) -> int:
        """Passe les paiements en retard (appelé par le scheduler)."""
        today = date.today()
        result = await db.execute(
            select(Payment).where(
                Payment.status.in_([PaymentStatus.PENDING]),
                Payment.due_date < today,
            )
        )
        payments = result.scalars().all()
        for p in payments:
            p.status = PaymentStatus.LATE
        await db.flush()
        return len(payments)

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        payment_id: uuid.UUID,
        load_relations: bool = False,
    ) -> Payment:
        if load_relations:
            result = await db.execute(
                select(Payment)
                .options(
                    selectinload(Payment.tenant),
                    selectinload(Payment.lease).selectinload(Lease.parent_property),
                )
                .where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
        else:
            payment = await db.get(Payment, payment_id)
        if not payment:
            raise NotFoundException("Loyer introuvable")
        return payment

    @staticmethod
    async def list_all(
        db: AsyncSession,
        *,
        search: Optional[str] = None,
        lease_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        status: Optional[PaymentStatus] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Payment], int]:
        base_q = (
            select(Payment)
            .join(Tenant, Payment.tenant_id == Tenant.id)
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Property, Lease.property_id == Property.id)
            .options(
                selectinload(Payment.tenant),
                selectinload(Payment.lease).selectinload(Lease.parent_property),
            )
        )

        filters = []
        if lease_id:
            filters.append(Payment.lease_id == lease_id)
        if tenant_id:
            filters.append(Payment.tenant_id == tenant_id)
        if status:
            filters.append(Payment.status == status)
        if year:
            filters.append(Payment.period_year == year)
        if month:
            filters.append(Payment.period_month == month)
        if search:
            s = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(Tenant.first_name).like(s),
                    func.lower(Tenant.last_name).like(s),
                    func.lower(Property.name).like(s),
                )
            )

        if filters:
            base_q = base_q.where(and_(*filters))

        total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
        items = (
            await db.execute(
                base_q.order_by(Payment.period_year.desc(), Payment.period_month.desc()).offset(skip).limit(limit)
            )
        ).scalars().all()

        return list(items), total

    @staticmethod
    def to_list_item(p: Payment) -> PaymentListItem:
        property_name = ""
        if p.lease and p.lease.parent_property:
            property_name = p.lease.parent_property.name

        return PaymentListItem(
            id=p.id,
            tenant_full_name=p.tenant.full_name if p.tenant else str(p.tenant_id),
            property_name=property_name,
            period_label=p.period_label,
            period_start=p.period_start,
            period_end=p.period_end,
            period_range_label=p.period_range_label,
            period_year=p.period_year,
            period_month=p.period_month,
            due_date=p.due_date,
            amount_rent=float(p.amount_rent),
            amount_charges=float(p.amount_charges),
            amount_apl=float(p.amount_apl) if p.amount_apl is not None else None,
            amount_due=float(p.amount_due),
            amount_paid=float(p.amount_paid),
            balance=p.balance,
            status=p.status,
            quittance_generated_at=p.quittance_generated_at,
            quittance_sent_at=p.quittance_sent_at,
        )

    @staticmethod
    async def get_monthly_stats(
        db: AsyncSession, year: int, month: int
    ) -> MonthlyStats:
        months_fr = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ]
        result = await db.execute(
            select(
                func.count(Payment.id).label("total_count"),
                func.coalesce(func.sum(Payment.amount_due), 0).label("total_due"),
                func.coalesce(func.sum(Payment.amount_paid), 0).label("total_paid"),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.PAID).label("paid_count"),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.PENDING).label("pending_count"),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.PARTIAL).label("partial_count"),
                func.count(Payment.id).filter(Payment.status == PaymentStatus.LATE).label("late_count"),
            ).where(
                Payment.period_year == year,
                Payment.period_month == month,
            )
        )
        row = result.one()
        total_due = float(row.total_due)
        total_paid = float(row.total_paid)

        return MonthlyStats(
            period_label=f"{months_fr[month]} {year}",
            total_due=total_due,
            total_paid=total_paid,
            total_balance=total_due - total_paid,
            paid_count=row.paid_count or 0,
            pending_count=row.pending_count or 0,
            partial_count=row.partial_count or 0,
            late_count=row.late_count or 0,
        )

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
        today = date.today()
        year, month = today.year, today.month

        monthly = await PaymentService.get_monthly_stats(db, year, month)

        active_leases = (
            await db.execute(select(func.count(Lease.id)).where(Lease.is_active == True))
        ).scalar_one()

        occupied_units = (
            await db.execute(select(func.count(Property.id)).where(Property.is_occupied == True))
        ).scalar_one()

        total_units = (await db.execute(select(func.count(Property.id)))).scalar_one()

        total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar_one()

        occupancy_rate = (occupied_units / total_units) if total_units > 0 else 0.0

        return DashboardStats(
            monthly=monthly,
            active_leases=active_leases,
            occupied_units=occupied_units,
            total_units=total_units,
            occupancy_rate=round(occupancy_rate, 4),
            total_tenants=total_tenants,
        )

    @staticmethod
    async def send_quittance(db: AsyncSession, payment_id: uuid.UUID) -> Payment:
        """Marque la quittance comme envoyée et enregistre l'horodatage."""
        payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
        if payment.status not in (PaymentStatus.PAID, PaymentStatus.PARTIAL):
            raise BadRequestException("Impossible de générer une quittance pour un loyer non payé")
        now = datetime.now(timezone.utc)
        if not payment.quittance_generated_at:
            payment.quittance_generated_at = now
        payment.quittance_sent_at = now
        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def cancel_payment(db: AsyncSession, payment_id: uuid.UUID) -> Payment:
        payment = await PaymentService.get_by_id(db, payment_id)
        if payment.status == PaymentStatus.PAID:
            raise BadRequestException("Impossible d'annuler un loyer déjà payé")
        payment.status = PaymentStatus.CANCELLED
        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def delete_payment(db: AsyncSession, payment_id: uuid.UUID) -> None:
        payment = await PaymentService.get_by_id(db, payment_id)
        await db.delete(payment)
        await db.flush()
