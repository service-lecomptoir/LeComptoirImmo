"""
API de génération de lettres et documents PDF.
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import require_role, Role
from app.models.user import User
from app.models.lease import LeaseType
from app.services.lease_service import LeaseService
from app.services.payment_service import PaymentService
from app.services.pdf_service import render_template, html_to_pdf
from app.core.exceptions import NotFoundException, BadRequestException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/letters", tags=["Letters"])

LEASE_TYPE_LABELS = {
    "vide": "Location vide (loi du 6 juillet 1989)",
    "meuble": "Location meublée",
    "mobilite": "Bail mobilité",
    "commercial": "Bail commercial",
}

MONTHS_FR = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _today_str() -> str:
    d = date.today()
    return f"{d.day} {MONTHS_FR[d.month]} {d.year}"


@router.get("/relance/{payment_id}")
async def lettre_relance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère une lettre de relance pour un loyer impayé."""
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if payment.status not in ("pending", "partial", "late"):
        raise BadRequestException("Ce loyer ne nécessite pas de relance")

    property_obj = payment.lease.parent_property if payment.lease else None
    apl_info = bool(payment.amount_apl)

    ctx = {
        "property_name": property_obj.name if property_obj else "Le bailleur",
        "property_address": property_obj.full_address if property_obj else "—",
        "city": (property_obj.city if property_obj else ""),
        "tenant_name": payment.tenant.full_name if payment.tenant else "—",
        "period_label": payment.period_label,
        "due_date": payment.due_date.strftime("%d/%m/%Y"),
        "amount_due": f"{payment.balance:.2f}",
        "apl_info": apl_info,
        "apl_amount": f"{float(payment.amount_apl):.2f}" if payment.amount_apl else "0.00",
        "today": _today_str(),
    }

    html = render_template("lettre_relance.html.j2", ctx)
    pdf = html_to_pdf(html)

    tenant_name = payment.tenant.full_name.replace(" ", "_") if payment.tenant else str(payment_id)
    filename = f"relance_{tenant_name}_{payment.period_year}_{payment.period_month:02d}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attestation-caf/{lease_id}")
async def attestation_caf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère une attestation de loyer pour la CAF."""
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)

    tenant = lease.tenant
    unit = lease.unit
    prop = lease.parent_property
    today = date.today()

    ctx = {
        "property_address": prop.full_address if prop else "—",
        "unit_ref": unit.unit_ref if unit else "—",
        "unit_type": unit.unit_type if unit else "—",
        "area_sqm": f"{float(unit.area_sqm):.0f}" if unit and unit.area_sqm else None,
        "tenant_name": tenant.full_name if tenant else "—",
        "tenant_birth_date": (
            tenant.birth_date.strftime("%d/%m/%Y") if tenant and tenant.birth_date else None
        ),
        "start_date": lease.start_date.strftime("%d/%m/%Y"),
        "lease_type_label": LEASE_TYPE_LABELS.get(lease.lease_type, lease.lease_type),
        "is_active": lease.is_active,
        "rent_amount": f"{float(lease.rent_amount):.2f}",
        "charges_amount": f"{float(lease.charges_amount):.2f}",
        "total_monthly": f"{lease.total_monthly:.2f}",
        "today": _today_str(),
    }

    html = render_template("attestation_caf.html.j2", ctx)
    pdf = html_to_pdf(html)

    tenant_name = tenant.full_name.replace(" ", "_") if tenant else str(lease_id)
    filename = f"attestation_caf_{tenant_name}_{today.year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
