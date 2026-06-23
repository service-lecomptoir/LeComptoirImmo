"""Module Syndic — phase 4 : fonds de travaux (loi ALUR) et carnet d'entretien."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.copropriete_extras import CoproMaintenance, CoproWorksFundEntry
from app.schemas.copropriete_extras import (
    MaintenanceCreate,
    MaintenanceUpdate,
    WorksFundEntryCreate,
)


class CoproExtrasService:
    # ── Fonds de travaux ───────────────────────────────────────────────────────
    @staticmethod
    async def works_fund(db: AsyncSession, copro_id: uuid.UUID) -> dict:
        entries = (
            (
                await db.execute(
                    select(CoproWorksFundEntry)
                    .where(CoproWorksFundEntry.copropriete_id == copro_id)
                    .order_by(CoproWorksFundEntry.entry_date.desc())
                )
            )
            .scalars()
            .all()
        )
        contrib = round(sum(float(e.amount or 0) for e in entries if e.kind == "contribution"), 2)
        depense = round(sum(float(e.amount or 0) for e in entries if e.kind == "depense"), 2)
        return {
            "total_contributions": contrib,
            "total_depenses": depense,
            "balance": round(contrib - depense, 2),
            "entries": [
                {
                    "id": e.id,
                    "entry_date": e.entry_date,
                    "kind": e.kind,
                    "label": e.label,
                    "amount": float(e.amount or 0),
                }
                for e in entries
            ],
        }

    @staticmethod
    async def add_works_entry(
        db: AsyncSession, copro_id: uuid.UUID, data: WorksFundEntryCreate, created_by: uuid.UUID
    ) -> dict:
        e = CoproWorksFundEntry(
            copropriete_id=copro_id,
            entry_date=data.entry_date,
            kind=data.kind,
            label=data.label,
            amount=data.amount,
            created_by=created_by,
        )
        db.add(e)
        await db.flush()
        return {
            "id": e.id,
            "entry_date": e.entry_date,
            "kind": e.kind,
            "label": e.label,
            "amount": float(e.amount or 0),
        }

    @staticmethod
    async def delete_works_entry(
        db: AsyncSession, copro_id: uuid.UUID, entry_id: uuid.UUID
    ) -> None:
        e = await db.get(CoproWorksFundEntry, entry_id)
        if not e or e.copropriete_id != copro_id:
            raise NotFoundException("Mouvement introuvable")
        await db.delete(e)
        await db.flush()

    # ── Carnet d'entretien ─────────────────────────────────────────────────────
    @staticmethod
    def _serialize_maint(m: CoproMaintenance) -> dict:
        return {
            "id": m.id,
            "entry_date": m.entry_date,
            "category": m.category,
            "description": m.description,
            "supplier": m.supplier,
            "cost": float(m.cost) if m.cost is not None else None,
        }

    @staticmethod
    async def list_maintenance(db: AsyncSession, copro_id: uuid.UUID) -> list[dict]:
        rows = (
            (
                await db.execute(
                    select(CoproMaintenance)
                    .where(CoproMaintenance.copropriete_id == copro_id)
                    .order_by(CoproMaintenance.entry_date.desc().nullslast())
                )
            )
            .scalars()
            .all()
        )
        return [CoproExtrasService._serialize_maint(m) for m in rows]

    @staticmethod
    async def add_maintenance(
        db: AsyncSession, copro_id: uuid.UUID, data: MaintenanceCreate, created_by: uuid.UUID
    ) -> dict:
        m = CoproMaintenance(
            copropriete_id=copro_id,
            entry_date=data.entry_date,
            category=(data.category or None),
            description=data.description,
            supplier=(data.supplier or None),
            cost=data.cost,
            created_by=created_by,
        )
        db.add(m)
        await db.flush()
        return CoproExtrasService._serialize_maint(m)

    @staticmethod
    async def update_maintenance(
        db: AsyncSession, copro_id: uuid.UUID, maint_id: uuid.UUID, data: MaintenanceUpdate
    ) -> dict:
        m = await db.get(CoproMaintenance, maint_id)
        if not m or m.copropriete_id != copro_id:
            raise NotFoundException("Entrée d'entretien introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(m, field, value)
        await db.flush()
        return CoproExtrasService._serialize_maint(m)

    @staticmethod
    async def delete_maintenance(
        db: AsyncSession, copro_id: uuid.UUID, maint_id: uuid.UUID
    ) -> None:
        m = await db.get(CoproMaintenance, maint_id)
        if not m or m.copropriete_id != copro_id:
            raise NotFoundException("Entrée d'entretien introuvable")
        await db.delete(m)
        await db.flush()
