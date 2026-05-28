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
    from app.models.property import Property
    result = await db.execute(
        select(PaymentModel)
        .options(
            selectinload(PaymentModel.tenant),
            selectinload(PaymentModel.lease).selectinload(Lease.parent_property),
        )
        .where(PaymentModel.tenant_id == tenant.id)
        .where(PaymentModel.status.in_(["pending", "partial", "late"]))
        .order_by(PaymentModel.period_year.desc(), PaymentModel.period_month.desc())
        .limit(1)
    )
    payment = result.scalar_one_or_none()

    # ── Bénéficiaire = propriétaire / GP du bien loué (jamais le mandataire,
    #    qui ne reçoit pas les règlements à la place du propriétaire) ────────────
    #    Source UNIQUE des coordonnées de règlement : la fiche propriétaire (Owner),
    #    éditée soit par le gestionnaire (onglet Propriétaires) soit par le
    #    propriétaire lui-même (/profil → PATCH /owners/me). Fonctionne sans compte.
    payee = None
    prop = getattr(getattr(payment, "lease", None), "parent_property", None) if payment else None
    owner_id = getattr(prop, "owner_id", None) if prop else None
    if owner_id:
        from app.models.owner import Owner
        owner = (await db.execute(
            select(Owner).where(Owner.id == owner_id)
        )).scalar_one_or_none()
        if owner:
            payee = {
                "name": owner.bank_holder or owner.full_name,
                "address": owner.address,
                "iban": owner.iban,
                "bic": owner.bic,
            }

    return {
        "payment": PaymentService.to_list_item(payment).__dict__ if payment else None,
        "tenant_name": tenant.full_name,
        "payee": payee,
    }


@router.post("/locataire/declare", status_code=201, summary="Déclarer un paiement (locataire)")
async def locataire_declare_payment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le locataire déclare avoir payé son loyer (virement/espèces).
    On marque le paiement comme « déclaré, à valider » et on notifie le gestionnaire,
    qui devra valider le règlement pour qu'il soit enregistré."""
    from datetime import datetime as _dt, timezone as _tz
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.core.exceptions import BadRequestException, NotFoundException

    tenant_res = await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise BadRequestException("Profil locataire introuvable")

    method_labels = {
        "virement": "Virement bancaire",
        "especes": "Espèces",
    }
    method = data.get("method", "virement")
    payment_id = data.get("payment_id")
    if not payment_id:
        raise BadRequestException("Paiement non précisé")

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if payment.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    if payment.status == PaymentStatus.PAID:
        raise BadRequestException("Ce loyer est déjà réglé")

    amount = data.get("amount") or float(payment.balance)
    label = method_labels.get(method, method)

    # Marque le paiement comme déclaré (à valider par le gestionnaire)
    payment.declared_at = _dt.now(_tz.utc)
    payment.declared_method = method
    payment.declared_amount = amount

    # Notifie le gestionnaire en charge du bail (created_by), liée au paiement
    manager_id = getattr(payment.lease, "created_by", None) if payment.lease else None
    notif = Notification(
        title=f"Paiement à valider — {tenant.full_name}",
        message=(
            f"{tenant.full_name} a déclaré avoir réglé le loyer de {payment.period_label} "
            f"({amount:.2f} € par {label}). Validez le règlement pour l'enregistrer."
        ),
        notification_type=NotificationType.PAIEMENT_RECU,
        priority=NotificationPriority.HIGH,
        entity_type="payment",
        entity_id=payment.id,
        user_id=manager_id,
    )
    db.add(notif)
    await db.flush()
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
        leases = (await db.execute(
            select(Lease).where(Lease.property_id.in_(prop_ids))
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


@router.post("/{payment_id}/validate-declaration", response_model=PaymentResponse)
async def validate_declaration(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.COMPTABLE)),
):
    """Valide la déclaration de paiement faite par le locataire → enregistre l'encaissement."""
    from datetime import date as _date
    from sqlalchemy import select as _select
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.models.tenant import Tenant as _Tenant
    from app.core.exceptions import BadRequestException

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if not payment.declared_at:
        raise BadRequestException("Aucune déclaration de paiement à valider pour ce loyer")

    amount = float(payment.declared_amount) if payment.declared_amount else float(payment.balance)
    method = payment.declared_method or "virement"

    payment = await PaymentService.record_payment(
        db, payment_id,
        PaymentRecordIn(amount_paid=amount, payment_date=_date.today(), payment_method=method),
    )
    # Déclaration consommée
    payment.declared_at = None
    payment.declared_method = None
    payment.declared_amount = None

    # Notifie le locataire que son règlement est validé
    tenant = (await db.execute(
        _select(_Tenant).where(_Tenant.id == payment.tenant_id)
    )).scalar_one_or_none()
    if tenant and tenant.user_id:
        db.add(Notification(
            title="Paiement validé",
            message=(
                f"Votre règlement du loyer de {payment.period_label} a été validé "
                f"par votre gestionnaire. Votre quittance est disponible."
            ),
            notification_type=NotificationType.PAIEMENT_RECU,
            priority=NotificationPriority.NORMAL,
            entity_type="payment",
            entity_id=payment.id,
            user_id=tenant.user_id,
        ))

    await audit_service.log(
        db, action=audit_service.PAYMENT_RECORD,
        user_id=current_user.id, user_email=current_user.email,
        entity_type="payment", entity_id=payment.id,
        details={"amount_paid": amount, "method": method, "validated_declaration": True},
    )
    await db.flush()
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


@router.post("/{payment_id}/refuse-declaration", response_model=PaymentResponse)
async def refuse_declaration(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.COMPTABLE)),
):
    """Refuse la déclaration de paiement faite par le locataire (le règlement n'est
    pas enregistré ; le locataire est invité à reprendre contact)."""
    from sqlalchemy import select as _select
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.models.tenant import Tenant as _Tenant
    from app.core.exceptions import BadRequestException

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if not payment.declared_at:
        raise BadRequestException("Aucune déclaration de paiement à refuser pour ce loyer")

    payment.declared_at = None
    payment.declared_method = None
    payment.declared_amount = None

    tenant = (await db.execute(
        _select(_Tenant).where(_Tenant.id == payment.tenant_id)
    )).scalar_one_or_none()
    if tenant and tenant.user_id:
        db.add(Notification(
            title="Déclaration de paiement refusée",
            message=(
                f"Votre déclaration de paiement du loyer de {payment.period_label} "
                f"n'a pas été validée par votre gestionnaire. Merci de le contacter."
            ),
            notification_type=NotificationType.PAIEMENT_RECU,
            priority=NotificationPriority.HIGH,
            entity_type="payment",
            entity_id=payment.id,
            user_id=tenant.user_id,
        ))

    await db.flush()
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

    # Noms de tous les locataires : principal puis co-titulaires, chacun sur sa ligne.
    names: list[str] = []
    if getattr(payment, "lease_id", None):
        from sqlalchemy import select as _select
        from sqlalchemy.orm import selectinload as _selectinload
        from app.models.lease import Lease as _Lease
        _lease_obj = (await db.execute(
            _select(_Lease)
            .options(_selectinload(_Lease.tenant), _selectinload(_Lease.co_tenants))
            .where(_Lease.id == payment.lease_id)
        )).scalar_one_or_none()
        if _lease_obj:
            try:
                names = [t.full_name for t in _lease_obj.all_tenants]
            except Exception:
                names = []
    if not names and payment.tenant:
        names = [payment.tenant.full_name]
    tenant_names = " & ".join(names)
    layout = get_layout()

    # 1) Template ENREGISTRÉ par le gestionnaire (éditeur) si présent…
    from app.services.document_render_service import render_saved_document, eur
    _prop_obj = (payment.lease.parent_property
                 if getattr(payment, "lease", None) and getattr(payment.lease, "parent_property", None)
                 else None)
    _gid = getattr(payment.lease, "created_by", None) if getattr(payment, "lease", None) else None
    variables = {
        "tenant_name": " et ".join(names),
        "company_name": "",
        "property_name": _prop_obj.name if _prop_obj else "",
        "unit_ref": _prop_obj.name if _prop_obj else "",
        "property_address": _prop_obj.full_address if _prop_obj else "",
        "amount_paid": eur(payment.amount_paid),
        "rent_amount": eur(payment.amount_rent),
        "charges_amount": eur(payment.amount_charges),
        "apl_amount": eur(payment.amount_apl) if payment.amount_apl else "",
        "month": payment.period_label,
        "date": today_fr,
    }
    custom = await render_saved_document(
        db, template_type="quittance", gestionnaire_id=_gid,
        variables=variables, recipient_lines=names, layout=layout,
    )
    if custom:
        pdf_bytes = html_to_pdf(custom)
    else:
        # 2) …sinon, modèle .j2 historique (mise en page complète).
        html = render_template("quittance.html.j2", {
            "payment": payment,
            "today": today_fr,
            "tenant_names": tenant_names,
            "tenant_names_list": names,
            "layout": layout,
        })
        pdf_bytes = html_to_pdf(html)

    from app.utils.filename import doc_filename
    _prop = (payment.lease.parent_property.name
             if getattr(payment, "lease", None) and getattr(payment.lease, "parent_property", None)
             else None)
    filename = doc_filename(
        "quittance",
        tenant=payment.tenant.full_name if payment.tenant else None,
        property_name=_prop,
        month=payment.period_month,
        year=payment.period_year,
    )
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
