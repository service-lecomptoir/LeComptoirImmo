"""Régularisation annuelle des charges (Actualisation — Étape 3).

Compare les provisions de charges versées par le locataire sur une période aux
charges réelles saisies par le gestionnaire, puis :
  • réajuste la provision mensuelle du bail (calcul annuel → application mensuelle) ;
  • dégage un solde ponctuel : trop-perçu (remboursement, crédité au locataire et
    déduit du prochain loyer) ou complément dû par le locataire.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.charge_regularization import ChargeRegularization

_MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def months_between(start: date, end: date) -> int:
    """Nombre de mois inclusifs entre deux dates (>=1)."""
    if end < start:
        return 1
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _fr(d: date) -> str:
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"


class ChargeRegularizationService:

    @staticmethod
    async def provisions_paid(
        db: AsyncSession, lease_id: uuid.UUID, period_start: date, period_end: date
    ) -> float:
        """Total des provisions de charges appelées sur la période (somme des
        amount_charges des loyers dont le mois tombe dans la fenêtre)."""
        rows = (await db.execute(
            select(Payment.period_year, Payment.period_month, Payment.amount_charges)
            .where(Payment.lease_id == lease_id, Payment.status != PaymentStatus.CANCELLED)
        )).all()
        total = 0.0
        for year, month, charges in rows:
            try:
                m = date(year, month, 1)
            except (ValueError, TypeError):
                continue
            if period_start <= m <= period_end:
                total += float(charges or 0)
        return round(total, 2)

    @classmethod
    async def compute(
        cls, db: AsyncSession, lease: Lease, period_start: date, period_end: date,
        real_total: float,
    ) -> dict:
        """Prévisualise une régularisation (sans rien persister)."""
        months = months_between(period_start, period_end)
        provisions = await cls.provisions_paid(db, lease.id, period_start, period_end)
        # Repli si aucun loyer enregistré sur la période : provision théorique du bail.
        if provisions == 0:
            provisions = round(float(lease.charges_amount) * months, 2)
        real = round(float(real_total), 2)
        balance = round(provisions - real, 2)
        suggested = round(real / months, 2) if months else real
        return {
            "months_count": months,
            "provisions_total": provisions,
            "real_total": real,
            "balance": balance,  # >0 trop-perçu (remboursement) ; <0 complément dû
            "old_monthly_provision": round(float(lease.charges_amount), 2),
            "suggested_monthly_provision": suggested,
        }

    @classmethod
    async def apply(
        cls, db: AsyncSession, lease: Lease, period_start: date, period_end: date,
        real_total: float, new_monthly_provision: float,
        created_by: Optional[uuid.UUID] = None, notes: Optional[str] = None,
        effective_date: Optional[date] = None,
    ) -> ChargeRegularization:
        """Applique la régularisation : enregistre, réajuste la provision mensuelle
        du bail, notifie le locataire (+ e-mail no-op tant que SMTP off)."""
        c = await cls.compute(db, lease, period_start, period_end, real_total)
        old_monthly = c["old_monthly_provision"]
        new_monthly = round(float(new_monthly_provision), 2)

        reg = ChargeRegularization(
            lease_id=lease.id,
            tenant_id=lease.tenant_id,
            period_start=period_start,
            period_end=period_end,
            months_count=c["months_count"],
            provisions_total=c["provisions_total"],
            real_total=c["real_total"],
            balance=c["balance"],
            old_monthly_provision=old_monthly,
            new_monthly_provision=new_monthly,
            status="applied",
            applied_at=datetime.utcnow(),
            notes=notes,
            created_by=created_by,
        )
        db.add(reg)

        # Réajustement de la provision mensuelle via une révision datée : le mois
        # courant reste figé, l'ancienne provision est conservée en historique.
        from app.services.rent_revision_service import RentRevisionService, first_of_next_month
        rev = await RentRevisionService.schedule(
            db, lease, kind="charges", new_amount=new_monthly,
            effective_date=effective_date or first_of_next_month(date.today()),
            source="charges", reason="Régularisation des charges", created_by=created_by,
        )
        reg.rent_revision_id = rev.id
        await db.flush()

        await cls._notify(db, lease, reg)
        await db.commit()
        await db.refresh(reg)
        return reg

    @classmethod
    async def update(
        cls, db: AsyncSession, reg: ChargeRegularization, lease: Lease,
        period_start: date, period_end: date, real_total: float,
        new_monthly_provision: float, notes: Optional[str] = None,
    ) -> ChargeRegularization:
        """Modifie une régularisation existante : recalcule le solde et réapplique
        la provision mensuelle. `old_monthly_provision` reste la valeur d'origine
        (pré-régularisation) pour permettre une annulation correcte."""
        c = await cls.compute(db, lease, period_start, period_end, real_total)
        new_monthly = round(float(new_monthly_provision), 2)
        reg.period_start = period_start
        reg.period_end = period_end
        reg.months_count = c["months_count"]
        reg.provisions_total = c["provisions_total"]
        reg.real_total = c["real_total"]
        reg.balance = c["balance"]
        reg.new_monthly_provision = new_monthly
        if notes is not None:
            reg.notes = notes
        # Met à jour la révision de charges liée (au lieu d'écraser le bail).
        from app.services.rent_revision_service import RentRevisionService, first_of_next_month
        from app.models.rent_revision import RentRevision
        rev = await db.get(RentRevision, reg.rent_revision_id) if reg.rent_revision_id else None
        if rev:
            rev.charges_amount = new_monthly
        else:
            rev = await RentRevisionService.schedule(
                db, lease, kind="charges", new_amount=new_monthly,
                effective_date=first_of_next_month(date.today()),
                source="charges", reason="Régularisation des charges (modifiée)",
            )
            reg.rent_revision_id = rev.id
        await db.flush()
        await RentRevisionService.sync_lease_current(db, lease)
        await cls._notify(db, lease, reg)
        await db.commit()
        await db.refresh(reg)
        return reg

    @staticmethod
    async def delete(db: AsyncSession, reg: ChargeRegularization, lease: Lease) -> None:
        """Supprime une régularisation : retire la révision de charges qu'elle avait
        générée, puis restaure la provision mensuelle en vigueur (révision restante
        applicable, ou la provision antérieure à la régularisation)."""
        from app.services.rent_revision_service import RentRevisionService
        from app.models.rent_revision import RentRevision

        if reg.rent_revision_id:
            rev = await db.get(RentRevision, reg.rent_revision_id)
            if rev:
                await db.delete(rev)
                await db.flush()

        # Provision en vigueur après retrait : dernière révision de charges restante
        # applicable, sinon la provision antérieure à la régularisation.
        remaining = await RentRevisionService.list_for_lease(db, lease.id)
        lease.charges_amount = round(RentRevisionService._effective_field(
            float(reg.old_monthly_provision), remaining, "charges", date.today()), 2)

        await db.delete(reg)
        await db.flush()
        await db.commit()

    @staticmethod
    async def _notify(db: AsyncSession, lease: Lease, reg: ChargeRegularization) -> None:
        """Notification interne + e-mail (best-effort)."""
        try:
            from app.models.tenant import Tenant
            tenant = await db.get(Tenant, lease.tenant_id)
            bal = float(reg.balance)
            period = f"du {_fr(reg.period_start)} au {_fr(reg.period_end)}"
            if bal > 0:
                solde = (f"Un trop-perçu de {bal:.2f} € vous est restitué "
                         f"(déduit de vos prochains loyers).")
            elif bal < 0:
                solde = f"Un complément de {abs(bal):.2f} € reste à régler."
            else:
                solde = "Les provisions correspondent exactement aux charges réelles."
            message = (
                f"Régularisation des charges {period} : provisions versées "
                f"{float(reg.provisions_total):.2f} € pour {float(reg.real_total):.2f} € "
                f"de charges réelles. {solde} Votre nouvelle provision mensuelle de "
                f"charges est de {float(reg.new_monthly_provision):.2f} €."
            )

            if tenant and getattr(tenant, "user_id", None):
                from app.models.notification import (
                    Notification, NotificationType, NotificationPriority,
                )
                db.add(Notification(
                    title="Régularisation des charges",
                    message=message,
                    notification_type=NotificationType.SYSTEME,
                    priority=NotificationPriority.NORMAL,
                    entity_type="lease",
                    entity_id=lease.id,
                    user_id=tenant.user_id,
                ))
                await db.flush()

            email = getattr(tenant, "email", None) if tenant else None
            if email:
                from app.services.email_service import send_charge_regularization
                await send_charge_regularization(
                    to=email,
                    tenant_name=tenant.full_name if tenant else "",
                    period=period,
                    provisions_total=float(reg.provisions_total),
                    real_total=float(reg.real_total),
                    balance=bal,
                    new_monthly_provision=float(reg.new_monthly_provision),
                )
        except Exception:  # pragma: no cover - best effort
            pass
