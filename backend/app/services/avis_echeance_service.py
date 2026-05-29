"""
Service AvisEcheance — Génération des avis d'échéances (manuelle et automatique).
"""
import uuid
import calendar
import logging
from datetime import date, timedelta, datetime
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
        """Période couverte + facteur de prorata pour UN mois (délègue au module
        partagé `billing_period`). Conservé pour compat (tests + APL)."""
        from app.services.billing_period import month_period_and_factor
        return month_period_and_factor(
            lease.start_date,
            getattr(lease, "end_date", None),
            getattr(lease, "rent_call_rule", None) or "calendrier",
            year,
            month,
        )

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

        apl_override : montant APL spécifique à cette période ; None = utiliser le bail.

        La période couvre N mois selon `lease.payment_frequency` (1 = mensuel). Elle
        est calculée par `billing_period.compute_period` ; (year, month) peut être
        n'importe quel mois de la période, la clé d'unicité retenue est le premier
        mois réellement couvert.
        """
        from app.services.billing_period import compute_period

        bp = compute_period(lease, year, month)
        if bp is None:
            raise BadRequestException(
                f"Le bail ne couvre pas la période {month:02d}/{year}."
            )

        # Vérifier unicité sur la clé de période (premier mois couvert)
        existing = (await db.execute(
            select(AvisEcheance).where(
                AvisEcheance.lease_id == lease.id,
                AvisEcheance.period_year == bp.key_year,
                AvisEcheance.period_month == bp.key_month,
            )
        )).scalar_one_or_none()

        if existing:
            raise ConflictException(
                f"Avis d'échéance déjà existant pour la période "
                f"{bp.key_month:02d}/{bp.key_year} (bail {lease.id})"
            )

        # Loyer et charges = somme des mois couverts (prorata d'entrée/sortie inclus)
        amount_rent = round(float(lease.rent_amount) * bp.factor_sum, 2)
        amount_charges = round(float(lease.charges_amount) * bp.factor_sum, 2)

        # APL : override = total pour la période ; sinon montant mensuel × mois couverts
        if apl_override is not None:
            apl = float(apl_override) if apl_override > 0 else None
        elif lease.apl_tiers_payant and lease.apl_amount:
            apl = round(float(lease.apl_amount) * bp.covered_count, 2)
        else:
            apl = None

        total = cls._compute_total(amount_rent, amount_charges, apl)
        due = cls._due_date(bp.key_year, bp.key_month, lease.payment_day)

        avis = AvisEcheance(
            id=uuid.uuid4(),
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_year=bp.key_year,
            period_month=bp.key_month,
            period_start=bp.period_start,
            period_end=bp.period_end,
            due_date=due,
            amount_rent=amount_rent,
            amount_charges=amount_charges,
            amount_apl=apl,
            amount_total=total,
            # L'avis est immédiatement visible dans l'espace locataire → « Envoyé ».
            status=AvisEcheanceStatus.ENVOYE,
            sent_at=datetime.utcnow(),
            generated_by=generated_by,
        )
        db.add(avis)
        await db.flush()

        # ── Paiement de la période (systématique, montants agrégés/proratisés) ──
        await cls._ensure_payment(
            db, lease, bp.key_year, bp.key_month, apl, due,
            amount_rent, amount_charges,
            period_start=bp.period_start, period_end=bp.period_end,
        )

        # Si le loyer est déjà soldé dès la génération (APL/avance couvrant tout),
        # l'avis passe directement « Acquitté ».
        pay = (await db.execute(
            select(Payment).where(
                Payment.lease_id == lease.id,
                Payment.period_year == bp.key_year,
                Payment.period_month == bp.key_month,
            )
        )).scalar_one_or_none()
        if pay and pay.status == PaymentStatus.PAID:
            avis.status = AvisEcheanceStatus.ACQUITTE
            await db.flush()

        # Prévenir le locataire 1 mois avant une révision IRL (notification + e-mail).
        await cls._notify_upcoming_revision(db, lease, bp.key_year, bp.key_month)

        return avis

    @classmethod
    async def _notify_upcoming_revision(
        cls, db: AsyncSession, lease: Lease, year: int, month: int
    ) -> None:
        """Si une révision IRL prend effet le mois suivant cette période, crée une
        notification pour le locataire et envoie un e-mail (no-op tant que SMTP off).
        Best-effort : n'interrompt jamais la génération de l'avis."""
        try:
            from app.services.irl_notice import upcoming_revision_notice, notice_text
            notice = await upcoming_revision_notice(db, lease, year, month)
            if not notice:
                return
            text = notice_text(notice)

            tenant = await db.get(Tenant, lease.tenant_id)
            if tenant and getattr(tenant, "user_id", None):
                from app.models.notification import (
                    Notification, NotificationType, NotificationPriority,
                )
                db.add(Notification(
                    title="Révision de loyer à venir",
                    message=text,
                    notification_type=NotificationType.SYSTEME,
                    priority=NotificationPriority.NORMAL,
                    entity_type="lease",
                    entity_id=lease.id,
                    user_id=tenant.user_id,
                ))
                await db.flush()

            # E-mail (no-op si SMTP désactivé).
            email = getattr(tenant, "email", None) if tenant else None
            if email:
                from app.services.email_service import send_revision_loyer
                await send_revision_loyer(
                    to=email,
                    tenant_name=tenant.full_name if tenant else "",
                    effective_date=notice["effective_date"],
                    old_rent=notice["old_rent"],
                    new_rent=notice.get("new_rent"),
                    irl_quarter=notice.get("irl_quarter"),
                    irl_year=notice.get("irl_year"),
                )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Notification révision loyer ignorée (bail %s): %s", lease.id, exc)

    @classmethod
    async def sync_statuses(cls, db: AsyncSession) -> int:
        """Backfill : aligne le statut des avis « brouillon » existants sur la réalité —
        Envoyé (ils sont visibles côté locataire) ou Acquitté si le loyer lié est payé.
        Ne touche que les avis encore en BROUILLON. Idempotent."""
        avis_list = (await db.execute(
            select(AvisEcheance).where(AvisEcheance.status == AvisEcheanceStatus.BROUILLON)
        )).scalars().all()
        n = 0
        for a in avis_list:
            pay = (await db.execute(
                select(Payment).where(
                    Payment.lease_id == a.lease_id,
                    Payment.period_year == a.period_year,
                    Payment.period_month == a.period_month,
                )
            )).scalar_one_or_none()
            if pay and pay.status == PaymentStatus.PAID:
                a.status = AvisEcheanceStatus.ACQUITTE
            else:
                a.status = AvisEcheanceStatus.ENVOYE
                if a.sent_at is None:
                    a.sent_at = datetime.utcnow()
            n += 1
        if n:
            await db.flush()
        return n

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
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> None:
        """Crée ou met à jour le paiement de la période (montants déjà proratisés).

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
                period_start=period_start,
                period_end=period_end,
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
        """Génère les avis pour tous les baux actifs (appelé par le scheduler).

        Ne génère que pour les baux dont (year, month) est le mois de DÉCLENCHEMENT
        de leur période (selon fréquence + règle d'appel) → un seul avis par période.
        """
        from app.services.billing_period import is_trigger_month

        q = select(Lease).where(Lease.is_active == True)
        if property_ids is not None:
            q = q.where(Lease.property_id.in_(property_ids))
        leases = (await db.execute(q)).scalars().all()

        count = 0
        for lease in leases:
            if not is_trigger_month(lease, year, month):
                continue  # Mois au milieu d'une période / hors couverture du bail
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
