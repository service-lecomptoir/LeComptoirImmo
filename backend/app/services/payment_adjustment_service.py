"""Service des ajustements ad hoc d'une échéance (suppléments / restitutions).

Permet d'ajouter à la volée, sur l'échéance d'un mois :
  • un montant à PAYER en plus du loyer + charges (« supplément ») ;
  • un montant à RESTITUER au locataire (« restitution », ex. caution).

Règle de calcul (validée) :
  net à payer du mois = loyer + charges + Σ suppléments − Σ restitutions, plancher 0.

Le surplus de restitution (la part qui ferait passer le net sous 0) est :
  • REPORTÉ EN CRÉDIT du bail (déduit de la prochaine échéance) si le bail est actif ;
  • traité comme un REMBOURSEMENT (montant à restituer) si le locataire a donné son
    congé (bail résilié) : il n'y a pas de mois suivant sur lequel reporter.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.avis_echeance import AvisEcheance
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.payment_adjustment import (
    ADJUSTMENT_RESTITUTION,
    ADJUSTMENT_SUPPLEMENT,
    PaymentAdjustment,
)

_VALID_TYPES = {ADJUSTMENT_SUPPLEMENT, ADJUSTMENT_RESTITUTION}


class PaymentAdjustmentService:
    # ── Lecture ────────────────────────────────────────────────────────────────
    @staticmethod
    async def list_for_payment(db: AsyncSession, payment_id: uuid.UUID) -> list[PaymentAdjustment]:
        return list(
            (
                await db.execute(
                    select(PaymentAdjustment)
                    .where(PaymentAdjustment.payment_id == payment_id)
                    .order_by(PaymentAdjustment.created_at)
                )
            )
            .scalars()
            .all()
        )

    @classmethod
    async def for_lease_period(
        cls, db: AsyncSession, lease_id: uuid.UUID, year: int, month: int
    ) -> tuple[Payment | None, list[PaymentAdjustment]]:
        """Échéance (lease, période) + ses lignes d'ajustement. Utilisé au rendu de
        l'avis (qui raisonne sur l'entité AvisEcheance, pas sur le paiement)."""
        pay = (
            await db.execute(
                select(Payment).where(
                    Payment.lease_id == lease_id,
                    Payment.period_year == year,
                    Payment.period_month == month,
                )
            )
        ).scalar_one_or_none()
        if pay is None:
            return None, []
        return pay, await cls.list_for_payment(db, pay.id)

    # ── Détection « départ annoncé » (congé / résiliation) ──────────────────────
    @staticmethod
    async def _lease_en_depart(db: AsyncSession, lease_id: uuid.UUID) -> bool:
        lease = await db.get(Lease, lease_id)
        if lease is None:
            return False
        return (not lease.is_active) or (getattr(lease, "notice_date", None) is not None)

    # ── Recalcul du net + crédit/remboursement + statut ─────────────────────────
    @classmethod
    async def recompute(cls, db: AsyncSession, payment: Payment) -> None:
        adjs = await cls.list_for_payment(db, payment.id)
        supp = sum(float(a.montant) for a in adjs if a.type == ADJUSTMENT_SUPPLEMENT)
        rest = sum(float(a.montant) for a in adjs if a.type == ADJUSTMENT_RESTITUTION)
        base = float(payment.amount_rent) + float(payment.amount_charges)
        net = base + supp - rest

        payment.amount_due = round(max(0.0, net), 2)
        surplus = round(max(0.0, -net), 2)

        if surplus > 0 and await cls._lease_en_depart(db, payment.lease_id):
            payment.restitution_refund = surplus
            payment.restitution_credit = 0
        elif surplus > 0:
            payment.restitution_credit = surplus
            payment.restitution_refund = 0
        else:
            payment.restitution_credit = 0
            payment.restitution_refund = 0

        cls._sync_status(payment)
        await db.flush()
        await cls._sync_avis(db, payment)

    @staticmethod
    def _sync_status(payment: Payment) -> None:
        """Réaligne le statut sur le net dû (ne touche ni aux mois annulés ni aux
        mois reportés sur un plan d'apurement)."""
        if payment.status == PaymentStatus.CANCELLED or getattr(payment, "settled_by_plan", False):
            return
        due = float(payment.amount_due)
        covered = float(payment.amount_paid) + float(getattr(payment, "amount_on_plan", 0) or 0)
        if due > 0 and covered >= due:
            payment.status = PaymentStatus.PAID
            payment.payment_date = payment.payment_date or payment.due_date
        elif covered > 0:
            payment.status = PaymentStatus.PARTIAL
        elif payment.due_date and payment.due_date < date.today():
            payment.status = PaymentStatus.LATE
        else:
            payment.status = PaymentStatus.PENDING

    @staticmethod
    async def _sync_avis(db: AsyncSession, payment: Payment) -> None:
        """Aligne le total de l'avis de loyer lié (même bail + période) sur le net."""
        avis = (
            await db.execute(
                select(AvisEcheance).where(
                    AvisEcheance.lease_id == payment.lease_id,
                    AvisEcheance.period_year == payment.period_year,
                    AvisEcheance.period_month == payment.period_month,
                    (AvisEcheance.kind == "loyer") | (AvisEcheance.kind.is_(None)),
                )
            )
        ).scalar_one_or_none()
        if avis is not None:
            apl = float(avis.amount_apl) if avis.amount_apl else 0.0
            avis.amount_total = round(max(0.0, float(payment.amount_due) - apl), 2)
            await db.flush()

    # ── Écriture ────────────────────────────────────────────────────────────────
    @classmethod
    async def add(
        cls,
        db: AsyncSession,
        payment: Payment,
        *,
        type_: str,
        libelle: str | None,
        montant: float,
        created_by: uuid.UUID | None = None,
    ) -> PaymentAdjustment:
        if type_ not in _VALID_TYPES:
            raise BadRequestException(
                "Type d'ajustement invalide (attendu : supplément ou restitution)."
            )
        if montant is None or float(montant) <= 0:
            raise BadRequestException("Le montant de la ligne doit être supérieur à 0.")
        if payment.status == PaymentStatus.CANCELLED:
            raise BadRequestException("Impossible d'ajouter une ligne sur une échéance annulée.")
        default_label = "Supplément" if type_ == ADJUSTMENT_SUPPLEMENT else "Restitution"
        adj = PaymentAdjustment(
            payment_id=payment.id,
            type=type_,
            libelle=(libelle or "").strip() or default_label,
            montant=round(float(montant), 2),
            created_by=created_by,
        )
        db.add(adj)
        await db.flush()
        await cls.recompute(db, payment)
        return adj

    @classmethod
    async def delete(cls, db: AsyncSession, payment: Payment, adjustment_id: uuid.UUID) -> None:
        adj = await db.get(PaymentAdjustment, adjustment_id)
        if adj is None or adj.payment_id != payment.id:
            raise NotFoundException("Ligne d'ajustement introuvable.")
        await db.delete(adj)
        await db.flush()
        await cls.recompute(db, payment)

    # ── Rendu (avis / quittance) ────────────────────────────────────────────────
    @staticmethod
    def line_items(
        adjustments: list[PaymentAdjustment],
        eur_fn,
        *,
        with_regle: bool = False,
    ) -> list[dict]:
        """Lignes prêtes à injecter dans le tableau détaillé (avis / quittance).

        `eur_fn(value) -> str` formate un montant. `with_regle` duplique le montant
        dans la colonne « réglés » (utile pour la quittance)."""
        items: list[dict] = []
        for a in adjustments:
            montant = eur_fn(a.montant)
            if a.type == ADJUSTMENT_SUPPLEMENT:
                row = {"label": (a.libelle or "Supplément").upper(), "appele": "+" + montant}
                if with_regle:
                    row["regle"] = "+" + montant
            else:
                row = {"label": (a.libelle or "Restitution").upper(), "appele": "-" + montant}
                if with_regle:
                    row["regle"] = "-" + montant
            items.append(row)
        return items

    @staticmethod
    def surplus_note(payment: Payment, eur_fn) -> dict | None:
        """Ligne informative décrivant le surplus de restitution (crédit ou
        remboursement), sans impacter les colonnes de montants."""
        credit = float(getattr(payment, "restitution_credit", 0) or 0)
        refund = float(getattr(payment, "restitution_refund", 0) or 0)
        if credit > 0:
            return {
                "label": f"Dont {eur_fn(credit)} reporté(s) en crédit sur la prochaine échéance",
                "appele": "",
                "regle": "",
            }
        if refund > 0:
            return {
                "label": f"Dont {eur_fn(refund)} à vous restituer (remboursement)",
                "appele": "",
                "regle": "",
            }
        return None
