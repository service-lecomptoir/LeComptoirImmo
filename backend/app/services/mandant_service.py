"""Compta mandant : compte rendu de gestion (CRG) du mandataire pour un propriétaire.

Calcule, à partir des loyers réellement encaissés (cf. OwnerService.get_finances)
et des honoraires de gestion configurés, le net dû au propriétaire, les
reversements déjà effectués et le solde restant à reverser. Gère aussi le CRUD
des reversements.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.owner_reversement import OwnerReversement
from app.schemas.owner_reversement import ReversementCreate
from app.services.owner_service import OwnerService

# Périodicités du compte rendu de gestion.
CRG_PERIODS = ("mensuel", "trimestriel", "semestriel", "annuel")
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


def resolve_period(year: int, period: str, index: int) -> tuple[int, int, str]:
    """(month_start, month_end, libellé) pour une périodicité CRG donnée.

    `index` désigne le mois (1-12), le trimestre (1-4) ou le semestre (1-2) ;
    ignoré pour l'annuel. Toute valeur hors bornes est repliée sur l'année."""
    if period == "mensuel":
        m = min(12, max(1, index))
        return m, m, f"{_MONTHS_FR[m]} {year}"
    if period == "trimestriel":
        q = min(4, max(1, index))
        s = (q - 1) * 3 + 1
        return s, s + 2, f"T{q} {year}"
    if period == "semestriel":
        h = min(2, max(1, index))
        s = (h - 1) * 6 + 1
        return s, s + 5, f"{'1er' if h == 1 else '2e'} semestre {year}"
    return 1, 12, f"Année {year}"


class MandantService:
    @staticmethod
    async def list_reversements(
        db: AsyncSession, owner_id: uuid.UUID, year: int | None = None
    ) -> list[OwnerReversement]:
        q = select(OwnerReversement).where(OwnerReversement.owner_id == owner_id)
        if year is not None:
            q = q.where(OwnerReversement.period_year == year)
        q = q.order_by(OwnerReversement.reversement_date.desc())
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def create_reversement(
        db: AsyncSession, owner_id: uuid.UUID, data: ReversementCreate, created_by: uuid.UUID
    ) -> OwnerReversement:
        from app.models.owner import Owner

        owner = await db.get(Owner, owner_id)
        if not owner:
            raise NotFoundException("Propriétaire introuvable")
        rev = OwnerReversement(
            owner_id=owner_id,
            period_year=data.period_year,
            period_month=data.period_month,
            amount=data.amount,
            method=(data.method or None),
            reversement_date=data.reversement_date,
            label=(data.label or None),
            note=(data.note or None),
            created_by=created_by,
        )
        db.add(rev)
        await db.flush()
        await db.refresh(rev)
        return rev

    @staticmethod
    async def delete_reversement(
        db: AsyncSession, owner_id: uuid.UUID, reversement_id: uuid.UUID
    ) -> None:
        rev = await db.get(OwnerReversement, reversement_id)
        if not rev or rev.owner_id != owner_id:
            raise NotFoundException("Reversement introuvable")
        await db.delete(rev)
        await db.flush()

    @staticmethod
    async def get_account(
        db: AsyncSession,
        owner_id: uuid.UUID,
        year: int,
        period: str = "annuel",
        index: int = 1,
    ) -> dict:
        """Compte mandant d'un propriétaire pour une période (mensuel/trimestriel/
        semestriel/annuel) : encaissé, honoraires (HT/TVA/TTC), net dû, reversé et
        solde à reverser."""
        month_start, month_end, period_label = resolve_period(year, period, index)
        finances = await OwnerService.get_finances(db, owner_id, year, month_start, month_end)
        fiscal = finances["fiscal"]

        gross_rent = float(fiscal["gross_rent_revenue"])
        charges_received = float(fiscal["charges_received"])
        fees_ht = float(fiscal["management_fees_ht"])
        fees_vat = float(fiscal["management_fees_vat"])
        fees_ttc = float(fiscal["management_fees_ttc"])

        # Total encaissé pour le compte du propriétaire (loyers + charges).
        total_encaisse = round(gross_rent + charges_received, 2)
        # Net dû au propriétaire = encaissé - honoraires TTC retenus par le mandataire.
        net_du = round(total_encaisse - fees_ttc, 2)

        all_reversements = await MandantService.list_reversements(db, owner_id, year)
        # Vue infra-annuelle : on ne compte que les reversements rattachés à un mois
        # de la plage. Vue annuelle : tous (y compris ceux sans mois précis).
        is_annual = month_start == 1 and month_end == 12
        reversements = [
            r
            for r in all_reversements
            if is_annual
            or (r.period_month is not None and month_start <= r.period_month <= month_end)
        ]
        total_reverse = round(sum(float(r.amount) for r in reversements), 2)
        solde_a_reverser = round(net_du - total_reverse, 2)

        return {
            "owner_id": finances["owner_id"],
            "owner_name": finances["owner_name"],
            "year": year,
            "period": period,
            "period_index": index,
            "period_label": period_label,
            "month_start": month_start,
            "month_end": month_end,
            "honoraires": {
                "rate": fiscal["management_fee_rate"],
                "vat_rate": fiscal["management_fee_vat_rate"],
                "ht": fees_ht,
                "vat": fees_vat,
                "ttc": fees_ttc,
            },
            "loyers_encaisses": gross_rent,
            "charges_encaissees": charges_received,
            "total_encaisse": total_encaisse,
            "net_proprietaire": net_du,
            "total_reverse": total_reverse,
            "solde_a_reverser": solde_a_reverser,
            "reversements": [
                {
                    "id": r.id,
                    "period_year": r.period_year,
                    "period_month": r.period_month,
                    "amount": float(r.amount),
                    "method": r.method,
                    "reversement_date": r.reversement_date,
                    "label": r.label,
                    "note": r.note,
                }
                for r in reversements
            ],
            # Détail des revenus (lignes mensuelles) réutilisé pour le CRG.
            "revenus": finances["revenus"],
            "biens": finances["biens"],
        }
