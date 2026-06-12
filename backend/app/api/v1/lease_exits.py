# -*- coding: utf-8 -*-
"""Gestion de la sortie du locataire.

Suivi du préavis et de la date de départ, organisation de l'état des lieux de
sortie et comparaison avec celui d'entrée (dégradations), décompte du dépôt de
garantie (retenues → restitution), puis clôture administrative du dossier
(résiliation du bail + libération du bien).
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role, get_current_user
from app.api.v1._isolation import assert_lease_access
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import Role
from app.database import get_db
from app.models.inspection import Inspection
from app.models.lease import Lease
from app.models.lease_exit import LeaseExit
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.lease import LeaseTerminate
from app.services.lease_service import LeaseService

router = APIRouter(prefix="/lease-exits", tags=["Sortie du locataire"])

_STATUSES = ("preavis", "etat_des_lieux", "decompte", "cloture")


# ── Schémas ────────────────────────────────────────────────────────────────────
class ExitCreate(BaseModel):
    lease_id: uuid.UUID
    notice_received_at: Optional[date] = None
    departure_date: Optional[date] = None


class PreavisIn(BaseModel):
    departure_date: Optional[date] = None


class ExitUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(preavis|etat_des_lieux|decompte)$")
    notice_received_at: Optional[date] = None
    departure_date: Optional[date] = None
    entry_inspection_id: Optional[uuid.UUID] = None
    exit_inspection_id: Optional[uuid.UUID] = None
    deductions: Optional[list] = None
    comments: Optional[str] = Field(None, max_length=4000)


# ── Helpers ────────────────────────────────────────────────────────────────────
async def _get_exit(db: AsyncSession, user: User, exit_id: uuid.UUID) -> tuple[LeaseExit, Lease]:
    ex = await db.get(LeaseExit, exit_id)
    if not ex:
        raise NotFoundException("Dossier de sortie", str(exit_id))
    lease = await LeaseService.get_by_id(db, ex.lease_id, load_relations=True)
    await assert_lease_access(db, user, lease)
    return ex, lease


def _insp_out(i: Optional[Inspection]) -> Optional[dict]:
    if not i:
        return None
    return {
        "id": i.id,
        "inspection_type": i.inspection_type,
        "inspection_date": i.inspection_date,
        "inspector_name": i.inspector_name,
        "overall_condition": i.overall_condition,
        "notes": i.notes,
    }


async def _out(db: AsyncSession, ex: LeaseExit, lease: Lease) -> dict:
    tenant = await db.get(Tenant, lease.tenant_id) if lease.tenant_id else None
    prop = await db.get(Property, lease.property_id) if lease.property_id else None
    entry = await db.get(Inspection, ex.entry_inspection_id) if ex.entry_inspection_id else None
    exit_i = await db.get(Inspection, ex.exit_inspection_id) if ex.exit_inspection_id else None
    deductions = ex.deductions or []
    total_deductions = round(sum(float(d.get("amount") or 0) for d in deductions), 2)
    deposit = float(ex.deposit_amount or 0)
    return {
        "id": ex.id,
        "lease_id": ex.lease_id,
        "status": ex.status,
        "tenant_name": getattr(tenant, "full_name", None),
        "property_id": lease.property_id,
        "property_name": getattr(prop, "name", None),
        "lease_is_active": lease.is_active,
        "notice_received_at": ex.notice_received_at,
        "departure_date": ex.departure_date,
        "entry_inspection": _insp_out(entry),
        "exit_inspection": _insp_out(exit_i),
        "deposit_amount": deposit,
        "deductions": deductions,
        "total_deductions": total_deductions,
        "deposit_to_return": round(max(0.0, deposit - total_deductions), 2),
        "comments": ex.comments,
        "closed_at": ex.closed_at,
        "created_at": ex.created_at,
        # États des lieux du bail, pour les sélecteurs (entrée / sortie).
        "lease_inspections": [
            _insp_out(i) for i in sorted(
                (lease.inspections or []), key=lambda x: x.inspection_date, reverse=True
            )
        ],
    }


def _clean_deductions(items: list) -> list:
    out = []
    for d in items:
        label = str(d.get("label") or "").strip()[:200]
        try:
            amount = round(float(d.get("amount") or 0), 2)
        except (TypeError, ValueError):
            amount = 0.0
        if label and amount > 0:
            out.append({"label": label, "amount": amount})
    return out


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("", summary="Dossiers de sortie")
async def list_exits(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    q = select(LeaseExit).order_by(LeaseExit.created_at.desc())
    if status in _STATUSES:
        q = q.where(LeaseExit.status == status)
    rows = (await db.execute(q)).scalars().all()
    out = []
    for ex in rows:
        try:
            lease = await LeaseService.get_by_id(db, ex.lease_id, load_relations=True)
            await assert_lease_access(db, user, lease)
        except Exception:  # noqa: BLE001 : hors périmètre / bail disparu → on masque
            continue
        out.append(await _out(db, ex, lease))
    return out


@router.get("/by-lease/{lease_id}", summary="Dossier de sortie d'un bail (s'il existe)")
async def exit_for_lease(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, user, lease)
    ex = (await db.execute(
        select(LeaseExit).where(LeaseExit.lease_id == lease_id)
    )).scalar_one_or_none()
    return await _out(db, ex, lease) if ex else None


@router.post("", status_code=201, summary="Ouvrir un dossier de sortie")
async def create_exit(
    data: ExitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    lease = await LeaseService.get_by_id(db, data.lease_id, load_relations=True)
    await assert_lease_access(db, user, lease, write=True)
    if not lease.is_active:
        raise BadRequestException("Ce bail est déjà résilié.")
    existing = (await db.execute(
        select(LeaseExit).where(LeaseExit.lease_id == data.lease_id)
    )).scalar_one_or_none()
    if existing:
        raise BadRequestException("Un dossier de sortie existe déjà pour ce bail.")

    # Pré-remplit l'état des lieux d'entrée le plus récent du bail, s'il existe.
    entry = next(
        (i for i in sorted((lease.inspections or []), key=lambda x: x.inspection_date, reverse=True)
         if i.inspection_type == "entree"),
        None,
    )
    ex = LeaseExit(
        lease_id=data.lease_id,
        status="preavis",
        notice_received_at=data.notice_received_at or date.today(),
        departure_date=data.departure_date,
        entry_inspection_id=entry.id if entry else None,
        deposit_amount=float(lease.deposit_amount or 0),
        deductions=[],
        created_by=user.id,
    )
    db.add(ex)
    await db.commit()
    await db.refresh(ex)
    return await _out(db, ex, lease)


@router.patch("/{exit_id}", summary="Mettre à jour le dossier de sortie")
async def update_exit(
    exit_id: uuid.UUID,
    data: ExitUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    ex, lease = await _get_exit(db, user, exit_id)
    if ex.status == "cloture":
        raise BadRequestException("Ce dossier de sortie est clôturé.")
    fields = data.model_dump(exclude_unset=True)
    if "deductions" in fields and fields["deductions"] is not None:
        ex.deductions = _clean_deductions(fields.pop("deductions"))
    lease_insp_ids = {i.id for i in (lease.inspections or [])}
    for key in ("entry_inspection_id", "exit_inspection_id"):
        if key in fields and fields[key] is not None and fields[key] not in lease_insp_ids:
            raise BadRequestException("L'état des lieux choisi n'appartient pas à ce bail.")
    for k, v in fields.items():
        setattr(ex, k, v)
    await db.commit()
    await db.refresh(ex)
    return await _out(db, ex, lease)


@router.post("/{exit_id}/close", summary="Clôturer le dossier (résilie le bail)")
async def close_exit(
    exit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Clôture administrative : résilie le bail à la date de départ (libère le bien)
    et fige le décompte du dépôt de garantie."""
    ex, lease = await _get_exit(db, user, exit_id)
    if ex.status == "cloture":
        raise BadRequestException("Ce dossier de sortie est déjà clôturé.")
    if not ex.departure_date:
        raise BadRequestException("Renseignez la date de départ avant de clôturer.")
    await assert_lease_access(db, user, lease, write=True)
    if lease.is_active:
        await LeaseService.terminate(db, lease.id, LeaseTerminate(
            end_date=ex.departure_date, notice_date=ex.notice_received_at,
        ))
    ex.status = "cloture"
    ex.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ex)
    lease = await LeaseService.get_by_id(db, ex.lease_id, load_relations=True)
    return await _out(db, ex, lease)


@router.delete("/{exit_id}", status_code=204, summary="Supprimer un dossier de sortie (non clôturé)")
async def delete_exit(
    exit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    ex, lease = await _get_exit(db, user, exit_id)
    if ex.status == "cloture":
        raise BadRequestException("Un dossier clôturé ne peut pas être supprimé.")
    await assert_lease_access(db, user, lease, write=True)
    await db.delete(ex)
    await db.commit()


# ── Côté locataire : envoi d'un préavis de départ ─────────────────────────────
async def _tenant_active_lease(db: AsyncSession, user: User):
    tenant = (await db.execute(
        select(Tenant).where(Tenant.user_id == user.id)
    )).scalar_one_or_none()
    if not tenant:
        raise BadRequestException("Profil locataire introuvable.")
    lease = (await db.execute(
        select(Lease).where(Lease.tenant_id == tenant.id, Lease.is_active.is_(True))
        .order_by(Lease.start_date.desc())
    )).scalars().first()
    return tenant, lease


@router.get("/locataire/mine", summary="Mon préavis de départ (locataire)")
async def my_preavis(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Statut du préavis pour le bail actif du locataire (null si aucun bail actif)."""
    tenant = (await db.execute(
        select(Tenant).where(Tenant.user_id == user.id)
    )).scalar_one_or_none()
    if not tenant:
        return None
    lease = (await db.execute(
        select(Lease).where(Lease.tenant_id == tenant.id, Lease.is_active.is_(True))
        .order_by(Lease.start_date.desc())
    )).scalars().first()
    if not lease:
        return None
    ex = (await db.execute(
        select(LeaseExit).where(LeaseExit.lease_id == lease.id)
    )).scalar_one_or_none()
    return {
        "lease_id": lease.id,
        "sent": bool(ex),
        "status": ex.status if ex else None,
        "notice_received_at": ex.notice_received_at if ex else None,
        "departure_date": ex.departure_date if ex else None,
    }


@router.post("/locataire/preavis", status_code=201, summary="Envoyer un préavis de départ (locataire)")
async def send_preavis(
    data: PreavisIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Le locataire transmet son préavis de départ : ouvre (ou met à jour) le dossier
    de sortie côté gestionnaire et le notifie. La résiliation reste à la main du
    gestionnaire (état des lieux, décompte, clôture)."""
    tenant, lease = await _tenant_active_lease(db, user)
    if not lease:
        raise BadRequestException("Aucun bail actif : impossible d'envoyer un préavis.")
    ex = (await db.execute(
        select(LeaseExit).where(LeaseExit.lease_id == lease.id)
    )).scalar_one_or_none()
    if ex and ex.status == "cloture":
        raise BadRequestException("Le dossier de sortie de ce bail est déjà clôturé.")
    if ex:
        if not ex.notice_received_at:
            ex.notice_received_at = date.today()
        if data.departure_date:
            ex.departure_date = data.departure_date
    else:
        entry = (await db.execute(
            select(Inspection).where(
                Inspection.lease_id == lease.id, Inspection.inspection_type == "entree"
            ).order_by(Inspection.inspection_date.desc())
        )).scalars().first()
        ex = LeaseExit(
            lease_id=lease.id, status="preavis", notice_received_at=date.today(),
            departure_date=data.departure_date,
            entry_inspection_id=entry.id if entry else None,
            deposit_amount=float(lease.deposit_amount or 0), deductions=[], created_by=user.id,
        )
        db.add(ex)
    await db.flush()

    manager_id = getattr(lease, "created_by", None)
    dep = f" Départ souhaité : {ex.departure_date:%d/%m/%Y}." if ex.departure_date else ""
    try:
        from app.models.notification import Notification, NotificationType, NotificationPriority
        db.add(Notification(
            title=f"Préavis de départ : {tenant.full_name}",
            message=f"{tenant.full_name} a transmis un préavis de départ.{dep} "
                    f"Ouvrez « Sortie du locataire » pour le traiter.",
            notification_type=NotificationType.SYSTEME, priority=NotificationPriority.HIGH,
            entity_type="lease_exit", entity_id=ex.id, user_id=manager_id,
        ))
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services import agent_events
        await agent_events.notify_manager(
            db, manager_id, "preavis",
            f"{tenant.full_name} a transmis un préavis de départ.{dep}",
            cta="Ouvrez « Sortie du locataire » pour organiser l'état des lieux et le décompte.",
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    return {"status": "received", "departure_date": ex.departure_date}
