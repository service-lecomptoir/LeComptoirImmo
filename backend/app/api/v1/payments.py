import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_user, require_role
from app.api.deps import get_current_user as _get_current_user
from app.api.v1._isolation import agency_lease_ids, assert_payment_access
from app.core.features import require_feature
from app.core.permissions import Role
from app.database import get_db
from app.models.payment import PaymentStatus
from app.models.user import User
from app.schemas.payment import (
    DashboardStats,
    GenerateMonthlyIn,
    MonthlyStats,
    PaymentCreate,
    PaymentListResponse,
    PaymentRecordIn,
    PaymentResponse,
)
from app.services import audit_service
from app.services.payment_service import PaymentService
from app.services.pdf_service import html_to_pdf, render_template

# Allow import from auth for backward compatibility
get_current_user = _get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Routes statiques (doivent être enregistrées AVANT les routes paramétrées) ──


def _stats_agency_only(current_user: User) -> None:
    """Stats globales (agence) : réservées admin + mandataire. Les GP/propriétaires
    disposent de tableaux de bord scopés (dashboard.py) : ces totaux globaux leur
    sont interdits pour ne pas révéler de chiffres hors périmètre."""
    if Role(current_user.role) not in (Role.ADMIN, Role.GESTIONNAIRE, Role.LECTURE, Role.COMPTABLE):
        from app.core.exceptions import ForbiddenException

        raise ForbiddenException("Statistiques globales non autorisées pour ce rôle.")


@router.get("/stats/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    _stats_agency_only(current_user)
    return await PaymentService.get_dashboard_stats(db)


@router.get("/stats/monthly", response_model=MonthlyStats)
async def get_monthly_stats(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.LECTURE)),
):
    _stats_agency_only(current_user)
    return await PaymentService.get_monthly_stats(db, year, month)


@router.post("/generate", status_code=201)
async def generate_monthly_payments(
    data: GenerateMonthlyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    prop_ids_filter = None
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        from sqlalchemy import select as sa_select

        from app.models.property import Property

        res = await db.execute(sa_select(Property.id).where(Property.created_by == current_user.id))
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
    from sqlalchemy import select

    from app.models.payment import Payment as PaymentModel
    from app.models.tenant import Tenant

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

        owner = (await db.execute(select(Owner).where(Owner.id == owner_id))).scalar_one_or_none()
        if owner:
            payee = {
                "name": owner.bank_holder or owner.full_name,
                "address": owner.full_address,
                "iban": owner.iban,
                "bic": owner.bic,
            }

    return {
        "payment": PaymentService.to_list_item(payment).__dict__ if payment else None,
        "tenant_name": tenant.full_name,
        "payee": payee,
    }


@router.get("/locataire/regularizations", summary="Régularisations de charges (locataire)")
async def locataire_regularizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Régularisations annuelles de charges du locataire (solde créditeur/débiteur),
    pour affichage dans son grand livre « Ma comptabilité »."""
    from sqlalchemy import select

    from app.models.charge_regularization import ChargeRegularization
    from app.models.tenant import Tenant

    tenant = (
        await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    ).scalar_one_or_none()
    if not tenant:
        return []
    regs = (
        (
            await db.execute(
                select(ChargeRegularization)
                .where(ChargeRegularization.tenant_id == tenant.id)
                .order_by(ChargeRegularization.period_end.desc())
            )
        )
        .scalars()
        .all()
    )
    cache: dict = {}
    return [
        {
            "id": str(r.id),
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "balance": float(r.balance or 0),
            "applied_at": r.applied_at.isoformat() if r.applied_at else None,
        }
        for r in regs
        if await _deposit_on(db, r.created_by, "revision_charges", cache)
    ]


async def _current_tenant(db: AsyncSession, current_user: User):
    from sqlalchemy import select

    from app.models.tenant import Tenant

    return (
        await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    ).scalar_one_or_none()


async def _deposit_on(db: AsyncSession, manager_id, rule_type: str, cache: dict) -> bool:
    """Interrupteur « Déposer sur le compte locataire » (onglet Automatisation) du
    gestionnaire pour ce type de document. True par défaut (aucune règle = visible)."""
    if not manager_id:
        return True
    key = (str(manager_id), rule_type)
    if key in cache:
        return cache[key]
    from sqlalchemy import select

    from app.models.automation import AutomationRule

    val = (
        await db.execute(
            select(AutomationRule.auto_deposit)
            .where(
                AutomationRule.created_by == manager_id,
                AutomationRule.rule_type == rule_type,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    enabled = True if val is None else bool(val)
    cache[key] = enabled
    return enabled


@router.get(
    "/locataire/regularizations/{reg_id}/pdf", summary="Décompte de régularisation (locataire)"
)
async def locataire_regularization_pdf(
    reg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Décompte de régularisation de charges du locataire (généré à la volée)."""
    from app.core.exceptions import NotFoundException
    from app.models.charge_regularization import ChargeRegularization

    tenant = await _current_tenant(db, current_user)
    reg = await db.get(ChargeRegularization, reg_id) if tenant else None
    if reg is None or reg.tenant_id != tenant.id:
        raise NotFoundException("Régularisation introuvable")
    from app.services.document_blocks_pdf_service import ChargeRegularizationPDFService

    pdf = await ChargeRegularizationPDFService.generate(db, reg)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="regularisation-charges-{reg_id}.pdf"'
        },
    )


@router.get("/locataire/revisions", summary="Révisions de loyer IRL (locataire)")
async def locataire_revisions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Baux du locataire éligibles à un avis de révision de loyer IRL (indice
    de référence configuré). Une ligne par bail, document généré à la volée."""
    from sqlalchemy import select

    from app.models.lease import Lease
    from app.models.property import Property

    tenant = await _current_tenant(db, current_user)
    if not tenant:
        return []
    leases = (
        (
            await db.execute(
                select(Lease).where(Lease.tenant_id == tenant.id, Lease.irl_base_index.isnot(None))
            )
        )
        .scalars()
        .all()
    )
    out, cache = [], {}
    for l in leases:
        if not await _deposit_on(db, l.created_by, "revision_loyer", cache):
            continue
        prop = await db.get(Property, l.property_id) if l.property_id else None
        out.append(
            {
                "lease_id": str(l.id),
                "property_name": getattr(prop, "name", None),
                "last_revision_date": l.last_revision_date.isoformat()
                if l.last_revision_date
                else None,
            }
        )
    return out


@router.get("/locataire/revisions/{lease_id}/pdf", summary="Avis de révision IRL (locataire)")
async def locataire_revision_pdf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Avis de révision de loyer IRL du locataire (généré à la volée)."""
    from app.core.exceptions import NotFoundException
    from app.models.lease import Lease

    tenant = await _current_tenant(db, current_user)
    lease = await db.get(Lease, lease_id) if tenant else None
    if lease is None or lease.tenant_id != tenant.id:
        raise NotFoundException("Bail introuvable")
    from app.services.document_blocks_pdf_service import RevisionLoyerPDFService

    pdf = await RevisionLoyerPDFService.generate(db, lease)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="revision-loyer-{lease_id}.pdf"'},
    )


@router.get("/locataire/taxes", summary="Taxes d'ordures ménagères (locataire)")
async def locataire_taxes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Déclarations de TEOM du locataire (document généré à la volée)."""
    from sqlalchemy import select

    from app.models.taxe_declaration import TaxeDeclaration

    tenant = await _current_tenant(db, current_user)
    if not tenant:
        return []
    rows = (
        (
            await db.execute(
                select(TaxeDeclaration)
                .where(TaxeDeclaration.tenant_id == tenant.id)
                .order_by(TaxeDeclaration.year.desc())
            )
        )
        .scalars()
        .all()
    )
    cache: dict = {}
    return [
        {
            "id": str(t.id),
            "year": t.year,
            "amount": float(t.teom_amount or 0),
            "declared_at": t.declared_at.isoformat() if t.declared_at else None,
        }
        for t in rows
        if await _deposit_on(db, t.created_by, "taxe_om", cache)
    ]


@router.get("/locataire/taxes/{taxe_id}/pdf", summary="Décompte TEOM (locataire)")
async def locataire_taxe_pdf(
    taxe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.exceptions import NotFoundException
    from app.models.lease import Lease
    from app.models.taxe_declaration import TaxeDeclaration

    tenant = await _current_tenant(db, current_user)
    taxe = await db.get(TaxeDeclaration, taxe_id) if tenant else None
    if taxe is None or taxe.tenant_id != tenant.id:
        raise NotFoundException("Déclaration introuvable")
    lease = await db.get(Lease, taxe.lease_id)
    from app.services.document_blocks_pdf_service import TaxesFoncieresPDFService

    pdf = await TaxesFoncieresPDFService.generate(
        db, lease, taxe.year, float(taxe.teom_amount or 0)
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="taxe-ordures-{taxe.year}.pdf"'},
    )


def _payment_id_from_dedup(dedup: str | None):
    """Extrait l'UUID du paiement d'une clé de dédup de relance « type:payment:rule »."""
    if not dedup:
        return None
    parts = dedup.split(":")
    if len(parts) >= 2:
        try:
            return uuid.UUID(parts[1])
        except (ValueError, AttributeError):
            return None
    return None


@router.get("/locataire/relances", summary="Relances / rappels reçus (locataire)")
async def locataire_relances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lettres de relance / rappels envoyés au locataire (CommunicationLog),
    régénérables à la volée depuis le paiement concerné."""
    from sqlalchemy import select

    from app.models.automation import AutomationRule, CommunicationLog

    tenant = await _current_tenant(db, current_user)
    if not tenant:
        return []
    logs = (
        await db.execute(
            select(CommunicationLog, AutomationRule.rule_type, AutomationRule.auto_deposit)
            .join(AutomationRule, CommunicationLog.rule_id == AutomationRule.id)
            .where(
                CommunicationLog.tenant_id == tenant.id,
                CommunicationLog.status == "sent",
                AutomationRule.rule_type.in_(("rappel_impaye", "relance_1", "relance_2")),
            )
            .order_by(CommunicationLog.sent_at.desc())
        )
    ).all()
    out = []
    for log, rtype, deposit in logs:
        if not (deposit if deposit is not None else True):
            continue  # dépôt locataire désactivé pour ce type
        pid = _payment_id_from_dedup(log.dedup_key)
        if not pid:
            continue
        out.append(
            {
                "id": str(log.id),
                "payment_id": str(pid),
                "label": log.subject or "Relance de loyer",
                "rule_type": rtype,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            }
        )
    return out


@router.get("/locataire/relances/{payment_id}/pdf", summary="Lettre de relance (locataire)")
async def locataire_relance_pdf(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.exceptions import NotFoundException

    tenant = await _current_tenant(db, current_user)
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    if payment is None or not tenant or payment.tenant_id != tenant.id:
        raise NotFoundException("Relance introuvable")
    from app.services.pdf_service import build_relance_pdf, relance_filename

    pdf = await build_relance_pdf(db, payment)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{relance_filename(payment)}"'},
    )


@router.post("/locataire/declare", status_code=201, summary="Déclarer un paiement (locataire)")
async def locataire_declare_payment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le locataire déclare avoir payé son loyer (virement/espèces).
    On marque le paiement comme « déclaré, à valider » et on notifie le gestionnaire,
    qui devra valider le règlement pour qu'il soit enregistré."""
    from datetime import datetime as _dt

    from sqlalchemy import select

    from app.core.exceptions import BadRequestException
    from app.models.notification import Notification, NotificationPriority, NotificationType
    from app.models.tenant import Tenant

    tenant_res = await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise BadRequestException("Profil locataire introuvable")

    method_labels = {
        "virement": "Virement bancaire",
        "especes": "Espèces",
    }
    method = data.get("method", "virement")
    if method not in method_labels:
        raise BadRequestException("Mode de règlement non autorisé")
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
    payment.declared_at = _dt.now(UTC)
    payment.declared_method = method
    payment.declared_amount = amount

    # Notifie le gestionnaire en charge du bail (created_by), liée au paiement
    manager_id = getattr(payment.lease, "created_by", None) if payment.lease else None
    notif = Notification(
        title=f"Paiement à valider : {tenant.full_name}",
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

    # Push « Agent Comptable » : prévient spontanément le gestionnaire sur Telegram
    # (best-effort, non bloquant — n'affecte pas la déclaration déjà enregistrée).
    try:
        from app.services import agent_events

        await agent_events.notify_manager(
            db,
            manager_id,
            "paiement",
            f"{tenant.full_name} a déclaré avoir réglé le loyer de {payment.period_label} "
            f"({amount:.2f} € par {label}).",
            cta="Validez le règlement dans l'application pour l'enregistrer.",
        )
    except Exception:  # noqa: BLE001
        pass
    return {"status": "declared", "method": method}


# ── Routes liste / création ────────────────────────────────────────────────────


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    search: str | None = Query(None),
    lease_id: uuid.UUID | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    status: PaymentStatus | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
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

    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    role = Role(current_user.role)

    # ── Locataire ─────────────────────────────────────────────────────────────
    if role == Role.LOCATAIRE:
        t = (
            await db.execute(select(Tenant).where(Tenant.user_id == current_user.id))
        ).scalar_one_or_none()
        if not t:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        tenant_id = t.id

    # ── Propriétaire / Gestionnaire-Propriétaire ──────────────────────────────
    elif role in (Role.PROPRIETAIRE, Role.GESTIONNAIRE_PROPRIO):
        from sqlalchemy import or_

        # Le gestionnaire-propriétaire voit AUSSI les biens qu'il a créés (cohérent
        # avec l'isolation par created_by) : une fiche propriétaire sans compte de
        # connexion laisse owner_user_id NULL, sinon il ne verrait aucun paiement.
        owner_cond = Property.owner_user_id == current_user.id
        if role == Role.GESTIONNAIRE_PROPRIO:
            owner_cond = or_(owner_cond, Property.created_by == current_user.id)
        props = (await db.execute(select(Property).where(owner_cond))).scalars().all()
        prop_ids = [p.id for p in props]
        if not prop_ids:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        leases = (
            (await db.execute(select(Lease).where(Lease.property_id.in_(prop_ids)))).scalars().all()
        )
        lease_ids = [l.id for l in leases]
        if not lease_ids:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        # Pour chaque bail du proprio, récupérer les paiements
        all_items = []
        for lid in lease_ids:
            page, _ = await PaymentService.list_all(
                db, lease_id=lid, status=status, year=year, month=month, skip=0, limit=200
            )
            all_items.extend(page)
        list_items = [PaymentService.to_list_item(p) for p in all_items]
        return PaymentListResponse(items=list_items, total=len(list_items), skip=0, limit=limit)

    # Gestionnaire mandataire : uniquement les paiements des baux de SON agence
    if Role(current_user.role) == Role.GESTIONNAIRE:
        allowed = await agency_lease_ids(db, current_user)
        if lease_id and lease_id not in allowed:
            return PaymentListResponse(items=[], total=0, skip=skip, limit=limit)
        all_items, _ = await PaymentService.list_all(
            db,
            search=search,
            lease_id=lease_id,
            tenant_id=tenant_id,
            status=status,
            year=year,
            month=month,
            skip=0,
            limit=5000,
        )
        filtered = [p for p in all_items if p.lease_id in allowed]
        page = filtered[skip : skip + limit]
        return PaymentListResponse(
            items=[PaymentService.to_list_item(p) for p in page],
            total=len(filtered),
            skip=skip,
            limit=limit,
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


@router.get("/comptabilite", summary="Grand livre des transactions (gestionnaire)")
async def comptabilite_ledger(
    year: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toutes les transactions du périmètre du gestionnaire : appels de loyer,
    règlements, APL, échéances d'apurement, régularisations de charges.
    GP / propriétaire : son parc. GM (mandataire) + lecture/comptable : les baux
    de l'agence, avec le propriétaire en plus du logement."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.exceptions import ForbiddenException
    from app.models.apurement_plan import ApurementPlan
    from app.models.charge_regularization import ChargeRegularization
    from app.models.lease import Lease
    from app.models.payment import Payment as P
    from app.models.property import Property
    from app.models.tenant import Tenant

    role = Role(current_user.role)
    is_mandataire = role in (Role.GESTIONNAIRE, Role.LECTURE, Role.COMPTABLE)
    if is_mandataire:
        lease_ids = await agency_lease_ids(db, current_user)
    elif role in (Role.GESTIONNAIRE_PROPRIO, Role.PROPRIETAIRE):
        from sqlalchemy import or_

        owner_cond = Property.owner_user_id == current_user.id
        if role == Role.GESTIONNAIRE_PROPRIO:
            # Inclut les biens créés par le GP (fiche propriétaire sans compte →
            # owner_user_id NULL), cohérent avec l'isolation par created_by.
            owner_cond = or_(owner_cond, Property.created_by == current_user.id)
        prop_ids = (await db.execute(select(Property.id).where(owner_cond))).scalars().all()
        lease_ids = (
            set(
                (await db.execute(select(Lease.id).where(Lease.property_id.in_(prop_ids))))
                .scalars()
                .all()
            )
            if prop_ids
            else set()
        )
    else:
        raise ForbiddenException("Accès réservé au gestionnaire")

    if not lease_ids:
        return {"is_mandataire": is_mandataire, "entries": []}
    lease_ids = list(lease_ids)

    # Contexte par bail : logement (+ réf), propriétaire (dénormalisé), locataire.
    leases = (
        (
            await db.execute(
                select(Lease)
                .options(selectinload(Lease.parent_property), selectinload(Lease.tenant))
                .where(Lease.id.in_(lease_ids))
            )
        )
        .scalars()
        .all()
    )
    # Noms de propriétaires : repli sur la fiche Owner si le champ dénormalisé est vide.
    from app.models.owner import Owner as _Owner

    _oids = {getattr(getattr(l, "parent_property", None), "owner_id", None) for l in leases}
    _oids.discard(None)
    owners_by_id = {}
    if _oids:
        owners_by_id = {
            o.id: o
            for o in (await db.execute(select(_Owner).where(_Owner.id.in_(_oids)))).scalars().all()
        }
    ctx: dict = {}
    for l in leases:
        pr = getattr(l, "parent_property", None)
        _own = owners_by_id.get(getattr(pr, "owner_id", None)) if pr else None
        _own_name = ((getattr(pr, "owner_name", "") or "") if pr else "") or (
            getattr(_own, "full_name", "") or "" if _own else ""
        )
        ctx[l.id] = {
            "logement": (getattr(pr, "name", "") or "") if pr else "",
            "logement_ref": (getattr(pr, "ref_code", "") or "") if pr else "",
            "proprietaire": _own_name,
            "locataire": (getattr(getattr(l, "tenant", None), "full_name", "") or ""),
        }

    def _c(lid):
        return ctx.get(
            lid, {"logement": "", "logement_ref": "", "proprietaire": "", "locataire": ""}
        )

    def _r2(n):
        return round(n * 100) / 100

    entries: list = []

    payments = (
        (
            await db.execute(
                select(P).options(selectinload(P.tenant)).where(P.lease_id.in_(lease_ids))
            )
        )
        .scalars()
        .all()
    )
    for p in payments:
        if p.status == "cancelled" or getattr(p, "settled_by_plan", False):
            continue  # annulé / mois reporté (la dette vit dans le plan)
        c = dict(_c(p.lease_id))
        if getattr(p, "tenant", None):
            c["locataire"] = p.tenant.full_name or c["locataire"]
        due = float(p.amount_due or 0)
        apl = min(float(p.amount_apl or 0), due)
        reste = _r2(float(p.amount_paid or 0) - apl)
        dd = p.due_date.isoformat() if p.due_date else None
        entries.append(
            {
                **c,
                "date": dd,
                "intitule": f"Appel de loyer · {p.period_label}",
                "montant": due,
                "sign": "debit",
            }
        )
        if apl > 0.005:
            entries.append(
                {
                    **c,
                    "date": dd,
                    "intitule": f"Aide au logement (APL) · {p.period_label}",
                    "montant": apl,
                    "sign": "credit",
                }
            )
        if reste > 0.005:
            pd = p.payment_date or p.due_date
            entries.append(
                {
                    **c,
                    "date": pd.isoformat() if pd else None,
                    "intitule": f"Règlement · {p.period_label}",
                    "montant": reste,
                    "sign": "credit",
                }
            )
        # Part reportée sur un plan d'apurement (apurement partiel) : sort du solde
        # du mois (la dette correspondante figure dans les échéances du plan).
        on_plan = float(getattr(p, "amount_on_plan", 0) or 0)
        if on_plan > 0.005:
            entries.append(
                {
                    **c,
                    "date": dd,
                    "intitule": f"Report sur plan d'apurement · {p.period_label}",
                    "montant": on_plan,
                    "sign": "credit",
                }
            )

    plans = (
        (await db.execute(select(ApurementPlan).where(ApurementPlan.lease_id.in_(lease_ids))))
        .scalars()
        .all()
    )
    for pl in plans:
        c = dict(_c(pl.lease_id))
        ten = await db.get(Tenant, pl.tenant_id)
        if ten:
            c["locataire"] = ten.full_name or c["locataire"]
        for i in pl.installments or []:
            seq = i.get("seq")
            entries.append(
                {
                    **c,
                    "date": i.get("due_date"),
                    "intitule": f"Plan d'apurement · échéance {seq}",
                    "montant": float(i.get("amount", 0)),
                    "sign": "debit",
                }
            )
            if i.get("paid"):
                entries.append(
                    {
                        **c,
                        "date": i.get("paid_date") or i.get("due_date"),
                        "intitule": f"Règlement apurement · échéance {seq}",
                        "montant": float(i.get("amount", 0)),
                        "sign": "credit",
                    }
                )

    regs = (
        (
            await db.execute(
                select(ChargeRegularization).where(ChargeRegularization.lease_id.in_(lease_ids))
            )
        )
        .scalars()
        .all()
    )
    for rg in regs:
        c = dict(_c(rg.lease_id))
        ten = await db.get(Tenant, rg.tenant_id)
        if ten:
            c["locataire"] = ten.full_name or c["locataire"]
        bal = float(rg.balance or 0)
        yr = (
            rg.period_start.year
            if rg.period_start
            else (rg.period_end.year if rg.period_end else "")
        )
        ds = (
            rg.applied_at.date().isoformat()
            if rg.applied_at
            else (rg.period_end.isoformat() if rg.period_end else None)
        )
        entries.append(
            {
                **c,
                "date": ds,
                "intitule": f"Régularisation charges {yr}".strip(),
                "montant": abs(bal),
                "sign": "credit" if bal >= 0 else "debit",
            }
        )

    if year:
        entries = [e for e in entries if (e.get("date") or "")[:4] == str(year)]
    entries.sort(key=lambda e: e.get("date") or "", reverse=True)
    return {"is_mandataire": is_mandataire, "entries": entries}


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
    current_user: User = Depends(get_current_user),
):
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment)
    return payment


@router.delete("/{payment_id}", status_code=204)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Supprime définitivement un paiement."""
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    await PaymentService.delete_payment(db, payment_id)
    await db.commit()


@router.post("/{payment_id}/record", response_model=PaymentResponse)
async def record_payment(
    payment_id: uuid.UUID,
    data: PaymentRecordIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.COMPTABLE)),
):
    _existing = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, _existing, write=True)
    payment = await PaymentService.record_payment(db, payment_id, data)
    await audit_service.log(
        db,
        action=audit_service.PAYMENT_RECORD,
        user_id=current_user.id,
        user_email=current_user.email,
        entity_type="payment",
        entity_id=payment.id,
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

    from app.core.exceptions import BadRequestException
    from app.models.notification import Notification, NotificationPriority, NotificationType
    from app.models.tenant import Tenant as _Tenant

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    if not payment.declared_at:
        raise BadRequestException("Aucune déclaration de paiement à valider pour ce loyer")

    amount = float(payment.declared_amount) if payment.declared_amount else float(payment.balance)
    method = payment.declared_method or "virement"

    payment = await PaymentService.record_payment(
        db,
        payment_id,
        PaymentRecordIn(amount_paid=amount, payment_date=_date.today(), payment_method=method),
    )
    # Déclaration consommée
    payment.declared_at = None
    payment.declared_method = None
    payment.declared_amount = None

    # Notifie le locataire que son règlement est validé
    tenant = (
        await db.execute(_select(_Tenant).where(_Tenant.id == payment.tenant_id))
    ).scalar_one_or_none()
    if tenant and tenant.user_id:
        _quittance_note = (
            " Votre quittance est disponible."
            if payment.status == PaymentStatus.PAID
            else " La quittance sera disponible une fois le loyer du mois intégralement réglé."
        )
        db.add(
            Notification(
                title="Paiement validé",
                message=(
                    f"Votre règlement du loyer de {payment.period_label} a été validé "
                    f"par votre gestionnaire.{_quittance_note}"
                ),
                notification_type=NotificationType.PAIEMENT_RECU,
                priority=NotificationPriority.NORMAL,
                entity_type="payment",
                entity_id=payment.id,
                user_id=tenant.user_id,
            )
        )

    await audit_service.log(
        db,
        action=audit_service.PAYMENT_RECORD,
        user_id=current_user.id,
        user_email=current_user.email,
        entity_type="payment",
        entity_id=payment.id,
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

    from app.core.exceptions import BadRequestException
    from app.models.notification import Notification, NotificationPriority, NotificationType
    from app.models.tenant import Tenant as _Tenant

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    if not payment.declared_at:
        raise BadRequestException("Aucune déclaration de paiement à refuser pour ce loyer")

    payment.declared_at = None
    payment.declared_method = None
    payment.declared_amount = None

    tenant = (
        await db.execute(_select(_Tenant).where(_Tenant.id == payment.tenant_id))
    ).scalar_one_or_none()
    if tenant and tenant.user_id:
        db.add(
            Notification(
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
            )
        )

    await db.flush()
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    _existing = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, _existing, write=True)
    payment = await PaymentService.cancel_payment(db, payment_id)
    await db.commit()
    return await PaymentService.get_by_id(db, payment.id, load_relations=True)


@router.get("/{payment_id}/quittance")
async def download_quittance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _feat: User = Depends(require_feature("quittances")),
):
    from datetime import datetime

    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    # Isolation par rôle : locataire→le sien, propriétaire→son bien, mandataire→hors GP.
    await assert_payment_access(db, current_user, payment)
    # Règle : une quittance n'est générée que lorsque le mois est INTÉGRALEMENT payé.
    if payment.status != PaymentStatus.PAID:
        from app.core.exceptions import BadRequestException

        raise BadRequestException(
            "La quittance n'est disponible que lorsque le loyer du mois est intégralement payé."
        )
    if not payment.quittance_generated_at:
        payment.quittance_generated_at = datetime.now(UTC)
        await db.flush()
        await db.commit()
        payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    pdf_bytes, filename = await build_quittance_pdf(db, payment)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def build_quittance_pdf(db: AsyncSession, payment) -> tuple:
    """Construit le PDF de quittance (blocs / template enregistré / .j2) et renvoie
    (pdf_bytes, filename). Réutilisé par le téléchargement ET l'envoi par e-mail."""
    from datetime import date as _date
    from datetime import datetime, timezone  # noqa: F401 (compat imports locaux)

    from app.services.template_layout_service import get_layout

    _MONTHS_FR = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    _d = _date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    # Noms de tous les locataires : principal puis co-titulaires, chacun sur sa ligne.
    names: list[str] = []
    _lease_obj = None
    if getattr(payment, "lease_id", None):
        from sqlalchemy import select as _select
        from sqlalchemy.orm import selectinload as _selectinload

        from app.models.lease import Lease as _Lease

        _lease_obj = (
            await db.execute(
                _select(_Lease)
                .options(_selectinload(_Lease.tenant), _selectinload(_Lease.co_tenants))
                .where(_Lease.id == payment.lease_id)
            )
        ).scalar_one_or_none()
        if _lease_obj:
            try:
                names = [t.full_name for t in _lease_obj.all_tenants]
            except Exception:
                names = []
    if not names and payment.tenant:
        names = [payment.tenant.full_name]
    tenant_names = " & ".join(names)
    layout = get_layout()

    # 0) Quittance par BLOCS (mise en page moderne) si le template par défaut en possède.
    _gid0 = getattr(payment.lease, "created_by", None) if getattr(payment, "lease", None) else None
    if _gid0:
        from sqlalchemy import select as _sel0

        from app.models.document_template import DocumentTemplate as _DT0

        _qt = (
            await db.execute(
                _sel0(_DT0).where(
                    _DT0.gestionnaire_id == _gid0,
                    _DT0.template_type == "quittance",
                    _DT0.is_default.is_(True),
                    _DT0.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if _qt is not None and getattr(_qt, "blocks", None):
            from app.services.document_blocks_pdf_service import (
                _doc_common_vars,
                _eur_sym,
                render_blocks_document,
            )

            _pobj0 = (
                payment.lease.parent_property
                if getattr(payment.lease, "parent_property", None)
                else None
            )
            _ten0 = getattr(payment, "tenant", None)
            if getattr(payment, "period_start", None) and getattr(payment, "period_end", None):
                _per0 = (
                    f"du {payment.period_start.strftime('%d/%m/%Y')} "
                    f"au {payment.period_end.strftime('%d/%m/%Y')}"
                )
            else:
                _per0 = payment.period_label
            _qv = _doc_common_vars(_ten0, _pobj0, today_fr)
            # Montant réglé du mois = paiements directs + part soldée par apurement.
            _paid_eff0 = float(payment.amount_paid or 0) + float(
                getattr(payment, "amount_on_plan", 0) or 0
            )
            _qv.update(
                {
                    "period_range": _per0,
                    "month": payment.period_label,
                    "total_due": _eur_sym(_paid_eff0),
                    "rent_amount": _eur_sym(payment.amount_rent),
                    "charges_amount": _eur_sym(payment.amount_charges),
                    "apl_amount": _eur_sym(payment.amount_apl) if payment.amount_apl else "",
                }
            )
            _li0 = [
                {
                    "label": "LOYER PRINCIPAL",
                    "appele": _eur_sym(payment.amount_rent),
                    "regle": _eur_sym(payment.amount_rent),
                },
                {
                    "label": "PROVISION CHARGES",
                    "appele": _eur_sym(payment.amount_charges),
                    "regle": _eur_sym(payment.amount_charges),
                },
            ]
            if payment.amount_apl:
                _li0.append(
                    {
                        "label": "AIDE PERSONNELLE AU LOGEMENT",
                        "appele": "-" + _eur_sym(payment.amount_apl),
                        "regle": "-" + _eur_sym(payment.amount_apl),
                    }
                )
            _pdf0 = await render_blocks_document(db, _gid0, "quittance", _qv, line_items=_li0)
            from app.utils.filename import doc_filename as _docfn0

            _fn0 = _docfn0(
                "quittance",
                tenant=payment.tenant.full_name if payment.tenant else None,
                property_name=_pobj0.name if _pobj0 else None,
                month=payment.period_month,
                year=payment.period_year,
            )
            return _pdf0, _fn0

    # 1) Template ENREGISTRÉ par le gestionnaire (éditeur) si présent…
    from app.services.document_render_service import eur, render_saved_document
    from app.services.pdf_service import civility_greeting, user_signature_uri

    _prop_obj = (
        payment.lease.parent_property
        if getattr(payment, "lease", None) and getattr(payment.lease, "parent_property", None)
        else None
    )
    _gid = getattr(payment.lease, "created_by", None) if getattr(payment, "lease", None) else None
    _sig_uri = await user_signature_uri(db, _gid)
    variables = {
        "tenant_name": names[0] if names else "",
        "civility_greeting": civility_greeting(getattr(payment, "tenant", None)),
        "company_name": "",
        "property_name": _prop_obj.name if _prop_obj else "",
        "unit_ref": _prop_obj.name if _prop_obj else "",
        "property_address": _prop_obj.full_address_block if _prop_obj else "",
        "amount_paid": eur(payment.amount_paid),
        "rent_amount": eur(payment.amount_rent),
        "charges_amount": eur(payment.amount_charges),
        "apl_amount": eur(payment.amount_apl) if payment.amount_apl else "",
        "month": payment.period_label,
        "date": today_fr,
        "lease_start_date": (
            _lease_obj.start_date.strftime("%d/%m/%Y")
            if _lease_obj and getattr(_lease_obj, "start_date", None)
            else ""
        ),
        "signature_uri": _sig_uri,
    }
    custom = await render_saved_document(
        db,
        template_type="quittance",
        gestionnaire_id=_gid,
        variables=variables,
        recipient_lines=names,
        property_address=_prop_obj.full_address_block if _prop_obj else "",
        layout=layout,
    )
    # Mention « révision de loyer à venir » (1 mois à l'avance), si applicable.
    notice = None
    if _lease_obj is not None:
        from app.services.irl_notice import upcoming_revision_notice

        notice = await upcoming_revision_notice(
            db, _lease_obj, payment.period_year, payment.period_month
        )

    if custom:
        if notice:
            from app.services.irl_notice import inject_notice

            custom = inject_notice(custom, notice)
        pdf_bytes = html_to_pdf(custom)
    else:
        # 2) …sinon, modèle .j2 historique (mise en page complète).
        html = render_template(
            "quittance.html.j2",
            {
                "payment": payment,
                "today": today_fr,
                "tenant_names": tenant_names,
                "tenant_names_list": names,
                "layout": layout,
                "signature_uri": _sig_uri,
            },
        )
        if notice:
            from app.services.irl_notice import inject_notice

            html = inject_notice(html, notice)
        pdf_bytes = html_to_pdf(html)

    from app.utils.filename import doc_filename

    _prop = (
        payment.lease.parent_property.name
        if getattr(payment, "lease", None) and getattr(payment.lease, "parent_property", None)
        else None
    )
    filename = doc_filename(
        "quittance",
        tenant=payment.tenant.full_name if payment.tenant else None,
        property_name=_prop,
        month=payment.period_month,
        year=payment.period_year,
    )
    return pdf_bytes, filename


@router.post("/{payment_id}/quittance/send")
async def send_quittance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("quittances")),
):
    """Envoie la quittance par e-mail au locataire (PDF joint) et la marque envoyée."""
    import logging

    from fastapi import HTTPException

    _log = logging.getLogger(__name__)
    try:
        _existing = await PaymentService.get_by_id(db, payment_id, load_relations=True)
        await assert_payment_access(db, current_user, _existing, write=True)
        payment = await PaymentService.send_quittance(db, payment_id)
        # Envoi e-mail réel du PDF au locataire (fail-soft : un échec d'envoi ne
        # bloque pas le marquage « envoyée »).
        email_sent = False
        _to = getattr(getattr(payment, "tenant", None), "email", None)
        if _to:
            try:
                pdf_bytes, _fn = await build_quittance_pdf(db, payment)
                from app.services import mail_signature
                from app.services.automation_engine import render_rule_body, render_subject
                from app.services.cc_service import rule_cc_for_lease, rule_message_for_lease
                from app.services.email_service import send_quittance as _send_q

                _cc = await rule_cc_for_lease(db, payment.lease_id, "quittance")
                _sig, _logo, _logosub = await mail_signature.build_for_lease(
                    db, payment.lease_id, "quittance"
                )
                _subjT, _bodyT = await rule_message_for_lease(db, payment.lease_id, "quittance")
                _amount = float(payment.amount_paid or 0) + float(
                    getattr(payment, "amount_on_plan", 0) or 0
                )
                _ctx = {
                    "tenant_name": (payment.tenant.full_name if payment.tenant else "") or "",
                    "period": payment.period_label,
                    "amount": f"{_amount:.2f} €",
                }
                email_sent = await _send_q(
                    to=_to,
                    tenant_name=payment.tenant.full_name if payment.tenant else "",
                    period_label=payment.period_label,
                    amount=_amount,
                    pdf_bytes=pdf_bytes,
                    cc=_cc,
                    subject=render_subject(_subjT, _ctx),
                    signature_html=_sig,
                    inline_logo=_logo,
                    inline_logo_subtype=_logosub,
                    body_html=render_rule_body(_bodyT, _ctx),
                )
            except Exception as _exc:  # noqa: BLE001
                _log.warning("Envoi e-mail quittance échoué (%s): %s", payment_id, _exc)
        await db.commit()
        return {
            "id": str(payment.id),
            "quittance_generated_at": payment.quittance_generated_at,
            "quittance_sent_at": payment.quittance_sent_at,
            "email_sent": email_sent,
        }
    except Exception as e:
        if "non payé" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise
