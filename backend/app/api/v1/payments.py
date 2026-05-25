import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import Role
from app.api.deps import require_role, get_current_gestionnaire, get_current_user
from app.models.user import User
from app.services import audit_service
from app.models.payment import PaymentStatus
from app.schemas.payment import (
    PaymentCreate,
    PaymentRecordIn,
    PaymentUpdate,
    PaymentResponse,
    PaymentListItem,
    PaymentListResponse,
    DashboardStats,
    MonthlyStats,
    GenerateMonthlyIn,
)
from app.services.payment_service import PaymentService
from app.services.pdf_service import render_template, html_to_pdf
from app.api.deps import get_current_user as _get_current_user
from app.api.v1._isolation import gp_lease_ids
# Allow import from auth for backward compatibility
get_current_user = _get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Routes statiques (doivent être enregistrées AVANT les routes paramétrées) ──

@router.get("/stats/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await PaymentService.get_dashboard_stats(db)


@router.get("/stats/monthly", response_model=MonthlyStats)
async def get_monthly_stats(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await PaymentService.get_monthly_stats(db, year, month)


@router.post("/generate", status_code=201)
async def generate_monthly_payments(
    data: GenerateMonthlyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    prop_ids_filter = None
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        from app.models.property import Property
        from sqlalchemy import select as sa_select
        res = await db.execute(
            sa_select(Property.id).where(Property.created_by == current_user.id)
        )
        prop_ids_filter = list(res.scalars().all())

    count = await PaymentService.generate_monthly(
        db, data.year, data.month, current_user.id, property_ids=prop_ids_filter
    )
    await db.commit()
    return {"generated": count, "year": data.year, "month": data.month}


@router.get("/locataire/current", summary="Paiement du mois courant (locataire)")
async def locataire_current_payment(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.payment import Payment as PaymentModel

    tenant_res = await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        return {"payment": None, "tenant": None}

    from sqlalchemy.orm import selectinload
    from app.models.lease import Lease
    result = await db.execute(
        select(PaymentModel)
        .options(
            selectinload(PaymentModel.tenant),
            selectinload(PaymentModel.unit),
            selectinload(PaymentModel.lease).selectinload(Lease.parent_property),
        )
        .where(PaymentModel.tenant_id == tenant.id)
        .where(PaymentModel.status.in_(["pending", "partial", "late"]))
        .order_by(PaymentModel.period_year.desc(), PaymentModel.period_month.desc())
        .limit(1)
    )
    payment = result.scalar_one_or_none()
    return {
        "payment": PaymentService.to_list_item(payment).__dict__ if payment else None,
        "tenant_name": tenant.full_name,
    }


@router.post("/locataire/declare", status_code=201, summary="Déclarer un paiement (locataire)")
async def locataire_declare_payment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService

    tenant_res = await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        from app.core.exceptions import BadRequestException
        raise BadRequestException("Profil locataire introuvable")

    method_labels = {
        "carte": "Carte bancaire",
        "virement": "Virement bancaire",
        "prelevement": "Prélèvement automatique",
        "cheque": "Chèque",
        "especes": "Espèces",
    }
    method = data.get("method", "virement")
    amount = data.get("amount", 0)
    label = method_labels.get(method, method)

    notif = NotificationCreate(
        title=f"Déclaration de paiement — {tenant.full_name}",
        message=f"{tenant.full_name} a déclaré un paiement de {amount} € par {label}. Veuillez valider le règlement.",
        notification_type=NotificationType.PAIEMENT_RECU,
        priority=NotificationPriority.HIGH,
        user_id=None,
    )
    await NotificationService.create(db, notif)
    await db.commit()
    return {"status": "declared", "method": method}


# ── Routes liste / création ────────────────────────────────────────────────────

@router.get("", response_model=PaymentListResponse)
async def list_payments(
    search: Optional[str] = Query(None),
    lease_id: Optional[uuid.UUID] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste les paiements.
    - Gestionnaire/Admin : tous les paiements
    - Propriétaire : paiements de ses biens
    - Locataire : uniquement ses paiements
    """
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.property import Property
    from app.models.unit import Unit
    from app.models.lease import Lease

    role = Role(current_user.role)

    # ── Locataire ─────────────────────────────────────────────────────────────
    if role == Role.LOCATAIRE:
        t = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not t:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        tenant_id = t.id

    # ── Propriétaire / Gestionnaire-Propriétaire ──────────────────────────────
    elif role in (Role.PROPRIETAIRE, Role.GESTIONNAIRE_PROPRIO):
        props = (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()
        prop_ids = [p.id for p in props]
        if not prop_ids:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        units = (await db.execute(
            select(Unit).where(Unit.property_id.in_(prop_ids))
        )).scalars().all()
        unit_ids = [u.id for u in units]
        leases = (await db.execute(
            select(Lease).where(Lease.unit_id.in_(unit_ids))
        )).scalars().all()
        lease_ids = [l.id for l in leases]
        if not lease_ids:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        # Pour chaque bail du proprio, récupérer les paiements
        all_items = []
        for lid in lease_ids:
            page, _ = await PaymentService.list_all(
                db, lease_id=lid, status=status, year=year, month=month,
                skip=0, limit=200
            )
            all_items.extend(page)
        list_items = [PaymentService.to_list_item(p) for p in all_items]
        return PaymentListResponse(items=list_items, total=len(list_items), skip=0, limit=limit)

    # Gestionnaire mandataire : exclure les paiements des baux GP
    if Role(current_user.role) == Role.GESTIONNAIRE:
        excluded = await gp_lease_ids(db)
        if lease_id and lease_id in excluded:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        all_items, _ = await PaymentService.list_all(
            db, search=search, lease_id=lease_id, tenant_id=tenant_id,
            status=status, year=year, month=month, skip=0, limit=5000,
        )
        filtered = [p for p in all_items if p.lease_id not in excluded]
        page = filtered[skip: skip + limit]
        return PaymentListResponse(
            items=[PaymentService.to_list_item(p) for p in page],
            total=len(filtered), skip=skip, limit=limit,
        )

    items, total = await PaymentService.list_all(
        db,
        search=search,
        lease_id=lease_id,
        tenant_id=tenant_id,
        status=status,
        year=year,
        month=month,
        skip=skip,
        limit=limit,
    )
    list_items = [PaymentService.to_list_item(p) for p in items]
    return PaymentListResponse(items=list_items, total=total, skip=skip, limit=limit)


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    from app.models.lease import Lease
    lease = await db.get(Lease, data.lease_id)
    if not lease:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Bail introuvable")
    payment = await PaymentService.generate_for_lease(
        db, lease, data.period_year, data.period_month, current_user.id
    )
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


# ── Routes paramétrées /{payment_id} ──────────────────────────────────────────

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await PaymentService.get_by_id(db, payment_id, load_relations=True)


@router.delete("/{payment_id}", status_code=204)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Supprime définitivement un paiement."""
    await PaymentService.delete_payment(db, payment_id)
    await db.commit()


@router.post("/{payment_id}/record", response_model=PaymentResponse)
async def record_payment(
    payment_id: uuid.UUID,
    data: PaymentRecordIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.COMPTABLE)),
):
    payment = await PaymentService.record_payment(db, payment_id, data)
    await audit_service.log(
        db, action=audit_service.PAYMENT_RECORD,
        user_id=current_user.id, user_email=current_user.email,
        entity_type="payment", entity_id=payment.id,
        details={"amount_paid": float(data.amount_paid), "method": data.payment_method},
    )
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    payment = await PaymentService.cancel_payment(db, payment_id)
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


@router.get("/{payment_id}/quittance")
async def download_quittance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    from app.models.tenant import Tenant as TenantModel
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)

    # Locataire : vérifier que c'est son propre paiement
    role = Role(current_user.role)
    if role == Role.LOCATAIRE:
        tenant_res = await db.execute(
            select(TenantModel).where(TenantModel.user_id == current_user.id)
        )
        tenant = tenant_res.scalar_one_or_none()
        if not tenant or payment.tenant_id != tenant.id:
            raise HTTPException(status_code=403, detail="Accès non autorisé")
    elif role not in (Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO, Role.PROPRIETAIRE, Role.LECTURE, Role.COMPTABLE):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    if payment.status not in (PaymentStatus.PAID, PaymentStatus.PARTIAL):
        from app.core.exceptions import BadRequestException
        raise BadRequestException("Impossible de générer une quittance pour un loyer non payé")

    # Marquer comme générée si c'est la première fois
    if not payment.quittance_generated_at:
        payment.quittance_generated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.commit()
        # Rechargement nécessaire : le commit expire tous les objets ORM
        payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)

    from datetime import date as _date
    from app.services.template_layout_service import get_layout
    _MONTHS_FR = ["janvier","février","mars","avril","mai","juin",
                  "juillet","août","septembre","octobre","novembre","décembre"]
    _d = _date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    html = render_template("quittance.html.j2", {
        "payment": payment,
        "today": today_fr,
        "layout": get_layout(),
    })
    pdf_bytes = html_to_pdf(html)

    tenant_name = (
        payment.tenant.full_name.replace(" ", "_") if payment.tenant else str(payment_id)
    )
    filename = f"quittance_{tenant_name}_{payment.period_year}_{payment.period_month:02d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{payment_id}/quittance/send")
async def send_quittance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Marque la quittance comme envoyée au locataire."""
    from fastapi import HTTPException
    try:
        payment = await PaymentService.send_quittance(db, payment_id)
        await db.commit()
        return {
            "id": str(payment.id),
            "quittance_generated_at": payment.quittance_generated_at,
            "quittance_sent_at": payment.quittance_sent_at,
        }
    except Exception as e:
        from app.core.exceptions import BadRequestException
        if "non payé" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise
