"""Module Syndic — phase 2a : comptabilité copropriété (budget prévisionnel,
appels de fonds ventilés par tantièmes, encaissements, comptes copropriétaires)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.copropriete import CoproLot, CoproLotTantieme, CoproRepartitionKey
from app.models.copropriete_compta import (
    CoproBudget,
    CoproBudgetLine,
    CoproExpense,
    CoproFundCall,
    CoproFundCallItem,
    CoproPayment,
)
from app.models.owner import Owner
from app.schemas.copropriete_compta import (
    BudgetCreate,
    BudgetUpdate,
    CoproPaymentIn,
    ExpenseCreate,
    ExpenseUpdate,
)

NB_PERIODS = {"mensuel": 12, "trimestriel": 4, "semestriel": 2, "annuel": 1}
_MONTHS_FR = [
    "",
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]


def nb_periods(periodicity: str) -> int:
    return NB_PERIODS.get(periodicity, 1)


def period_label(periodicity: str, index: int, year: int) -> str:
    if periodicity == "mensuel":
        return f"{_MONTHS_FR[min(12, max(1, index))]} {year}"
    if periodicity == "trimestriel":
        return f"T{index} {year}"
    if periodicity == "semestriel":
        return f"{'1er' if index == 1 else '2e'} semestre {year}"
    return f"Année {year}"


class CoproComptaService:
    # ── Budget ─────────────────────────────────────────────────────────────────
    @staticmethod
    async def _serialize_budget(db: AsyncSession, budget: CoproBudget) -> dict:
        lines = (
            (
                await db.execute(
                    select(CoproBudgetLine).where(CoproBudgetLine.budget_id == budget.id)
                )
            )
            .scalars()
            .all()
        )
        key_names = dict(
            (
                await db.execute(
                    select(CoproRepartitionKey.id, CoproRepartitionKey.name).where(
                        CoproRepartitionKey.copropriete_id == budget.copropriete_id
                    )
                )
            ).all()
        )
        return {
            "id": budget.id,
            "copropriete_id": budget.copropriete_id,
            "year": budget.year,
            "periodicity": budget.periodicity,
            "label": budget.label,
            "total": round(sum(float(line.amount or 0) for line in lines), 2),
            "nb_periods": nb_periods(budget.periodicity),
            "lines": [
                {
                    "id": line.id,
                    "key_id": line.key_id,
                    "key_name": key_names.get(line.key_id),
                    "label": line.label,
                    "amount": float(line.amount or 0),
                }
                for line in lines
            ],
        }

    @staticmethod
    async def get_budget(db: AsyncSession, copro_id: uuid.UUID, year: int) -> dict | None:
        budget = (
            (
                await db.execute(
                    select(CoproBudget).where(
                        CoproBudget.copropriete_id == copro_id, CoproBudget.year == year
                    )
                )
            )
            .scalars()
            .first()
        )
        if not budget:
            return None
        return await CoproComptaService._serialize_budget(db, budget)

    @staticmethod
    async def create_budget(
        db: AsyncSession, copro_id: uuid.UUID, data: BudgetCreate, created_by: uuid.UUID
    ) -> dict:
        existing = (
            (
                await db.execute(
                    select(CoproBudget).where(
                        CoproBudget.copropriete_id == copro_id, CoproBudget.year == data.year
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing:
            raise BadRequestException(f"Un budget existe déjà pour {data.year}.")
        budget = CoproBudget(
            copropriete_id=copro_id,
            year=data.year,
            periodicity=data.periodicity,
            label=data.label,
            created_by=created_by,
        )
        db.add(budget)
        await db.flush()
        for line in data.lines:
            db.add(
                CoproBudgetLine(
                    budget_id=budget.id,
                    key_id=line.key_id,
                    label=line.label,
                    amount=line.amount,
                )
            )
        await db.flush()
        return await CoproComptaService._serialize_budget(db, budget)

    @staticmethod
    async def update_budget(
        db: AsyncSession, copro_id: uuid.UUID, budget_id: uuid.UUID, data: BudgetUpdate
    ) -> dict:
        budget = await db.get(CoproBudget, budget_id)
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Budget introuvable")
        if data.periodicity is not None:
            budget.periodicity = data.periodicity
        if data.label is not None:
            budget.label = data.label or None
        if data.lines is not None:
            # Remplacement intégral des postes.
            for old in (
                (
                    await db.execute(
                        select(CoproBudgetLine).where(CoproBudgetLine.budget_id == budget_id)
                    )
                )
                .scalars()
                .all()
            ):
                await db.delete(old)
            await db.flush()
            for line in data.lines:
                db.add(
                    CoproBudgetLine(
                        budget_id=budget_id,
                        key_id=line.key_id,
                        label=line.label,
                        amount=line.amount,
                    )
                )
        await db.flush()
        return await CoproComptaService._serialize_budget(db, budget)

    @staticmethod
    async def delete_budget(db: AsyncSession, copro_id: uuid.UUID, budget_id: uuid.UUID) -> None:
        budget = await db.get(CoproBudget, budget_id)
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Budget introuvable")
        await db.delete(budget)
        await db.flush()

    # ── Appels de fonds ─────────────────────────────────────────────────────────
    @staticmethod
    async def _budget_for(
        db: AsyncSession, copro_id: uuid.UUID, budget_id: uuid.UUID
    ) -> CoproBudget:
        budget = await db.get(CoproBudget, budget_id)
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Budget introuvable")
        return budget

    @staticmethod
    async def generate_call(
        db: AsyncSession,
        copro_id: uuid.UUID,
        budget_id: uuid.UUID,
        period_index: int,
        due_date: date | None,
        created_by: uuid.UUID,
    ) -> dict:
        budget = await CoproComptaService._budget_for(db, copro_id, budget_id)
        n = nb_periods(budget.periodicity)
        if not (1 <= period_index <= n):
            raise BadRequestException(
                f"Période invalide : {period_index} (1..{n} pour {budget.periodicity})."
            )
        # Anti-doublon.
        dup = (
            (
                await db.execute(
                    select(CoproFundCall).where(
                        CoproFundCall.budget_id == budget_id,
                        CoproFundCall.period_index == period_index,
                    )
                )
            )
            .scalars()
            .first()
        )
        if dup:
            raise BadRequestException("Un appel de fonds existe déjà pour cette période.")

        lines = (
            (
                await db.execute(
                    select(CoproBudgetLine).where(CoproBudgetLine.budget_id == budget_id)
                )
            )
            .scalars()
            .all()
        )
        keys = {
            k.id: k
            for k in (
                await db.execute(
                    select(CoproRepartitionKey).where(
                        CoproRepartitionKey.copropriete_id == copro_id
                    )
                )
            )
            .scalars()
            .all()
        }
        lots = (
            (
                await db.execute(
                    select(CoproLot)
                    .options(selectinload(CoproLot.tantiemes))
                    .where(CoproLot.copropriete_id == copro_id)
                )
            )
            .scalars()
            .all()
        )

        call = CoproFundCall(
            budget_id=budget_id,
            period_index=period_index,
            period_label=period_label(budget.periodicity, period_index, budget.year),
            due_date=due_date,
            created_by=created_by,
        )
        db.add(call)
        await db.flush()

        # Quote-part (non arrondie) de chaque lot pour la période.
        raw: list[tuple] = []  # (lot, montant brut)
        for lot in lots:
            tmap = {t.key_id: float(t.tantiemes or 0) for t in lot.tantiemes}
            annual = 0.0
            for line in lines:
                key = keys.get(line.key_id)
                base = float(key.total_tantiemes) if key else 0.0
                if base > 0:
                    annual += float(line.amount or 0) * tmap.get(line.key_id, 0.0) / base
            raw.append((lot, annual / n))

        rounded = [(lot, round(m, 2)) for lot, m in raw]
        # Compta immobilière : le total appelé doit égaler le montant budgété de la
        # période (Σ des quote-parts brutes), sans dérive de centimes due aux
        # arrondis. On affecte le résidu à la plus grosse quote-part.
        expected_total = round(sum(m for _l, m in raw), 2)
        residual = round(expected_total - sum(m for _l, m in rounded), 2)
        if residual != 0 and rounded:
            idx = max(range(len(rounded)), key=lambda i: rounded[i][1])
            rounded[idx] = (rounded[idx][0], round(rounded[idx][1] + residual, 2))

        for lot, amount in rounded:
            if amount <= 0:
                continue
            db.add(
                CoproFundCallItem(
                    call_id=call.id,
                    lot_id=lot.id,
                    owner_id=lot.owner_id,
                    amount_due=amount,
                    amount_paid=0,
                    status="pending",
                )
            )
        await db.flush()
        return await CoproComptaService.serialize_call(db, call)

    @staticmethod
    async def serialize_call(db: AsyncSession, call: CoproFundCall) -> dict:
        items = (
            (
                await db.execute(
                    select(CoproFundCallItem).where(CoproFundCallItem.call_id == call.id)
                )
            )
            .scalars()
            .all()
        )
        lot_nums = dict((await db.execute(select(CoproLot.id, CoproLot.numero))).all())
        # Noms copropriétaires (full_name) via fetch ciblé.
        owner_ids = [i.owner_id for i in items if i.owner_id]
        names: dict = {}
        if owner_ids:
            for o in (
                (await db.execute(select(Owner).where(Owner.id.in_(owner_ids)))).scalars().all()
            ):
                names[o.id] = o.full_name
        out_items = [
            {
                "id": i.id,
                "lot_id": i.lot_id,
                "lot_numero": lot_nums.get(i.lot_id),
                "owner_id": i.owner_id,
                "owner_name": names.get(i.owner_id),
                "amount_due": float(i.amount_due or 0),
                "amount_paid": float(i.amount_paid or 0),
                "status": i.status,
            }
            for i in items
        ]
        return {
            "id": call.id,
            "period_index": call.period_index,
            "period_label": call.period_label,
            "due_date": call.due_date,
            "total_due": round(sum(x["amount_due"] for x in out_items), 2),
            "total_paid": round(sum(x["amount_paid"] for x in out_items), 2),
            "items": out_items,
        }

    @staticmethod
    async def list_calls(db: AsyncSession, copro_id: uuid.UUID, budget_id: uuid.UUID) -> list[dict]:
        await CoproComptaService._budget_for(db, copro_id, budget_id)
        calls = (
            (
                await db.execute(
                    select(CoproFundCall)
                    .where(CoproFundCall.budget_id == budget_id)
                    .order_by(CoproFundCall.period_index)
                )
            )
            .scalars()
            .all()
        )
        return [await CoproComptaService.serialize_call(db, c) for c in calls]

    @staticmethod
    async def delete_call(db: AsyncSession, copro_id: uuid.UUID, call_id: uuid.UUID) -> None:
        call = await db.get(CoproFundCall, call_id)
        if not call:
            raise NotFoundException("Appel de fonds introuvable")
        budget = await db.get(CoproBudget, call.budget_id)
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Appel de fonds introuvable")
        await db.delete(call)
        await db.flush()

    # ── Encaissements ───────────────────────────────────────────────────────────
    @staticmethod
    async def record_payment(
        db: AsyncSession,
        copro_id: uuid.UUID,
        item_id: uuid.UUID,
        data: CoproPaymentIn,
        created_by: uuid.UUID,
    ) -> dict:
        item = await db.get(CoproFundCallItem, item_id)
        if not item:
            raise NotFoundException("Quote-part introuvable")
        call = await db.get(CoproFundCall, item.call_id)
        budget = await db.get(CoproBudget, call.budget_id) if call else None
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Quote-part introuvable")

        db.add(
            CoproPayment(
                item_id=item_id,
                amount=data.amount,
                payment_date=data.payment_date,
                method=(data.method or None),
                note=(data.note or None),
                created_by=created_by,
            )
        )
        item.amount_paid = round(float(item.amount_paid or 0) + float(data.amount), 2)
        due = float(item.amount_due or 0)
        if item.amount_paid >= due and due > 0:
            item.status = "paid"
        elif item.amount_paid > 0:
            item.status = "partial"
        else:
            item.status = "pending"
        await db.flush()
        return {
            "id": item.id,
            "amount_due": float(item.amount_due or 0),
            "amount_paid": float(item.amount_paid or 0),
            "status": item.status,
        }

    @staticmethod
    async def appel_pdf_context(db: AsyncSession, copro_id: uuid.UUID, item_id: uuid.UUID) -> dict:
        """Contexte du PDF d'appel de fonds pour une quote-part (copropriétaire) :
        détail par poste ventilé selon les tantièmes du lot, sur la période."""
        from app.models.copropriete import Copropriete

        item = await db.get(CoproFundCallItem, item_id)
        if not item:
            raise NotFoundException("Quote-part introuvable")
        call = await db.get(CoproFundCall, item.call_id)
        budget = await db.get(CoproBudget, call.budget_id) if call else None
        if not budget or budget.copropriete_id != copro_id:
            raise NotFoundException("Quote-part introuvable")
        copro = await db.get(Copropriete, copro_id)
        lot = await db.get(CoproLot, item.lot_id) if item.lot_id else None
        owner = await db.get(Owner, item.owner_id) if item.owner_id else None

        n = nb_periods(budget.periodicity)
        keys = {
            k.id: k
            for k in (
                await db.execute(
                    select(CoproRepartitionKey).where(
                        CoproRepartitionKey.copropriete_id == copro_id
                    )
                )
            )
            .scalars()
            .all()
        }
        lines = (
            (
                await db.execute(
                    select(CoproBudgetLine).where(CoproBudgetLine.budget_id == budget.id)
                )
            )
            .scalars()
            .all()
        )
        tmap = {}
        if lot:
            for t in (
                (
                    await db.execute(
                        select(CoproLotTantieme).where(CoproLotTantieme.lot_id == lot.id)
                    )
                )
                .scalars()
                .all()
            ):
                tmap[t.key_id] = float(t.tantiemes or 0)

        detail = []
        for line in lines:
            key = keys.get(line.key_id)
            base = float(key.total_tantiemes) if key else 0.0
            tant = tmap.get(line.key_id, 0.0)
            annual = float(line.amount or 0) * tant / base if base > 0 else 0.0
            period_amount = round(annual / n, 2)
            if period_amount <= 0:
                continue
            detail.append(
                {
                    "label": line.label,
                    "key_name": key.name if key else "",
                    "tantiemes": tant,
                    "base": int(base),
                    "amount": period_amount,
                }
            )
        return {
            "copro_name": copro.name if copro else "",
            "copro_address": (copro.full_address if copro else "") or "",
            "owner_name": owner.full_name if owner else "Copropriétaire",
            "lot_numero": lot.numero if lot else "",
            "period_label": call.period_label,
            "due_date": call.due_date,
            "detail": detail,
            "total": float(item.amount_due or 0),
        }

    # ── Comptes copropriétaires ───────────────────────────────────────────────────
    @staticmethod
    async def accounts(db: AsyncSession, copro_id: uuid.UUID, year: int) -> list[dict]:
        budget = (
            (
                await db.execute(
                    select(CoproBudget).where(
                        CoproBudget.copropriete_id == copro_id, CoproBudget.year == year
                    )
                )
            )
            .scalars()
            .first()
        )
        if not budget:
            return []
        rows = (
            (
                await db.execute(
                    select(CoproFundCallItem)
                    .join(CoproFundCall, CoproFundCallItem.call_id == CoproFundCall.id)
                    .where(CoproFundCall.budget_id == budget.id)
                )
            )
            .scalars()
            .all()
        )
        agg: dict = {}
        for it in rows:
            key = it.owner_id
            cur = agg.setdefault(key, {"due": 0.0, "paid": 0.0})
            cur["due"] += float(it.amount_due or 0)
            cur["paid"] += float(it.amount_paid or 0)
        # Noms.
        owner_ids = [k for k in agg if k]
        names: dict = {}
        if owner_ids:
            for o in (
                (await db.execute(select(Owner).where(Owner.id.in_(owner_ids)))).scalars().all()
            ):
                names[o.id] = o.full_name
        out = [
            {
                "owner_id": oid,
                "owner_name": names.get(oid) if oid else "Sans copropriétaire",
                "total_due": round(v["due"], 2),
                "total_paid": round(v["paid"], 2),
                "balance": round(v["due"] - v["paid"], 2),
            }
            for oid, v in agg.items()
        ]
        out.sort(key=lambda r: (r["owner_name"] or "").lower())
        return out

    # ── Dépenses réelles ──────────────────────────────────────────────────────
    @staticmethod
    async def _key_names(db: AsyncSession, copro_id: uuid.UUID) -> dict:
        return dict(
            (
                await db.execute(
                    select(CoproRepartitionKey.id, CoproRepartitionKey.name).where(
                        CoproRepartitionKey.copropriete_id == copro_id
                    )
                )
            ).all()
        )

    @staticmethod
    async def list_expenses(db: AsyncSession, copro_id: uuid.UUID, year: int) -> list[dict]:
        rows = (
            (
                await db.execute(
                    select(CoproExpense)
                    .where(CoproExpense.copropriete_id == copro_id, CoproExpense.year == year)
                    .order_by(CoproExpense.expense_date, CoproExpense.label)
                )
            )
            .scalars()
            .all()
        )
        names = await CoproComptaService._key_names(db, copro_id)
        return [
            {
                "id": e.id,
                "year": e.year,
                "key_id": e.key_id,
                "key_name": names.get(e.key_id),
                "label": e.label,
                "amount": float(e.amount or 0),
                "expense_date": e.expense_date,
                "supplier": e.supplier,
            }
            for e in rows
        ]

    @staticmethod
    async def create_expense(
        db: AsyncSession, copro_id: uuid.UUID, data: ExpenseCreate, created_by: uuid.UUID
    ) -> dict:
        exp = CoproExpense(
            copropriete_id=copro_id,
            year=data.year,
            key_id=data.key_id,
            label=data.label,
            amount=data.amount,
            expense_date=data.expense_date,
            supplier=(data.supplier or None),
            created_by=created_by,
        )
        db.add(exp)
        await db.flush()
        names = await CoproComptaService._key_names(db, copro_id)
        return {
            "id": exp.id,
            "year": exp.year,
            "key_id": exp.key_id,
            "key_name": names.get(exp.key_id),
            "label": exp.label,
            "amount": float(exp.amount or 0),
            "expense_date": exp.expense_date,
            "supplier": exp.supplier,
        }

    @staticmethod
    async def update_expense(
        db: AsyncSession, copro_id: uuid.UUID, expense_id: uuid.UUID, data: ExpenseUpdate
    ) -> dict:
        exp = await db.get(CoproExpense, expense_id)
        if not exp or exp.copropriete_id != copro_id:
            raise NotFoundException("Dépense introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(exp, field, value)
        await db.flush()
        names = await CoproComptaService._key_names(db, copro_id)
        return {
            "id": exp.id,
            "year": exp.year,
            "key_id": exp.key_id,
            "key_name": names.get(exp.key_id),
            "label": exp.label,
            "amount": float(exp.amount or 0),
            "expense_date": exp.expense_date,
            "supplier": exp.supplier,
        }

    @staticmethod
    async def delete_expense(db: AsyncSession, copro_id: uuid.UUID, expense_id: uuid.UUID) -> None:
        exp = await db.get(CoproExpense, expense_id)
        if not exp or exp.copropriete_id != copro_id:
            raise NotFoundException("Dépense introuvable")
        await db.delete(exp)
        await db.flush()

    # ── Régularisation annuelle ───────────────────────────────────────────────
    @staticmethod
    async def _appele_par_owner(db: AsyncSession, copro_id: uuid.UUID, year: int) -> dict:
        """Provisions appelées par copropriétaire sur l'année (somme des quote-parts)."""
        budget = (
            (
                await db.execute(
                    select(CoproBudget).where(
                        CoproBudget.copropriete_id == copro_id, CoproBudget.year == year
                    )
                )
            )
            .scalars()
            .first()
        )
        if not budget:
            return {}
        items = (
            (
                await db.execute(
                    select(CoproFundCallItem)
                    .join(CoproFundCall, CoproFundCallItem.call_id == CoproFundCall.id)
                    .where(CoproFundCall.budget_id == budget.id)
                )
            )
            .scalars()
            .all()
        )
        agg: dict = {}
        for it in items:
            agg[it.owner_id] = round(agg.get(it.owner_id, 0.0) + float(it.amount_due or 0), 2)
        return agg

    @staticmethod
    async def _reel_par_owner(db: AsyncSession, copro_id: uuid.UUID, year: int) -> dict:
        """Quote-part des dépenses réelles par copropriétaire (ventilée par tantièmes)."""
        keys = {
            k.id: float(k.total_tantiemes)
            for k in (
                await db.execute(
                    select(CoproRepartitionKey).where(
                        CoproRepartitionKey.copropriete_id == copro_id
                    )
                )
            )
            .scalars()
            .all()
        }
        expenses = (
            (
                await db.execute(
                    select(CoproExpense).where(
                        CoproExpense.copropriete_id == copro_id, CoproExpense.year == year
                    )
                )
            )
            .scalars()
            .all()
        )
        lots = (
            (
                await db.execute(
                    select(CoproLot)
                    .options(selectinload(CoproLot.tantiemes))
                    .where(CoproLot.copropriete_id == copro_id)
                )
            )
            .scalars()
            .all()
        )
        agg: dict = {}
        for lot in lots:
            tmap = {t.key_id: float(t.tantiemes or 0) for t in lot.tantiemes}
            quote = 0.0
            for e in expenses:
                base = keys.get(e.key_id, 0.0)
                if base > 0:
                    quote += float(e.amount or 0) * tmap.get(e.key_id, 0.0) / base
            if quote:
                agg[lot.owner_id] = round(agg.get(lot.owner_id, 0.0) + quote, 2)
        return agg

    @staticmethod
    async def regularization(db: AsyncSession, copro_id: uuid.UUID, year: int) -> dict:
        appele = await CoproComptaService._appele_par_owner(db, copro_id, year)
        reel = await CoproComptaService._reel_par_owner(db, copro_id, year)
        budget = await CoproComptaService.get_budget(db, copro_id, year)
        expenses = await CoproComptaService.list_expenses(db, copro_id, year)

        owner_ids = {oid for oid in (set(appele) | set(reel)) if oid}
        names: dict = {}
        if owner_ids:
            for o in (
                (await db.execute(select(Owner).where(Owner.id.in_(owner_ids)))).scalars().all()
            ):
                names[o.id] = o.full_name
        rows = []
        for oid in set(appele) | set(reel):
            a = round(appele.get(oid, 0.0), 2)
            r = round(reel.get(oid, 0.0), 2)
            rows.append(
                {
                    "owner_id": oid,
                    "owner_name": names.get(oid) if oid else "Sans copropriétaire",
                    "appele": a,
                    "reel": r,
                    "solde": round(a - r, 2),
                }
            )
        rows.sort(key=lambda x: (x["owner_name"] or "").lower())
        return {
            "year": year,
            "budget_total": float(budget["total"]) if budget else 0.0,
            "expenses_total": round(sum(e["amount"] for e in expenses), 2),
            "appele_total": round(sum(appele.values()), 2),
            "rows": rows,
        }

    @staticmethod
    async def regul_pdf_context(
        db: AsyncSession, copro_id: uuid.UUID, owner_id: uuid.UUID, year: int
    ) -> dict:
        """Décompte de régularisation d'un copropriétaire : détail des dépenses
        ventilées sur ses lots, provisions appelées et solde."""
        from app.models.copropriete import Copropriete

        copro = await db.get(Copropriete, copro_id)
        owner = await db.get(Owner, owner_id)
        keys = {
            k.id: k
            for k in (
                await db.execute(
                    select(CoproRepartitionKey).where(
                        CoproRepartitionKey.copropriete_id == copro_id
                    )
                )
            )
            .scalars()
            .all()
        }
        expenses = (
            (
                await db.execute(
                    select(CoproExpense).where(
                        CoproExpense.copropriete_id == copro_id, CoproExpense.year == year
                    )
                )
            )
            .scalars()
            .all()
        )
        # Tantièmes cumulés du copropriétaire par clé (somme de ses lots).
        lots = (
            (
                await db.execute(
                    select(CoproLot)
                    .options(selectinload(CoproLot.tantiemes))
                    .where(CoproLot.copropriete_id == copro_id, CoproLot.owner_id == owner_id)
                )
            )
            .scalars()
            .all()
        )
        own_tant: dict = {}
        for lot in lots:
            for t in lot.tantiemes:
                own_tant[t.key_id] = own_tant.get(t.key_id, 0.0) + float(t.tantiemes or 0)

        detail = []
        reel_total = 0.0
        for e in expenses:
            key = keys.get(e.key_id)
            base = float(key.total_tantiemes) if key else 0.0
            tant = own_tant.get(e.key_id, 0.0)
            quote = round(float(e.amount or 0) * tant / base, 2) if base > 0 else 0.0
            if quote <= 0:
                continue
            reel_total += quote
            detail.append(
                {
                    "label": e.label,
                    "key_name": key.name if key else "",
                    "expense_amount": float(e.amount or 0),
                    "tantiemes": tant,
                    "base": int(base),
                    "amount": quote,
                }
            )
        reel_total = round(reel_total, 2)
        appele = (await CoproComptaService._appele_par_owner(db, copro_id, year)).get(owner_id, 0.0)
        appele = round(appele, 2)
        return {
            "copro_name": copro.name if copro else "",
            "copro_address": (copro.full_address if copro else "") or "",
            "owner_name": owner.full_name if owner else "Copropriétaire",
            "year": year,
            "detail": detail,
            "reel_total": reel_total,
            "appele": appele,
            "solde": round(appele - reel_total, 2),
        }
