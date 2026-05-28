"""
Service AvisEcheance — Génération des avis d'échéances (manuelle et automatique).
"""
import uuid
import calendar
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.payment import Payment, PaymentStatus
from app.core.exceptions import ConflictException, NotFoundException, BadRequestException

logger = logging.getLogger(__name__)


class AvisEcheanceService:

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _due_date(year: int, month: int, payment_day: int) -> date:
        max_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(payment_day, max_day))

    @staticmethod
    def _first_of_next_month(year: int, month: int) -> date:
        return date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    @classmethod
    def _period_and_factor(cls, lease, year: int, month: int):
        """Calcule la période réellement couverte et le facteur de prorata pour
        (bail, année, mois), selon la règle d'appel de loyer.

        - calendrier   : période = mois civil borné aux dates du bail ; prorata au
                         nombre de jours pour les mois d'entrée/sortie partiels.
        - contractuelle: période = du jour d'entrée (date à date) ; loyer plein.

        Retourne (period_start, period_end, factor). (None, None, 0.0) si le bail ne
        couvre pas ce mois."""
        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)
        lease_start: date = lease.start_date
        lease_end: Optional[date] = lease.end_date
        rule = (getattr(lease, "rent_call_rule", None) or "calendrier")

        if rule == "contractuelle":
            anniv = lease_start.day
            p_start = date(year, month, min(anniv, days_in_month))
            nxt = cls._first_of_next_month(year, month)
            nxt_days = calendar.monthrange(nxt.year, nxt.month)[1]
            p_end = date(nxt.year, nxt.month, min(anniv, nxt_days)) - timedelta(days=1)
            p_start = max(p_start, lease_start)
            if lease_end:
                p_end = min(p_end, lease_end)
            if p_start > p_end:
                return None, None, 0.0
            # Période contractuelle = loyer plein, pas de prorata.
            return p_start, p_end, 1.0

        # calendrier
        p_start = max(month_start, lease_start)
        p_end = min(month_end, lease_end) if lease_end else month_end
        if p_start > p_end:
            return None, None, 0.0
        covered = (p_end - p_start).days + 1
        factor = 1.0 if covered >= days_in_month else round(covered / days_in_month, 6)
        return p_start, p_end, factor

    @staticmethod
    def _compute_total(rent: float, charges: float, apl: Optional[float]) -> float:
        total = float(rent) + float(charges)
        if apl:
            total = max(0.0, total - float(apl))
        return round(total, 2)

    # ── Génération ────────────────────────────────────────────────────────────

    @classmethod
    async def generate_for_lease(
        cls,
        db: AsyncSession,
        lease: Lease,
        year: int,
        month: int,
        generated_by: Optional[uuid.UUID] = None,
        apl_override: Optional[float] = None,
    ) -> AvisEcheance:
        """Génère un avis d'échéance pour un bail et une période donnés.

        apl_override : montant APL spécifique à ce mois ; None = utiliser celui du bail.
        """
        # Vérifier unicité
        existing = (await db.execute(
            select(AvisEcheance).where(
                AvisEcheance.lease_id == lease.id,
                AvisEcheance.period_year == year,
                AvisEcheance.period_month == month,
            )
        )).scalar_one_or_none()

        if existing:
            raise ConflictException(
                f"Avis d'échéance déjà existant pour la période "
                f"{month:02d}/{year} (bail {lease.id})"
            )

        # ── Période couverte + prorata selon la règle d'appel de loyer ───────
        period_start, period_end, factor = cls._period_and_factor(lease, year, month)
        if period_start is None:
            raise BadRequestException(
                f"Le bail ne couvre pas la période {month:02d}/{year}."
            )

        # APL : override mensuel prioritaire sur la valeur du bail
        if apl_override is not None:
            apl = float(apl_override) if apl_override > 0 else None
        elif lease.apl_tiers_payant and lease.apl_amount:
            apl = float(lease.apl_amount)
        else:
            apl = None

        # Loyer et charges proratisés (facteur = 1.0 pour un mois plein / contractuel)
        amount_rent = round(float(lease.rent_amount) * factor, 2)
        amount_charges = round(float(lease.charges_amount) * factor, 2)
        total = cls._compute_total(amount_rent, amount_charges, apl)
        due = cls._due_date(year, month, lease.payment_day)

        avis = AvisEcheance(
            id=uuid.uuid4(),
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=year,
            period_month=month,
            period_start=period_start,
            period_end=period_end,
            due_date=due,
            amount_rent=amount_rent,
            amount_charges=amount_charges,
            amount_apl=apl,
            amount_total=total,
            status=AvisEcheanceStatus.BROUILLON,
            generated_by=generated_by,
        )
        db.add(avis)
        await db.flush()

        # ── Créer le paiement du mois (systématique, montants proratisés) ────
        # APL tiers-payant : pré-créditer le montant CAF ; sinon PENDING à 0.
        await cls._ensure_payment(db, lease, year, month, apl, due, amount_rent, amount_charges)

        return avis

    @classmethod
    async def _ensure_payment(
        cls,
        db: AsyncSession,
        lease: Lease,
        year: int,
        month: int,
        apl: Optional[float],
        due_date: date,
        amount_rent: float,
        amount_charges: float,
    ) -> None:
        """Crée ou met à jour le paiement du mois (montants déjà proratisés).

        Sans APL : paiement PENDING, montant dû = loyer + charges, rien d'encaissé.
        Avec APL tiers-payant : APL pré-créditée, solde restant à la charge du locataire.
        """
        existing = (await db.execute(
            select(Payment).where(
                Payment.lease_id == lease.id,
                Payment.period_year == year,
                Payment.period_month == month,
            )
        )).scalar_one_or_none()

        amount_rent = float(amount_rent)
        amount_charges = float(amount_charges)
        amount_due = amount_rent + amount_charges

        if apl and apl > 0:
            initial_paid = min(apl, amount_due)
            status = PaymentStatus.PAID if initial_paid >= amount_due else PaymentStatus.PARTIAL
            notes = "Tiers-payant CAF – versement automatique"
        else:
            initial_paid = 0.0
            status = PaymentStatus.PENDING
            notes = None

        if existing is None:
            payment = Payment(
                lease_id=lease.id,
                tenant_id=lease.tenant_id,
                period_year=year,
                period_month=month,
                due_date=due_date,
                amount_rent=amount_rent,
                amount_charges=amount_charges,
                amount_apl=apl if apl and apl > 0 else None,
                amount_due=amount_due,
                amount_paid=initial_paid,
                payment_date=due_date if (apl and apl > 0) else None,
                payment_method="virement" if (apl and apl > 0) else None,
                status=status,
                notes=notes,
            )
            db.add(payment)
        elif apl and apl > 0:
            # Mettre à jour l'APL si pas encore crédité
            if (existing.amount_apl or 0) < apl:
                existing.amount_apl = apl
                existing.amount_paid = max(float(existing.amount_paid), initial_paid)
                existing.payment_date = existing.payment_date or due_date
                existing.payment_method = existing.payment_method or "virement"
                if existing.amount_paid >= float(existing.amount_due):
                    existing.status = PaymentStatus.PAID
                elif existing.amount_paid > 0:
                    existing.status = PaymentStatus.PARTIAL
                if not existing.notes:
                    existing.notes = notes

        await db.flush()

    @classmethod
    async def generate_monthly_all(
        cls,
        db: AsyncSession,
        year: int,
        month: int,
        property_ids: list | None = None,
    ) -> int:
        """Génère les avis pour tous les baux actifs (appelé par le scheduler)."""
        q = select(Lease).where(Lease.is_active == True)
        if property_ids is not None:
            q = q.where(Lease.property_id.in_(property_ids))
        leases = (await db.execute(q)).scalars().all()

        count = 0
        for lease in leases:
            try:
                await cls.generate_for_lease(db, lease, year, month, generated_by=None)
                count += 1
            except ConflictException:
                pass  # Déjà existant, on ignore
            except BadRequestException:
                pass  # Le bail ne couvre pas ce mois (pas encore commencé / déjà fini)
            except Exception as exc:
                logger.error(f"Erreur génération avis bail {lease.id}: {exc}")

        return count

    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_list(
        db: AsyncSession,
        lease_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AvisEcheance]:
        q = select(AvisEcheance).options(
            selectinload(AvisEcheance.tenant),
            selectinload(AvisEcheance.lease).selectinload(Lease.parent_property),
        )
        if lease_id:
            q = q.where(AvisEcheance.lease_id == lease_id)
        if tenant_id:
            q = q.where(AvisEcheance.tenant_id == tenant_id)
        if year:
            q = q.where(AvisEcheance.period_year == year)
        if month:
            q = q.where(AvisEcheance.period_month == month)
        if status:
            q = q.where(AvisEcheance.status == status)
        q = q.order_by(
            AvisEcheance.period_year.desc(),
            AvisEcheance.period_month.desc(),
        ).offset(skip).limit(limit)
        return (await db.execute(q)).scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, avis_id: uuid.UUID) -> AvisEcheance:
        avis = (await db.execute(
            select(AvisEcheance)
            .options(
                selectinload(AvisEcheance.tenant),
                selectinload(AvisEcheance.lease).selectinload(Lease.parent_property),
            )
            .where(AvisEcheance.id == avis_id)
        )).scalar_one_or_none()
        if not avis:
            raise NotFoundException("Avis d'échéance introuvable")
        return avis

    # ── Mise à jour statut ────────────────────────────────────────────────────

    @staticmethod
    async def mark_sent(db: AsyncSession, avis_id: uuid.UUID) -> AvisEcheance:
        from datetime import datetime
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        avis.status = AvisEcheanceStatus.ENVOYE
        avis.sent_at = datetime.utcnow()
        await db.flush()
        return avis

    @staticmethod
    async def mark_acquitte(db: AsyncSession, avis_id: uuid.UUID) -> AvisEcheance:
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        avis.status = AvisEcheanceStatus.ACQUITTE
        await db.flush()
        return avis

    @classmethod
    async def update_apl(
        cls,
        db: AsyncSession,
        avis_id: uuid.UUID,
        new_apl: Optional[float],
    ) -> "AvisEcheance":
        """Met à jour le montant APL d'un avis existant et recalcule le total.
        Met aussi à jour le paiement lié si présent.
        """
        avis = await cls.get_by_id(db, avis_id)

        old_apl = float(avis.amount_apl) if avis.amount_apl else None
        apl = float(new_apl) if new_apl and new_apl > 0 else None

        # Recalcule le total de l'avis
        avis.amount_apl = apl
        avis.amount_total = cls._compute_total(avis.amount_rent, avis.amount_charges, apl)
        await db.flush()

        # Synchronise le paiement lié (s'il existe)
        existing_payment = (await db.execute(
            select(Payment).where(
                Payment.lease_id == avis.lease_id,
                Payment.period_year == avis.period_year,
                Payment.period_month == avis.period_month,
            )
        )).scalar_one_or_none()

        if existing_payment is not None:
            amount_due = float(existing_payment.amount_due)  # brut inchangé
            if apl and apl > 0:
                new_paid = min(apl, amount_due)
                existing_payment.amount_apl = apl
                existing_payment.amount_paid = new_paid
                existing_payment.payment_date = existing_payment.payment_date or avis.due_date
                existing_payment.payment_method = existing_payment.payment_method or "virement"
                if new_paid >= amount_due:
                    existing_payment.status = PaymentStatus.PAID
                else:
                    existing_payment.status = PaymentStatus.PARTIAL
                if not existing_payment.notes or "CAF" not in existing_payment.notes:
                    existing_payment.notes = "Tiers-payant CAF – versement automatique"
            else:
                # APL supprimée : remettre à zéro la part CAF
                if existing_payment.notes and "CAF" in (existing_payment.notes or ""):
                    existing_payment.amount_apl = None
                    existing_payment.amount_paid = 0.0
                    existing_payment.payment_date = None
                    existing_payment.payment_method = None
                    existing_payment.status = PaymentStatus.PENDING
                    existing_payment.notes = None
            await db.flush()

        return avis

    @classmethod
    async def patch(
        cls,
        db: AsyncSession,
        avis_id: uuid.UUID,
        amount_rent: Optional[float] = None,
        amount_charges: Optional[float] = None,
        amount_apl: Optional[float] = None,
        due_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> "AvisEcheance":
        """Modifie un ou plusieurs champs d'un avis et recalcule le total."""
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        if amount_rent is not None:
            avis.amount_rent = amount_rent
        if amount_charges is not None:
            avis.amount_charges = amount_charges
        if amount_apl is not None:
            avis.amount_apl = amount_apl if amount_apl > 0 else None
        if due_date is not None:
            avis.due_date = due_date
        if notes is not None:
            avis.notes = notes
        # Recalcul du total
        avis.amount_total = cls._compute_total(
            float(avis.amount_rent),
            float(avis.amount_charges),
            float(avis.amount_apl) if avis.amount_apl else None,
        )
        await db.flush()
        return avis

    @staticmethod
    async def relancer(db: AsyncSession, avis_id: uuid.UUID) -> "AvisEcheance":
        """Remet un avis en statut brouillon pour permettre une nouvelle modification/envoi."""
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        avis.status = AvisEcheanceStatus.BROUILLON
        avis.sent_at = None
        await db.flush()
        return avis

    @staticmethod
    async def delete(db: AsyncSession, avis_id: uuid.UUID) -> None:
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        await db.delete(avis)
        await db.flush()
