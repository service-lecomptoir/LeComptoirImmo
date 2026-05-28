"""
API de génération de lettres et documents PDF.
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import Role
from app.api.deps import require_role
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
        "property_address": property_obj.full_address if property_obj else "",
        "city": (property_obj.city if property_obj else ""),
        "tenant_name": payment.tenant.full_name if payment.tenant else "",
        "period_label": payment.period_label,
        "due_date": payment.due_date.strftime("%d/%m/%Y"),
        "amount_due": f"{payment.balance:.2f}",
        "apl_info": apl_info,
        "apl_amount": f"{float(payment.amount_apl):.2f}" if payment.amount_apl else "0.00",
        "today": _today_str(),
    }

    html = render_template("lettre_relance.html.j2", ctx)
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "relance",
        tenant=payment.tenant.full_name if payment.tenant else None,
        property_name=property_obj.name if property_obj else None,
        month=payment.period_month,
        year=payment.period_year,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attestation-caf/{lease_id}")
async def attestation_caf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère une attestation de loyer pour la CAF."""
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)

    tenant = lease.tenant
    prop = lease.parent_property
    today = date.today()

    ctx = {
        "bailleur_name": current_user.full_name,
        "property_address": prop.full_address if prop else "",
        "property_city": prop.city if prop and prop.city else "",
        "unit_ref": prop.name if prop else "",
        "unit_type": prop.property_type if prop else "",
        "area_sqm": f"{float(prop.area_sqm):.0f}" if prop and prop.area_sqm else None,
        "tenant_name": tenant.full_name if tenant else "",
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

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "attestation_caf",
        tenant=tenant.full_name if tenant else None,
        property_name=prop.name if prop else None,
        year=today.year,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
