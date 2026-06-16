"""Actualisation des loyers (révision IRL) et des charges. Réservé aux gestionnaires.

Étape 1 : indices IRL (manuel + INSEE) et révision du loyer par bail.
Étape 2 : mention de révision 1 mois à l'avance (avis/quittance/e-mail).
Étape 3 : régularisation annuelle des charges (provisions vs charges réelles →
réajustement de la provision mensuelle + solde remboursement/complément).
"""
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_gestionnaire
from app.core.permissions import Role
from app.api.v1._isolation import agency_lease_ids, assert_manager_scope
from app.models.user import User
from app.models.lease import Lease
from app.models.charge_regularization import ChargeRegularization
from app.services.irl_service import IrlService
from app.services.charge_regularization_service import ChargeRegularizationService

router = APIRouter(prefix="/actualisation", tags=["Actualisation"])


# ── Indices IRL ─────────────────────────────────────────────────────────────────
class IrlIn(BaseModel):
    year: int
    quarter: int  # 1..4
    value: float


@router.get("/irl")
async def list_irl(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_gestionnaire)):
    rows = await IrlService.list_indices(db)
    return [{"id": str(r.id), "year": r.year, "quarter": r.quarter,
             "value": float(r.value), "source": r.source} for r in rows]


@router.post("/irl", status_code=201)
async def add_irl(data: IrlIn, db: AsyncSession = Depends(get_db),
                  _: User = Depends(get_current_gestionnaire)):
    if data.quarter < 1 or data.quarter > 4:
        raise HTTPException(status_code=400, detail="Trimestre invalide (1 à 4)")
    idx = await IrlService.upsert(db, data.year, data.quarter, data.value, source="manuel")
    await db.commit()
    return {"id": str(idx.id), "year": idx.year, "quarter": idx.quarter,
            "value": float(idx.value), "source": idx.source}


@router.patch("/irl/{irl_id}")
async def update_irl(irl_id: uuid.UUID, data: IrlIn, db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_gestionnaire)):
    if data.quarter < 1 or data.quarter > 4:
        raise HTTPException(status_code=400, detail="Trimestre invalide (1 à 4)")
    try:
        idx = await IrlService.update(db, irl_id, data.year, data.quarter, data.value)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not idx:
        raise HTTPException(status_code=404, detail="Indice introuvable")
    await db.commit()
    return {"id": str(idx.id), "year": idx.year, "quarter": idx.quarter,
            "value": float(idx.value), "source": idx.source}


@router.delete("/irl/{irl_id}", status_code=204)
async def delete_irl(irl_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_gestionnaire)):
    ok = await IrlService.delete(db, irl_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Indice introuvable")
    await db.commit()


@router.post("/irl/refresh")
async def refresh_irl(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_gestionnaire)):
    res = await IrlService.fetch_from_insee(db)
    await db.commit()
    return res


# ── Révision des loyers ──────────────────────────────────────────────────────────
def _next_revision_date(lease: Lease) -> date:
    base = lease.last_revision_date or lease.start_date
    try:
        return base.replace(year=base.year + 1)
    except ValueError:  # 29 février
        return base + timedelta(days=365)


async def _scoped_active_leases(db: AsyncSession, current_user: User) -> list[Lease]:
    role = Role(current_user.role)
    q = (
        select(Lease)
        .options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.is_active == True)  # noqa: E712
    )
    leases = (await db.execute(q)).scalars().all()
    if role == Role.GESTIONNAIRE:
        allowed = await agency_lease_ids(db, current_user)
        leases = [l for l in leases if l.id in allowed]
    elif role == Role.GESTIONNAIRE_PROPRIO:
        leases = [l for l in leases if l.created_by == current_user.id]
    return list(leases)


async def _row(db: AsyncSession, lease: Lease) -> dict:
    prop = lease.parent_property
    current_rent = float(lease.rent_amount)
    quarter = lease.irl_quarter
    base = float(lease.irl_base_index) if lease.irl_base_index is not None else None
    latest = await IrlService.get_latest_for_quarter(db, quarter) if quarter else None
    proposed = None
    if base and base > 0 and latest is not None:
        proposed = round(current_rent * float(latest.value) / base, 2)
    nrd = _next_revision_date(lease)
    # Réévaluation de loyer déjà programmée (non encore appliquée) → visible sur la ligne.
    from app.services.rent_revision_service import RentRevisionService
    revs = await RentRevisionService.list_for_lease(db, lease.id)
    today = date.today()
    pend = next((r for r in revs if r.kind == "rent" and not r.applied and r.effective_date > today), None)
    return {
        "lease_id": str(lease.id),
        "tenant_full_name": lease.tenant.full_name if lease.tenant else "",
        "property_name": prop.name if prop else "",
        "owner_id": str(prop.owner_id) if prop and prop.owner_id else None,
        "owner_name": (prop.owner_name if prop else None) or "Sans propriétaire",
        "current_rent": current_rent,
        "charges": float(lease.charges_amount),
        "irl_quarter": quarter,
        "base_index": base,
        "latest_index_year": latest.year if latest else None,
        "latest_index_value": float(latest.value) if latest else None,
        "proposed_rent": proposed,
        "next_revision_date": nrd.isoformat(),
        "revision_due": date.today() >= nrd,
        "start_date": lease.start_date.isoformat(),
        # Révision programmée (loyer)
        "pending_rent": float(pend.amount) if pend else None,
        "pending_rent_id": str(pend.id) if pend else None,
        "pending_rent_date": pend.effective_date.isoformat() if pend else None,
    }


@router.get("/loyers")
async def list_revisions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    leases = await _scoped_active_leases(db, current_user)
    return [await _row(db, l) for l in leases]


class ReferenceIn(BaseModel):
    irl_quarter: int
    irl_base_index: float


@router.patch("/loyers/{lease_id}/reference")
async def set_reference(
    lease_id: uuid.UUID,
    data: ReferenceIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    if data.irl_quarter < 1 or data.irl_quarter > 4:
        raise HTTPException(status_code=400, detail="Trimestre invalide (1 à 4)")
    lease.irl_quarter = data.irl_quarter
    lease.irl_base_index = data.irl_base_index
    await db.flush()
    await db.commit()
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _row(db, lease)


@router.post("/loyers/{lease_id}/reference/clear")
async def clear_reference(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Réinitialise l'indice IRL de référence d'un bail (trimestre + indice de base)."""
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    lease.irl_quarter = None
    lease.irl_base_index = None
    await db.flush()
    await db.commit()
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _row(db, lease)


class ApplyRevisionIn(BaseModel):
    effective_date: Optional[date] = None


@router.post("/loyers/{lease_id}/appliquer")
async def apply_revision(
    lease_id: uuid.UUID,
    data: Optional[ApplyRevisionIn] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.models.tenant import Tenant
    from app.services.rent_revision_service import RentRevisionService, first_of_next_month

    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    if not lease.irl_quarter or lease.irl_base_index is None:
        raise HTTPException(status_code=400, detail="Indice IRL de référence non renseigné sur ce bail")
    base = float(lease.irl_base_index)
    latest = await IrlService.get_latest_for_quarter(db, lease.irl_quarter)
    if latest is None or base <= 0:
        raise HTTPException(status_code=400, detail="Indice IRL récent indisponible pour ce trimestre")

    old_rent = float(lease.rent_amount)
    new_rent = round(old_rent * float(latest.value) / base, 2)
    eff = (data.effective_date if data else None) or first_of_next_month(date.today())
    # Révision datée : le mois courant reste figé, l'ancien loyer est conservé en historique.
    await RentRevisionService.schedule(
        db, lease, kind="rent", new_amount=new_rent,
        effective_date=eff, source="irl",
        reason=f"Révision IRL T{lease.irl_quarter} {latest.year}",
        created_by=current_user.id,
    )
    lease.irl_base_index = float(latest.value)
    lease.last_revision_date = eff

    # Notifie le locataire de la révision (mention 1 mois à l'avance à câbler sur l'avis/quittance/email).
    tenant = await db.get(Tenant, lease.tenant_id)
    if tenant and tenant.user_id:
        db.add(Notification(
            title="Révision de votre loyer",
            message=(
                f"Votre loyer est révisé selon l'indice IRL (T{lease.irl_quarter} {latest.year}) : "
                f"{old_rent:.2f} € → {new_rent:.2f} €. La nouvelle mensualité s'appliquera aux prochains avis."
            ),
            notification_type=NotificationType.SYSTEME,
            priority=NotificationPriority.NORMAL,
            entity_type="lease",
            entity_id=lease.id,
            user_id=tenant.user_id,
        ))

    await db.flush()
    await db.commit()
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _row(db, lease)


# ── Réévaluation amiable du loyer (accord avec le locataire) ─────────────────────
class AmiableRentIn(BaseModel):
    new_rent: float
    effective_date: Optional[date] = None
    note: Optional[str] = None


@router.post("/loyers/{lease_id}/reevaluation-amiable")
async def amiable_rent(
    lease_id: uuid.UUID,
    data: AmiableRentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Réévalue le loyer d'un commun accord avec le locataire (hors formule IRL)."""
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.models.tenant import Tenant

    if data.new_rent < 0:
        raise HTTPException(status_code=400, detail="Loyer négatif invalide")
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")

    from app.services.rent_revision_service import RentRevisionService, first_of_next_month
    old_rent = float(lease.rent_amount)
    eff = data.effective_date or first_of_next_month(date.today())
    # Révision datée : le mois courant reste figé, l'ancien loyer est conservé en historique.
    await RentRevisionService.schedule(
        db, lease, kind="rent", new_amount=float(data.new_rent),
        effective_date=eff, source="amiable", reason=data.note or "Réévaluation amiable",
        created_by=current_user.id,
    )
    # Le loyer convenu devient la nouvelle base ; on ancre la date de dernière révision.
    lease.last_revision_date = eff

    tenant = await db.get(Tenant, lease.tenant_id)
    if tenant and tenant.user_id:
        msg = (f"Suite à votre accord, votre loyer est réévalué : {old_rent:.2f} € → "
               f"{float(data.new_rent):.2f} € à compter du {eff.strftime('%d/%m/%Y')}.")
        if data.note:
            msg += f" {data.note}"
        db.add(Notification(
            title="Réévaluation amiable de votre loyer",
            message=msg,
            notification_type=NotificationType.SYSTEME,
            priority=NotificationPriority.NORMAL,
            entity_type="lease", entity_id=lease.id, user_id=tenant.user_id,
        ))

    await db.flush()
    await db.commit()
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _row(db, lease)


# ── Régularisation des charges (Étape 3) ─────────────────────────────────────────
def _default_charge_period() -> tuple[date, date]:
    """Période par défaut : les 12 derniers mois civils complets (fin = dernier
    jour du mois précédent)."""
    today = date.today()
    first_this_month = today.replace(day=1)
    end = first_this_month - timedelta(days=1)  # dernier jour du mois précédent
    # Premier jour, 12 mois inclusifs → 11 mois avant le mois de `end`
    sy, sm = end.year, end.month - 11
    while sm <= 0:
        sm += 12
        sy -= 1
    start = date(sy, sm, 1)
    return start, end


async def _charge_row(db: AsyncSession, lease: Lease) -> dict:
    prop = lease.parent_property
    start, end = _default_charge_period()
    provisions = await ChargeRegularizationService.provisions_paid(db, lease.id, start, end)
    last = (await db.execute(
        select(ChargeRegularization)
        .where(ChargeRegularization.lease_id == lease.id)
        .order_by(ChargeRegularization.applied_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    # Réévaluation de charges déjà programmée (non appliquée) → visible sur la ligne.
    from app.services.rent_revision_service import RentRevisionService
    revs = await RentRevisionService.list_for_lease(db, lease.id)
    today = date.today()
    pend = next((r for r in revs if r.kind == "charges" and not r.applied and r.effective_date > today), None)
    return {
        "lease_id": str(lease.id),
        "tenant_full_name": lease.tenant.full_name if lease.tenant else "",
        "property_name": prop.name if prop else "",
        "owner_id": str(prop.owner_id) if prop and prop.owner_id else None,
        "owner_name": (prop.owner_name if prop else None) or "Sans propriétaire",
        "current_monthly_provision": float(lease.charges_amount),
        "default_period_start": start.isoformat(),
        "default_period_end": end.isoformat(),
        "provisions_paid_12m": provisions,
        "pending_charges": float(pend.amount) if pend else None,
        "pending_charges_id": str(pend.id) if pend else None,
        "pending_charges_date": pend.effective_date.isoformat() if pend else None,
        "last_regularization": None if not last else {
            "id": str(last.id),
            "period_start": last.period_start.isoformat(),
            "period_end": last.period_end.isoformat(),
            "provisions_total": float(last.provisions_total),
            "real_total": float(last.real_total),
            "balance": float(last.balance),
            "new_monthly_provision": float(last.new_monthly_provision),
            "applied_at": last.applied_at.isoformat() if last.applied_at else None,
        },
    }


@router.get("/charges")
async def list_charges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    leases = await _scoped_active_leases(db, current_user)
    return [await _charge_row(db, l) for l in leases]


class ChargePreviewIn(BaseModel):
    period_start: date
    period_end: date
    real_total: float


@router.post("/charges/{lease_id}/preview")
async def preview_charge(
    lease_id: uuid.UUID,
    data: ChargePreviewIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="Période invalide (fin avant début)")
    return await ChargeRegularizationService.compute(
        db, lease, data.period_start, data.period_end, data.real_total
    )


class ChargeApplyIn(BaseModel):
    period_start: date
    period_end: date
    real_total: float
    new_monthly_provision: float
    notes: Optional[str] = None
    effective_date: Optional[date] = None


@router.post("/charges/{lease_id}/appliquer")
async def apply_charge(
    lease_id: uuid.UUID,
    data: ChargeApplyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="Période invalide (fin avant début)")
    if data.real_total < 0 or data.new_monthly_provision < 0:
        raise HTTPException(status_code=400, detail="Montants négatifs invalides")
    await ChargeRegularizationService.apply(
        db, lease, data.period_start, data.period_end, data.real_total,
        data.new_monthly_provision, created_by=current_user.id, notes=data.notes,
        effective_date=data.effective_date,
    )
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _charge_row(db, lease)


class AmiableProvisionIn(BaseModel):
    new_provision: float
    effective_date: Optional[date] = None
    note: Optional[str] = None


@router.post("/charges/{lease_id}/reevaluation-amiable")
async def amiable_provision(
    lease_id: uuid.UUID,
    data: AmiableProvisionIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Réévalue la provision mensuelle pour charges d'un commun accord (hors régularisation)."""
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.models.tenant import Tenant

    if data.new_provision < 0:
        raise HTTPException(status_code=400, detail="Provision négative invalide")
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")

    from app.services.rent_revision_service import RentRevisionService, first_of_next_month
    old = float(lease.charges_amount)
    eff = data.effective_date or first_of_next_month(date.today())
    # Révision datée : le mois courant reste figé, l'ancienne provision en historique.
    await RentRevisionService.schedule(
        db, lease, kind="charges", new_amount=float(data.new_provision),
        effective_date=eff, source="amiable", reason=data.note or "Réévaluation amiable des charges",
        created_by=current_user.id,
    )

    tenant = await db.get(Tenant, lease.tenant_id)
    if tenant and tenant.user_id:
        msg = (f"Suite à votre accord, votre provision mensuelle pour charges est réévaluée : "
               f"{old:.2f} € → {float(data.new_provision):.2f} € à compter du {eff.strftime('%d/%m/%Y')}.")
        if data.note:
            msg += f" {data.note}"
        db.add(Notification(
            title="Réévaluation amiable de vos provisions pour charges",
            message=msg,
            notification_type=NotificationType.SYSTEME,
            priority=NotificationPriority.NORMAL,
            entity_type="lease", entity_id=lease.id, user_id=tenant.user_id,
        ))

    await db.flush()
    await db.commit()
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease_id)
    )).scalar_one()
    return await _charge_row(db, lease)


async def _get_regul_and_lease(db: AsyncSession, reg_id: uuid.UUID, current_user: User):
    reg = (await db.execute(
        select(ChargeRegularization).where(ChargeRegularization.id == reg_id)
    )).scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Régularisation introuvable")
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == reg.lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "cette régularisation")
    return reg, lease


@router.put("/charges/regularizations/{reg_id}")
async def update_charge_regularization(
    reg_id: uuid.UUID,
    data: ChargeApplyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="Période invalide (fin avant début)")
    if data.real_total < 0 or data.new_monthly_provision < 0:
        raise HTTPException(status_code=400, detail="Montants négatifs invalides")
    reg, lease = await _get_regul_and_lease(db, reg_id, current_user)
    await ChargeRegularizationService.update(
        db, reg, lease, data.period_start, data.period_end, data.real_total,
        data.new_monthly_provision, notes=data.notes,
    )
    lease = (await db.execute(
        select(Lease).options(selectinload(Lease.tenant), selectinload(Lease.parent_property))
        .where(Lease.id == lease.id)
    )).scalar_one()
    return await _charge_row(db, lease)


@router.delete("/charges/regularizations/{reg_id}", status_code=204)
async def delete_charge_regularization(
    reg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    reg, lease = await _get_regul_and_lease(db, reg_id, current_user)
    await ChargeRegularizationService.delete(db, reg, lease)


# ── Génération PDF (par blocs) ───────────────────────────────────────────────
def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/charges/regularizations/{reg_id}/pdf")
async def regularization_pdf(
    reg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """PDF de la régularisation de charges (par blocs)."""
    from app.services.document_blocks_pdf_service import ChargeRegularizationPDFService
    reg, _lease = await _get_regul_and_lease(db, reg_id, current_user)
    pdf = await ChargeRegularizationPDFService.generate(db, reg)
    return _pdf_response(pdf, f"regularisation_charges_{reg_id}.pdf")


@router.get("/loyers/{lease_id}/revision-pdf")
async def revision_pdf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """PDF de révision de loyer (IRL, par blocs)."""
    from app.services.document_blocks_pdf_service import RevisionLoyerPDFService
    lease = (await db.execute(select(Lease).where(Lease.id == lease_id))).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    if not lease.irl_quarter or lease.irl_base_index is None:
        raise HTTPException(status_code=400, detail="Indice IRL de référence non renseigné sur ce bail")
    pdf = await RevisionLoyerPDFService.generate(db, lease)
    return _pdf_response(pdf, f"revision_loyer_{lease_id}.pdf")


class TaxesPdfIn(BaseModel):
    lease_id: uuid.UUID
    year: int
    teom_amount: float


@router.post("/taxes/pdf")
async def taxes_pdf(
    data: TaxesPdfIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """PDF de décompte de taxes foncières (TEOM) — saisie ponctuelle."""
    from app.services.document_blocks_pdf_service import TaxesFoncieresPDFService
    if data.teom_amount < 0:
        raise HTTPException(status_code=400, detail="Montant négatif invalide")
    lease = (await db.execute(select(Lease).where(Lease.id == data.lease_id))).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    await assert_manager_scope(db, current_user, lease.created_by, "ce contrat")
    pdf = await TaxesFoncieresPDFService.generate(db, lease, data.year, data.teom_amount)
    return _pdf_response(pdf, f"taxes_foncieres_{data.year}.pdf")
