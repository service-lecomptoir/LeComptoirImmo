"""Module Syndic (copropriété) — phase 1 : copropriétés, lots, clés de
répartition et tantièmes. Les copropriétaires réutilisent l'entité Owner."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.copropriete import (
    CoproLot,
    CoproLotTantieme,
    Copropriete,
    CoproRepartitionKey,
)
from app.models.owner import Owner
from app.schemas.copropriete import (
    CoproprieteCreate,
    CoproprieteUpdate,
    LotCreate,
    LotUpdate,
    RepartitionKeyCreate,
    RepartitionKeyUpdate,
)
from app.utils.address import normalize_address_fields


class CoproprieteService:
    # ── Copropriété ──────────────────────────────────────────────────────────
    @staticmethod
    async def create(
        db: AsyncSession, data: CoproprieteCreate, created_by: uuid.UUID
    ) -> Copropriete:
        from app.services.reference_service import make_ref

        copro = Copropriete(**data.model_dump(), created_by=created_by)
        copro.address, copro.zip_code, copro.city = normalize_address_fields(
            copro.address, copro.zip_code, copro.city
        )
        copro.ref_code = await make_ref(db, Copropriete.ref_code, "CP")
        db.add(copro)
        await db.flush()
        # Clé générale par défaut (charges communes générales, base 10000 millièmes).
        db.add(
            CoproRepartitionKey(
                copropriete_id=copro.id,
                name="Charges générales",
                total_tantiemes=10000,
                is_general=True,
                position=0,
            )
        )
        await db.flush()
        return copro

    @staticmethod
    async def get_by_id(db: AsyncSession, copro_id: uuid.UUID) -> Copropriete:
        copro = await db.get(Copropriete, copro_id)
        if not copro:
            raise NotFoundException("Copropriété", str(copro_id))
        return copro

    @staticmethod
    async def list_for_member_ids(
        db: AsyncSession, member_ids: set[uuid.UUID] | None
    ) -> list[dict]:
        """Liste (agency-scopée si member_ids fourni) avec le nombre de lots."""
        q = select(Copropriete).order_by(Copropriete.name)
        if member_ids is not None:
            q = q.where(Copropriete.created_by.in_(member_ids))
        copros = list((await db.execute(q)).scalars().all())
        if not copros:
            return []
        counts = dict(
            (
                await db.execute(
                    select(CoproLot.copropriete_id, func.count(CoproLot.id))
                    .where(CoproLot.copropriete_id.in_([c.id for c in copros]))
                    .group_by(CoproLot.copropriete_id)
                )
            ).all()
        )
        return [
            {
                "id": c.id,
                "ref_code": c.ref_code,
                "name": c.name,
                "city": c.city,
                "immatriculation": c.immatriculation,
                "lot_count": int(counts.get(c.id, 0)),
                "created_at": c.created_at,
            }
            for c in copros
        ]

    @staticmethod
    async def update(db: AsyncSession, copro_id: uuid.UUID, data: CoproprieteUpdate) -> Copropriete:
        copro = await CoproprieteService.get_by_id(db, copro_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(copro, field, value)
        copro.address, copro.zip_code, copro.city = normalize_address_fields(
            copro.address, copro.zip_code, copro.city
        )
        await db.flush()
        await db.refresh(copro)
        return copro

    @staticmethod
    async def delete(db: AsyncSession, copro_id: uuid.UUID) -> None:
        copro = await CoproprieteService.get_by_id(db, copro_id)
        await db.delete(copro)
        await db.flush()

    # ── Détail (clés + lots + tantièmes) ──────────────────────────────────────
    @staticmethod
    async def get_detail(db: AsyncSession, copro_id: uuid.UUID) -> dict:
        copro = await CoproprieteService.get_by_id(db, copro_id)
        keys = list(
            (
                await db.execute(
                    select(CoproRepartitionKey)
                    .where(CoproRepartitionKey.copropriete_id == copro_id)
                    .order_by(CoproRepartitionKey.position, CoproRepartitionKey.name)
                )
            )
            .scalars()
            .all()
        )
        lots = list(
            (
                await db.execute(
                    select(CoproLot)
                    .options(selectinload(CoproLot.tantiemes), selectinload(CoproLot.owner))
                    .where(CoproLot.copropriete_id == copro_id)
                    .order_by(CoproLot.numero)
                )
            )
            .scalars()
            .all()
        )

        # Somme des tantièmes affectés par clé (pour le contrôle d'équilibre).
        assigned: dict[uuid.UUID, float] = {}
        for lot in lots:
            for t in lot.tantiemes:
                assigned[t.key_id] = assigned.get(t.key_id, 0.0) + float(t.tantiemes or 0)

        keys_out = [
            {
                "id": k.id,
                "name": k.name,
                "total_tantiemes": k.total_tantiemes,
                "is_general": k.is_general,
                "position": k.position,
                "assigned_tantiemes": round(assigned.get(k.id, 0.0), 2),
                "balanced": round(assigned.get(k.id, 0.0), 2) == float(k.total_tantiemes),
            }
            for k in keys
        ]
        lots_out = [
            {
                "id": lot.id,
                "numero": lot.numero,
                "lot_type": lot.lot_type,
                "floor": lot.floor,
                "description": lot.description,
                "owner_id": lot.owner_id,
                "owner_name": lot.owner.full_name if lot.owner else None,
                "property_id": lot.property_id,
                "tantiemes": {str(t.key_id): float(t.tantiemes or 0) for t in lot.tantiemes},
            }
            for lot in lots
        ]
        return {
            "id": copro.id,
            "ref_code": copro.ref_code,
            "name": copro.name,
            "immatriculation": copro.immatriculation,
            "address": copro.address,
            "zip_code": copro.zip_code,
            "city": copro.city,
            "country": copro.country,
            "construction_year": copro.construction_year,
            "notes": copro.notes,
            "keys": keys_out,
            "lots": lots_out,
            "created_at": copro.created_at,
            "updated_at": copro.updated_at,
        }

    # ── Clés de répartition ───────────────────────────────────────────────────
    @staticmethod
    async def add_key(
        db: AsyncSession, copro_id: uuid.UUID, data: RepartitionKeyCreate
    ) -> CoproRepartitionKey:
        await CoproprieteService.get_by_id(db, copro_id)
        key = CoproRepartitionKey(copropriete_id=copro_id, **data.model_dump())
        db.add(key)
        await db.flush()
        await db.refresh(key)
        return key

    @staticmethod
    async def update_key(
        db: AsyncSession, copro_id: uuid.UUID, key_id: uuid.UUID, data: RepartitionKeyUpdate
    ) -> CoproRepartitionKey:
        key = await db.get(CoproRepartitionKey, key_id)
        if not key or key.copropriete_id != copro_id:
            raise NotFoundException("Clé de répartition introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(key, field, value)
        await db.flush()
        await db.refresh(key)
        return key

    @staticmethod
    async def delete_key(db: AsyncSession, copro_id: uuid.UUID, key_id: uuid.UUID) -> None:
        key = await db.get(CoproRepartitionKey, key_id)
        if not key or key.copropriete_id != copro_id:
            raise NotFoundException("Clé de répartition introuvable")
        await db.delete(key)
        await db.flush()

    # ── Lots ──────────────────────────────────────────────────────────────────
    @staticmethod
    async def _set_tantiemes(db: AsyncSession, lot: CoproLot, tantiemes: list) -> None:
        """Remplace les tantièmes du lot par la liste fournie (clé → valeur)."""
        existing = {
            t.key_id: t
            for t in (
                await db.execute(select(CoproLotTantieme).where(CoproLotTantieme.lot_id == lot.id))
            )
            .scalars()
            .all()
        }
        seen = set()
        for entry in tantiemes:
            seen.add(entry.key_id)
            if entry.key_id in existing:
                existing[entry.key_id].tantiemes = entry.tantiemes
            else:
                db.add(
                    CoproLotTantieme(lot_id=lot.id, key_id=entry.key_id, tantiemes=entry.tantiemes)
                )
        # Supprime les tantièmes des clés non transmises.
        for key_id, t in existing.items():
            if key_id not in seen:
                await db.delete(t)
        await db.flush()

    @staticmethod
    async def create_lot(db: AsyncSession, copro_id: uuid.UUID, data: LotCreate) -> CoproLot:
        await CoproprieteService.get_by_id(db, copro_id)
        payload = data.model_dump(exclude={"tantiemes"})
        lot = CoproLot(copropriete_id=copro_id, **payload)
        db.add(lot)
        await db.flush()
        await CoproprieteService._set_tantiemes(db, lot, data.tantiemes or [])
        return lot

    @staticmethod
    async def update_lot(
        db: AsyncSession, copro_id: uuid.UUID, lot_id: uuid.UUID, data: LotUpdate
    ) -> CoproLot:
        lot = await db.get(CoproLot, lot_id)
        if not lot or lot.copropriete_id != copro_id:
            raise NotFoundException("Lot introuvable")
        for field, value in data.model_dump(exclude_unset=True, exclude={"tantiemes"}).items():
            setattr(lot, field, value)
        await db.flush()
        if data.tantiemes is not None:
            await CoproprieteService._set_tantiemes(db, lot, data.tantiemes)
        await db.refresh(lot)
        return lot

    @staticmethod
    async def delete_lot(db: AsyncSession, copro_id: uuid.UUID, lot_id: uuid.UUID) -> None:
        lot = await db.get(CoproLot, lot_id)
        if not lot or lot.copropriete_id != copro_id:
            raise NotFoundException("Lot introuvable")
        await db.delete(lot)
        await db.flush()

    @staticmethod
    async def owner_name(db: AsyncSession, owner_id: uuid.UUID | None) -> str | None:
        if not owner_id:
            return None
        owner = await db.get(Owner, owner_id)
        return owner.full_name if owner else None
