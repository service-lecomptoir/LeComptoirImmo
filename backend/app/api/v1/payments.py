import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import require_role, Role
from app.models.user import User
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
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


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
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    count = await PaymentService.generate_monthly(db, data.year, data.month, current_user.id)
    await db.commit()
    return {"generated": count, "year": data.year, "month": data.month}


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
    _: User = Depends(require_role(Role.LECTURE)),
):
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


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.LECTURE)),
):
    return await PaymentService.get_by_id(db, payment_id, load_relations=True)


@router.post("/{payment_id}/record", response_model=PaymentResponse)
async def record_payment(
    payment_id: uuid.UUID,
    data: PaymentRecordIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.COMPTABLE)),
):
    payment = await PaymentService.record_payment(db, payment_id, data)
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
    _: User = Depends(require_role(Role.LECTURE)),
):
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if payment.status not in (PaymentStatus.PAID, PaymentStatus.PARTIAL):
        from app.core.exceptions import BadRequestException
        raise BadRequestException("Impossible de générer une quittance pour un loyer non payé")

    html = render_template("quittance.html.j2", {"payment": payment})
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
