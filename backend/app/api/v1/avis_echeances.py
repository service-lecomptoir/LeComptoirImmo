"""
API Avis d'échéances — Génération manuelle, automatique, listing, PDF.
"""
import uuid
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import Role
from app.models.user import User
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.avis_echeance import AvisEcheance
from app.services.avis_echeance_service import AvisEcheanceService
from app.schemas.avis_echeance import (
    AvisEcheanceGenerateIn,
    AvisEcheaneBulkGenerateIn,
    AvisEcheanceOut,
    AvisEcheanceSummary,
    GenerateMonthlyResult,
    AvisEcheancePatchApl,
)
from app.core.exceptions import ConflictException, NotFoundException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/avis-echeances", tags=["Avis d'échéances"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_manager(user: User) -> None:
    if user.role not in (Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")


def _avis_to_summary(avis: AvisEcheance) -> dict:
    months = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    return {
        "id": avis.id,
        "period_year": avis.period_year,
        "period_month": avis.period_month,
        "period_label": f"{months[avis.period_month]} {avis.period_year}",
        "due_date": avis.due_date,
        "amount_total": float(avis.amount_total),
        "amount_rent": float(avis.amount_rent),
        "amount_charges": float(avis.amount_charges),
        "amount_apl": float(avis.amount_apl) if avis.amount_apl else None,
        "status": avis.status,
        "sent_at": avis.sent_at,
        "is_auto_generated": avis.generated_by is None,
        "tenant_full_name": avis.tenant.full_name if avis.tenant else "",
        "unit_ref": avis.unit.unit_ref if avis.unit else "",
        "lease_id": avis.lease_id,
        "tenant_id": avis.tenant_id,
        "unit_id": avis.unit_id,
        "notes": avis.notes,
        "pdf_path": avis.pdf_path,
        "generated_by": avis.generated_by,
        "created_at": avis.created_at,
        "updated_at": avis.updated_at,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_avis(
    lease_id: Optional[uuid.UUID] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les avis d'échéances avec filtres.
    - Gestionnaire/Admin : tous les avis
    - Locataire : uniquement ses propres avis
    - Propriétaire : avis de ses biens
    """
    tenant_id_filter = None

    if current_user.role == Role.LOCATAIRE:
        # Le locataire ne voit que ses avis
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant:
            return []
        tenant_id_filter = tenant.id

    elif current_user.role in (Role.PROPRIETAIRE, Role.GESTIONNAIRE_PROPRIO):
        # Le propriétaire voit les avis de ses biens
        from app.models.property import Property
        from app.models.unit import Unit
        props = (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()
        prop_ids = [p.id for p in props]
        if not prop_ids:
            return []
        units = (await db.execute(
            select(Unit).where(Unit.property_id.in_(prop_ids))
        )).scalars().all()
        unit_ids = [u.id for u in units]
        leases = (await db.execute(
            select(Lease).where(Lease.unit_id.in_(unit_ids), Lease.is_active == True)
        )).scalars().all()
        lease_ids = [l.id for l in leases]
        if not lease_ids:
            return []
        # Filtrer sur lease_ids
        from sqlalchemy import select as sel
        q = sel(AvisEcheance)
        if lease_id:
            q = q.where(AvisEcheance.lease_id == lease_id)
        else:
            q = q.where(AvisEcheance.lease_id.in_(lease_ids))
        if year:
            q = q.where(AvisEcheance.period_year == year)
        if month:
            q = q.where(AvisEcheance.period_month == month)
        if status:
            q = q.where(AvisEcheance.status == status)
        from sqlalchemy.orm import selectinload
        q = q.options(
            selectinload(AvisEcheance.tenant),
            selectinload(AvisEcheance.unit),
            selectinload(AvisEcheance.lease),
        ).order_by(
            AvisEcheance.period_year.desc(),
            AvisEcheance.period_month.desc(),
        ).offset(skip).limit(limit)
        avis_list = (await db.execute(q)).scalars().all()
        return [_avis_to_summary(a) for a in avis_list]

    avis_list = await AvisEcheanceService.get_list(
        db,
        lease_id=lease_id,
        tenant_id=tenant_id_filter,
        year=year,
        month=month,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [_avis_to_summary(a) for a in avis_list]


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_one(
    body: AvisEcheanceGenerateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Génère manuellement un avis d'échéance pour un bail et une période."""
    _require_manager(current_user)

    lease = (await db.execute(
        select(Lease).where(Lease.id == body.lease_id)
    )).scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    if not lease.is_active:
        raise HTTPException(status_code=400, detail="Ce bail n'est plus actif")

    try:
        avis = await AvisEcheanceService.generate_for_lease(
            db, lease, body.period_year, body.period_month,
            generated_by=current_user.id,
            apl_override=body.apl_amount_override,
        )
        await db.commit()
        avis = await AvisEcheanceService.get_by_id(db, avis.id)
        return _avis_to_summary(avis)
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/generate-monthly")
async def generate_monthly(
    body: AvisEcheaneBulkGenerateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Génère les avis pour tous les baux actifs sur un mois donné."""
    _require_manager(current_user)

    count = await AvisEcheanceService.generate_monthly_all(
        db, body.period_year, body.period_month
    )
    await db.commit()

    months = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    return {
        "generated": count,
        "period_year": body.period_year,
        "period_month": body.period_month,
        "message": f"{count} avis générés pour {months[body.period_month]} {body.period_year}",
    }


@router.get("/{avis_id}")
async def get_avis(
    avis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Contrôle d'accès
    if current_user.role == Role.LOCATAIRE:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant or avis.tenant_id != tenant.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")

    return _avis_to_summary(avis)


@router.post("/{avis_id}/send")
async def mark_sent(
    avis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marque un avis comme envoyé."""
    _require_manager(current_user)
    try:
        avis = await AvisEcheanceService.mark_sent(db, avis_id)
        await db.commit()
        avis = await AvisEcheanceService.get_by_id(db, avis.id)
        return _avis_to_summary(avis)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{avis_id}/acquitter")
async def mark_acquitte(
    avis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marque un avis comme acquitté (loyer reçu)."""
    _require_manager(current_user)
    try:
        avis = await AvisEcheanceService.mark_acquitte(db, avis_id)
        await db.commit()
        avis = await AvisEcheanceService.get_by_id(db, avis.id)
        return _avis_to_summary(avis)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{avis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avis(
    avis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime un avis d'échéance (brouillon uniquement)."""
    _require_manager(current_user)
    try:
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
        if avis.status != "brouillon":
            raise HTTPException(
                status_code=400,
                detail="Seuls les brouillons peuvent être supprimés"
            )
        await AvisEcheanceService.delete(db, avis_id)
        await db.commit()
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{avis_id}/apl")
async def patch_apl(
    avis_id: uuid.UUID,
    body: AvisEcheancePatchApl,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modifie le montant APL d'un avis existant (recalcule total + paiement lié)."""
    _require_manager(current_user)
    try:
        avis = await AvisEcheanceService.update_apl(db, avis_id, body.apl_amount)
        await db.commit()
        avis = await AvisEcheanceService.get_by_id(db, avis.id)
        return _avis_to_summary(avis)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{avis_id}/pdf")
async def download_pdf(
    avis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Génère et retourne le PDF de l'avis d'échéance."""
    try:
        avis = await AvisEcheanceService.get_by_id(db, avis_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Contrôle d'accès locataire
    if current_user.role == Role.LOCATAIRE:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant or avis.tenant_id != tenant.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")

    from app.services.pdf_service import AvisEcheancePDFService
    from fastapi.responses import Response

    pdf_bytes = await AvisEcheancePDFService.generate(db, avis)
    months = ["", "janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    filename = f"avis-echeance-{months[avis.period_month]}-{avis.period_year}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
