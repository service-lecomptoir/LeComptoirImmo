"""Module Syndic — phase 3 : assemblées générales (résolutions, votes pondérés
par les tantièmes de la clé générale, dépouillement selon la règle de majorité)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.copropriete import CoproLot, CoproRepartitionKey
from app.models.copropriete_ag import CoproAssembly, CoproResolution, CoproVote
from app.models.owner import Owner
from app.schemas.copropriete_ag import (
    AssemblyCreate,
    AssemblyUpdate,
    ResolutionCreate,
    ResolutionUpdate,
)

MAJORITY_LABELS = {
    "art24": "Majorité simple (art. 24)",
    "art25": "Majorité absolue (art. 25)",
    "art26": "Double majorité (art. 26)",
    "unanimite": "Unanimité",
}


def _outcome(majority: str, pour: float, contre: float, abstention: float, base: float) -> str:
    """Résultat d'une résolution selon la règle de majorité (loi 10/07/1965).
    Calcul simplifié : base = total des tantièmes de la clé générale."""
    if pour == 0 and contre == 0 and abstention == 0:
        return "pending"
    if majority == "art24":
        # Majorité des voix exprimées (abstentions exclues).
        return "adopted" if pour > contre else "rejected"
    if majority == "art25":
        # Majorité absolue de tous les tantièmes.
        return "adopted" if pour > base / 2 else "rejected"
    if majority == "art26":
        # Au moins deux tiers de tous les tantièmes.
        return "adopted" if pour >= base * 2 / 3 else "rejected"
    if majority == "unanimite":
        return "adopted" if contre == 0 and abstention == 0 and pour > 0 else "rejected"
    return "pending"


class CoproAGService:
    # ── Pondération (tantièmes clé générale) ───────────────────────────────────
    @staticmethod
    async def _general_key(db: AsyncSession, copro_id: uuid.UUID) -> CoproRepartitionKey | None:
        keys = (
            (
                await db.execute(
                    select(CoproRepartitionKey)
                    .where(CoproRepartitionKey.copropriete_id == copro_id)
                    .order_by(CoproRepartitionKey.position)
                )
            )
            .scalars()
            .all()
        )
        if not keys:
            return None
        for k in keys:
            if k.is_general:
                return k
        return keys[0]

    @staticmethod
    async def voter_weights(db: AsyncSession, copro_id: uuid.UUID) -> tuple[dict, float]:
        """(poids par copropriétaire, base totale) sur la clé générale."""
        key = await CoproAGService._general_key(db, copro_id)
        if not key:
            return {}, 0.0
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
        weights: dict = {}
        for lot in lots:
            if not lot.owner_id:
                continue
            for t in lot.tantiemes:
                if t.key_id == key.id:
                    weights[lot.owner_id] = round(
                        weights.get(lot.owner_id, 0.0) + float(t.tantiemes or 0), 2
                    )
        return weights, float(key.total_tantiemes)

    @staticmethod
    async def voters(db: AsyncSession, copro_id: uuid.UUID) -> list[dict]:
        weights, _base = await CoproAGService.voter_weights(db, copro_id)
        if not weights:
            return []
        names = {
            o.id: o.full_name
            for o in (
                (await db.execute(select(Owner).where(Owner.id.in_(list(weights))))).scalars().all()
            )
        }
        rows = [
            {"owner_id": oid, "owner_name": names.get(oid), "tantiemes": w}
            for oid, w in weights.items()
        ]
        rows.sort(key=lambda r: (r["owner_name"] or "").lower())
        return rows

    # ── Assemblées ──────────────────────────────────────────────────────────────
    @staticmethod
    async def list_assemblies(db: AsyncSession, copro_id: uuid.UUID) -> list[dict]:
        rows = (
            (
                await db.execute(
                    select(CoproAssembly)
                    .where(CoproAssembly.copropriete_id == copro_id)
                    .order_by(
                        CoproAssembly.meeting_date.desc().nullslast(),
                        CoproAssembly.created_at.desc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        counts = (
            dict(
                (
                    await db.execute(
                        select(CoproResolution.assembly_id, func.count(CoproResolution.id))
                        .where(CoproResolution.assembly_id.in_([a.id for a in rows]))
                        .group_by(CoproResolution.assembly_id)
                    )
                ).all()
            )
            if rows
            else {}
        )
        return [
            {
                "id": a.id,
                "title": a.title,
                "kind": a.kind,
                "meeting_date": a.meeting_date,
                "status": a.status,
                "resolution_count": int(counts.get(a.id, 0)),
                "created_at": a.created_at,
            }
            for a in rows
        ]

    @staticmethod
    async def _assembly_for(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID
    ) -> CoproAssembly:
        a = await db.get(CoproAssembly, assembly_id)
        if not a or a.copropriete_id != copro_id:
            raise NotFoundException("Assemblée introuvable")
        return a

    @staticmethod
    async def create_assembly(
        db: AsyncSession, copro_id: uuid.UUID, data: AssemblyCreate, created_by: uuid.UUID
    ) -> dict:
        a = CoproAssembly(
            copropriete_id=copro_id,
            title=data.title,
            kind=data.kind,
            meeting_date=data.meeting_date,
            location=(data.location or None),
            notes=(data.notes or None),
            created_by=created_by,
        )
        db.add(a)
        await db.flush()
        return await CoproAGService.get_detail(db, copro_id, a.id)

    @staticmethod
    async def update_assembly(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID, data: AssemblyUpdate
    ) -> dict:
        a = await CoproAGService._assembly_for(db, copro_id, assembly_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(a, field, value)
        await db.flush()
        return await CoproAGService.get_detail(db, copro_id, assembly_id)

    @staticmethod
    async def delete_assembly(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID
    ) -> None:
        a = await CoproAGService._assembly_for(db, copro_id, assembly_id)
        await db.delete(a)
        await db.flush()

    # ── Détail + dépouillement ────────────────────────────────────────────────
    @staticmethod
    async def get_detail(db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID) -> dict:
        a = await CoproAGService._assembly_for(db, copro_id, assembly_id)
        weights, base = await CoproAGService.voter_weights(db, copro_id)
        resolutions = (
            (
                await db.execute(
                    select(CoproResolution)
                    .options(selectinload(CoproResolution.votes))
                    .where(CoproResolution.assembly_id == assembly_id)
                    .order_by(CoproResolution.position, CoproResolution.created_at)
                )
            )
            .scalars()
            .all()
        )
        owner_ids = {v.owner_id for r in resolutions for v in r.votes}
        names = {}
        if owner_ids:
            names = {
                o.id: o.full_name
                for o in (
                    (await db.execute(select(Owner).where(Owner.id.in_(list(owner_ids)))))
                    .scalars()
                    .all()
                )
            }
        res_out = []
        for r in resolutions:
            pour = contre = abstention = 0.0
            vote_rows = []
            for v in r.votes:
                w = weights.get(v.owner_id, 0.0)
                if v.choice == "pour":
                    pour += w
                elif v.choice == "contre":
                    contre += w
                else:
                    abstention += w
                vote_rows.append(
                    {
                        "owner_id": v.owner_id,
                        "owner_name": names.get(v.owner_id),
                        "choice": v.choice,
                        "tantiemes": round(w, 2),
                    }
                )
            res_out.append(
                {
                    "id": r.id,
                    "position": r.position,
                    "title": r.title,
                    "description": r.description,
                    "majority": r.majority,
                    "outcome": r.outcome,
                    "base_tantiemes": int(base),
                    "pour": round(pour, 2),
                    "contre": round(contre, 2),
                    "abstention": round(abstention, 2),
                    "votes": vote_rows,
                }
            )
        return {
            "id": a.id,
            "copropriete_id": a.copropriete_id,
            "title": a.title,
            "kind": a.kind,
            "meeting_date": a.meeting_date,
            "location": a.location,
            "status": a.status,
            "notes": a.notes,
            "resolutions": res_out,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }

    # ── Résolutions ──────────────────────────────────────────────────────────────
    @staticmethod
    async def add_resolution(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID, data: ResolutionCreate
    ) -> dict:
        await CoproAGService._assembly_for(db, copro_id, assembly_id)
        r = CoproResolution(
            assembly_id=assembly_id,
            title=data.title,
            description=(data.description or None),
            majority=data.majority,
            position=data.position,
        )
        db.add(r)
        await db.flush()
        return await CoproAGService.get_detail(db, copro_id, assembly_id)

    @staticmethod
    async def _resolution_for(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID, resolution_id: uuid.UUID
    ) -> CoproResolution:
        r = await db.get(CoproResolution, resolution_id)
        if not r or r.assembly_id != assembly_id:
            raise NotFoundException("Résolution introuvable")
        await CoproAGService._assembly_for(db, copro_id, assembly_id)
        return r

    @staticmethod
    async def update_resolution(
        db: AsyncSession,
        copro_id: uuid.UUID,
        assembly_id: uuid.UUID,
        resolution_id: uuid.UUID,
        data: ResolutionUpdate,
    ) -> dict:
        r = await CoproAGService._resolution_for(db, copro_id, assembly_id, resolution_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(r, field, value)
        await db.flush()
        return await CoproAGService.get_detail(db, copro_id, assembly_id)

    @staticmethod
    async def delete_resolution(
        db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID, resolution_id: uuid.UUID
    ) -> None:
        r = await CoproAGService._resolution_for(db, copro_id, assembly_id, resolution_id)
        await db.delete(r)
        await db.flush()

    # ── Votes ─────────────────────────────────────────────────────────────────
    @staticmethod
    async def set_vote(
        db: AsyncSession,
        copro_id: uuid.UUID,
        assembly_id: uuid.UUID,
        resolution_id: uuid.UUID,
        owner_id: uuid.UUID,
        choice: str,
    ) -> dict:
        r = await CoproAGService._resolution_for(db, copro_id, assembly_id, resolution_id)
        existing = (
            (
                await db.execute(
                    select(CoproVote).where(
                        CoproVote.resolution_id == resolution_id, CoproVote.owner_id == owner_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing:
            existing.choice = choice
        else:
            db.add(CoproVote(resolution_id=resolution_id, owner_id=owner_id, choice=choice))
        await db.flush()
        await CoproAGService._recompute_outcome(db, copro_id, r)
        return await CoproAGService.get_detail(db, copro_id, assembly_id)

    @staticmethod
    async def clear_vote(
        db: AsyncSession,
        copro_id: uuid.UUID,
        assembly_id: uuid.UUID,
        resolution_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> dict:
        r = await CoproAGService._resolution_for(db, copro_id, assembly_id, resolution_id)
        existing = (
            (
                await db.execute(
                    select(CoproVote).where(
                        CoproVote.resolution_id == resolution_id, CoproVote.owner_id == owner_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing:
            await db.delete(existing)
            await db.flush()
        await CoproAGService._recompute_outcome(db, copro_id, r)
        return await CoproAGService.get_detail(db, copro_id, assembly_id)

    @staticmethod
    async def _recompute_outcome(
        db: AsyncSession, copro_id: uuid.UUID, resolution: CoproResolution
    ) -> None:
        weights, base = await CoproAGService.voter_weights(db, copro_id)
        votes = (
            (await db.execute(select(CoproVote).where(CoproVote.resolution_id == resolution.id)))
            .scalars()
            .all()
        )
        pour = contre = abstention = 0.0
        for v in votes:
            w = weights.get(v.owner_id, 0.0)
            if v.choice == "pour":
                pour += w
            elif v.choice == "contre":
                contre += w
            else:
                abstention += w
        resolution.outcome = _outcome(resolution.majority, pour, contre, abstention, base)
        await db.flush()

    # ── PDF (convocation + PV) ────────────────────────────────────────────────
    @staticmethod
    async def pdf_context(db: AsyncSession, copro_id: uuid.UUID, assembly_id: uuid.UUID) -> dict:
        from app.models.copropriete import Copropriete

        detail = await CoproAGService.get_detail(db, copro_id, assembly_id)
        copro = await db.get(Copropriete, copro_id)
        detail["copro_name"] = copro.name if copro else ""
        detail["copro_address"] = (copro.full_address if copro else "") or ""
        for r in detail["resolutions"]:
            r["majority_label"] = MAJORITY_LABELS.get(r["majority"], r["majority"])
        return detail
