import uuid
import calendar
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.models.user import User
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.apurement_plan import ApurementPlan
from app.services.payment_service import PaymentService
from app.services.apurement_plan_service import ApurementPlanService, plan_to_dict
from app.api.v1._isolation import (
    assert_payment_access, assert_lease_access, agency_tenant_ids,
)
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.features import require_feature
from app.schemas.apurement_plan import ApurementPlanCreate, InstallmentMark

router = APIRouter(prefix="/apurement-plans", tags=["Apurement"])


def _add_months(d: date, m: int) -> date:
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


async def _lease_for_access(db: AsyncSession, lease_id):
    """Charge le bail AVEC parent_property et tenant : `assert_lease_access` lit ces
    relations, qui doivent être eager-loadées (sinon lazy-load sync → MissingGreenlet)."""
    return (await db.execute(
        select(Lease).options(selectinload(Lease.parent_property), selectinload(Lease.tenant))
        .where(Lease.id == lease_id)
    )).scalar_one_or_none()


async def _names(db: AsyncSession, plan) -> tuple:
    tenant = await db.get(Tenant, plan.tenant_id)
    lease = await db.get(Lease, plan.lease_id)
    prop = None
    if lease and getattr(lease, "property_id", None):
        prop = await db.get(Property, lease.property_id)
    return (getattr(tenant, "full_name", None), getattr(prop, "name", None))


@router.post("", summary="Créer un plan d'apurement depuis un loyer impayé")
async def create_plan(
    data: ApurementPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    payment = await PaymentService.get_by_id(db, data.payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    if payment.status not in ("pending", "partial", "late"):
        raise BadRequestException("Ce loyer ne nécessite pas de plan d'apurement")

    n = max(1, min(int(data.installments or 1), 36))
    total = round(float(payment.balance or 0), 2)
    base = round(total / n, 2)
    insts = []
    for i in range(n):
        due = _add_months(data.first_date, i)
        amount = base if i < n - 1 else round(total - base * (n - 1), 2)
        insts.append({
            "seq": i + 1, "due_date": due.isoformat(),
            "amount": amount, "paid": False, "paid_date": None,
        })

    plan = await ApurementPlanService.create(
        db, lease_id=payment.lease_id, tenant_id=payment.tenant_id,
        origin_payment_id=payment.id, total=total, installments=insts,
        created_by=current_user.id, label=f"Plan d'apurement · {payment.period_label}",
    )

    # Le mois d'origine est REPORTÉ sur le plan : il sort des impayés et des revenus
    # (statut « cancelled »), sa dette vit désormais dans les échéances. Le drapeau
    # permet d'afficher « Reporté » et de restaurer la dette si le plan est supprimé.
    from app.models.payment import PaymentStatus
    payment.status = PaymentStatus.CANCELLED
    payment.settled_by_plan = True
    _note = (payment.notes or "").strip()
    if "plan d'apurement" not in _note.lower():
        payment.notes = (f"{_note} · Reporté sur plan d'apurement").strip(" ·")
    await db.flush()

    tn, pn = await _names(db, plan)
    return plan_to_dict(plan, tn, pn)


@router.get("/mine", summary="Mes plans d'apurement (locataire)")
async def my_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = (await db.execute(
        select(Tenant).where(Tenant.user_id == current_user.id)
    )).scalar_one_or_none()
    if not t:
        return []
    plans = await ApurementPlanService.list_for_tenant(db, t.id)
    out = []
    for p in plans:
        tn, pn = await _names(db, p)
        out.append(plan_to_dict(p, tn, pn))
    return out


@router.get("/active", summary="Plans d'apurement actifs (gestionnaire)")
async def active_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    role = Role(current_user.role)
    if role == Role.ADMIN:
        plans = list((await db.execute(
            select(ApurementPlan).where(ApurementPlan.status == "active")
            .order_by(ApurementPlan.created_at.desc())
        )).scalars().all())
    else:
        allowed = await agency_tenant_ids(db, current_user)
        plans = await ApurementPlanService.list_active_for_tenants(db, allowed)
    out = []
    for p in plans:
        tn, pn = await _names(db, p)
        out.append(plan_to_dict(p, tn, pn))
    return out


@router.get("", summary="Plans d'apurement d'un locataire")
async def list_plans(
    tenant_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = Role(current_user.role)
    if role == Role.LOCATAIRE:
        t = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not t or t.id != tenant_id:
            return []
    elif role in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        if tenant_id not in await agency_tenant_ids(db, current_user):
            return []
    # admin : accès complet
    plans = await ApurementPlanService.list_for_tenant(db, tenant_id)
    out = []
    for p in plans:
        tn, pn = await _names(db, p)
        out.append(plan_to_dict(p, tn, pn))
    return out


@router.patch("/{plan_id}/installments/{seq}", summary="Pointer une échéance (payée/non)")
async def mark_installment(
    plan_id: uuid.UUID,
    seq: int,
    data: InstallmentMark,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    plan = await ApurementPlanService.get(db, plan_id)
    if not plan:
        raise NotFoundException("Plan d'apurement", str(plan_id))
    lease = await _lease_for_access(db, plan.lease_id)
    await assert_lease_access(db, current_user, lease, write=True)
    plan, found = await ApurementPlanService.mark_installment(
        db, plan, seq, data.paid, data.paid_date)
    if not found:
        raise BadRequestException("Échéance introuvable")
    tn, pn = await _names(db, plan)
    return plan_to_dict(plan, tn, pn)


@router.post("/{plan_id}/installments/{seq}/declare", summary="Locataire : déclarer le paiement d'une échéance")
async def declare_installment(
    plan_id: uuid.UUID,
    seq: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await ApurementPlanService.get(db, plan_id)
    if not plan:
        raise NotFoundException("Plan d'apurement", str(plan_id))
    # Le locataire ne peut déclarer que sur SON plan.
    t = (await db.execute(
        select(Tenant).where(Tenant.user_id == current_user.id)
    )).scalar_one_or_none()
    if not t or t.id != plan.tenant_id:
        raise BadRequestException("Ce plan d'apurement ne vous concerne pas.")
    plan, found = await ApurementPlanService.declare_installment(db, plan, seq)
    if not found:
        raise BadRequestException("Échéance introuvable")
    # Notifie le gestionnaire pour validation (best-effort).
    try:
        from app.models.notification import Notification, NotificationType, NotificationPriority
        manager_id = plan.created_by
        if not manager_id:
            manager_id = getattr(t, "created_by", None)
        inst = next((i for i in (plan.installments or []) if int(i.get("seq", -1)) == int(seq)), None)
        amt = float(inst.get("amount", 0)) if inst else 0
        if manager_id:
            db.add(Notification(
                title="Échéance d'apurement déclarée payée",
                message=f"{t.full_name} déclare avoir réglé une échéance de {amt:.2f} € de son plan d'apurement. À valider.",
                notification_type=NotificationType.SYSTEME, priority=NotificationPriority.NORMAL,
                entity_type="apurement_plan", entity_id=plan.id, user_id=manager_id,
            ))
    except Exception:  # noqa: BLE001
        pass
    tn, pn = await _names(db, plan)
    return plan_to_dict(plan, tn, pn)


@router.delete("/{plan_id}", status_code=204, summary="Supprimer un plan d'apurement")
async def delete_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    plan = await ApurementPlanService.get(db, plan_id)
    if not plan:
        raise NotFoundException("Plan d'apurement", str(plan_id))
    lease = await _lease_for_access(db, plan.lease_id)
    await assert_lease_access(db, current_user, lease, write=True)

    # Suppression du plan → la dette revient sur le mois d'origine (statut restauré).
    if plan.origin_payment_id:
        from app.models.payment import Payment, PaymentStatus
        pay = await db.get(Payment, plan.origin_payment_id)
        if pay is not None and getattr(pay, "settled_by_plan", False):
            pay.settled_by_plan = False
            paid = float(pay.amount_paid or 0)
            due = float(pay.amount_due or 0)
            if due > 0 and paid >= due:
                pay.status = PaymentStatus.PAID
            elif paid > 0:
                pay.status = PaymentStatus.PARTIAL
            else:
                pay.status = (PaymentStatus.LATE
                              if pay.due_date and pay.due_date < date.today()
                              else PaymentStatus.PENDING)
            if pay.notes:
                pay.notes = pay.notes.replace("· Reporté sur plan d'apurement", "").strip(" ·") or None
            await db.flush()

    await ApurementPlanService.delete(db, plan)


@router.get("/{plan_id}/pdf", summary="PDF du plan d'apurement")
async def plan_pdf(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await ApurementPlanService.get(db, plan_id)
    if not plan:
        raise NotFoundException("Plan d'apurement", str(plan_id))
    lease = await _lease_for_access(db, plan.lease_id)
    await assert_lease_access(db, current_user, lease)

    payment = None
    if plan.origin_payment_id:
        try:
            payment = await PaymentService.get_by_id(db, plan.origin_payment_id, load_relations=True)
        except Exception:
            payment = None
    if payment is None:
        raise BadRequestException("Document indisponible (paiement d'origine introuvable)")

    def _fr(iso: str) -> str:
        try:
            return date.fromisoformat(iso).strftime("%d/%m/%Y")
        except Exception:
            return iso

    schedule = [{"due": _fr(i["due_date"]), "amount": float(i["amount"])}
                for i in (plan.installments or [])]

    from app.services.pdf_service import render_plan_apurement_html, html_to_pdf
    html = await render_plan_apurement_html(db, payment, len(schedule), date.today(), schedule=schedule)
    if not html:
        raise BadRequestException("Modèle de plan d'apurement indisponible")
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    prop = await db.get(Property, lease.property_id) if lease and lease.property_id else None
    tenant = await db.get(Tenant, plan.tenant_id)
    filename = doc_filename(
        "plan_apurement",
        tenant=getattr(tenant, "full_name", None),
        property_name=getattr(prop, "name", None),
    )
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{plan_id}/installments/{seq}/quittance",
            summary="Quittance dédiée d'une échéance réglée")
async def installment_quittance(
    plan_id: uuid.UUID,
    seq: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _feat: User = Depends(require_feature("quittances")),
):
    plan = await ApurementPlanService.get(db, plan_id)
    if not plan:
        raise NotFoundException("Plan d'apurement", str(plan_id))
    lease = await _lease_for_access(db, plan.lease_id)
    await assert_lease_access(db, current_user, lease)  # lecture (locataire / gestionnaire)
    inst = next((i for i in (plan.installments or []) if int(i.get("seq", -1)) == int(seq)), None)
    if not inst:
        raise BadRequestException("Échéance introuvable")
    if not inst.get("paid"):
        raise BadRequestException("La quittance n'est disponible qu'une fois l'échéance réglée.")

    _MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                  "août", "septembre", "octobre", "novembre", "décembre"]
    _d = date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    prop = getattr(lease, "parent_property", None)
    tenant = getattr(lease, "tenant", None)
    gid = getattr(lease, "created_by", None)
    amount = float(inst.get("amount", 0))
    label = f"Plan d'apurement · échéance {seq}"

    from app.services.document_blocks_pdf_service import (
        render_blocks_document, _doc_common_vars, _eur_sym)
    qv = _doc_common_vars(tenant, prop, today_fr)
    qv.update({
        "period_range": label, "month": label,
        "total_due": _eur_sym(amount), "rent_amount": _eur_sym(amount),
        "charges_amount": _eur_sym(0), "apl_amount": "",
    })
    line_items = [{
        "label": f"RÈGLEMENT — PLAN D'APUREMENT, ÉCHÉANCE {seq}",
        "appele": _eur_sym(amount), "regle": _eur_sym(amount),
    }]
    pdf = await render_blocks_document(db, gid, "quittance", qv, line_items=line_items)

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "quittance",
        tenant=getattr(tenant, "full_name", None),
        property_name=getattr(prop, "name", None),
    )
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
