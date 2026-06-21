"""API Dashboard — statistiques avancées pour aide à la décision."""

import uuid
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_manager, get_current_user
from app.core.permissions import Role
from app.database import get_db
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.schemas.dashboard import (
    AlertStats,
    DashboardStats,
    FinancialStats,
    FiscalRevenueFoncier,
    MonthlyRevenue,
    OccupancyStats,
    OwnerBreakdown,
    PropertyStats,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _lease_active_in_month(today: date):
    """Condition SQL : bail réellement actif SUR le mois courant.

    Exclut les baux qui démarrent plus tard (mois prochain ou au-delà) et ceux
    déjà terminés, pour que des contrats futurs ne faussent pas les statistiques
    du mois (loyers attendus, occupation, revenus par bien…)."""
    month_start = today.replace(day=1)
    next_month = month_start + relativedelta(months=1)
    return and_(
        Lease.is_active.is_(True),
        Lease.start_date < next_month,
        or_(Lease.end_date.is_(None), Lease.end_date >= month_start),
    )

# Règles de revenu d'apurement (mois reportés + échéances) centralisées.
from app.services.apurement_revenue import (
    apurement_installments as _apurement_installments,
)
from app.services.apurement_revenue import (
    apurement_received as _apurement_received,
)
from app.services.apurement_revenue import (  # noqa: E402
    received_status as _received_status,
)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_manager),
):
    today = date.today()
    role = Role(current_user.role)

    # ── Périmètre ─────────────────────────────────────────────────────────────
    prop_ids_filter: list = []  # GP : liste blanche de ses biens
    is_gp = role == Role.GESTIONNAIRE_PROPRIO
    is_mandataire = role == Role.GESTIONNAIRE

    if is_gp:
        res = await db.execute(select(Property.id).where(Property.created_by == current_user.id))
        prop_ids_filter = list(res.scalars().all())
        if not prop_ids_filter:
            return DashboardStats(
                occupancy=OccupancyStats(
                    total_units=0, occupied_units=0, vacant_units=0, occupancy_rate=0
                ),
                financial=FinancialStats(
                    total_rent_expected=0,
                    total_rent_received=0,
                    total_outstanding=0,
                    collection_rate=0,
                    total_deposits=0,
                ),
                monthly_revenues=[
                    MonthlyRevenue(
                        month=(today.replace(day=1) - relativedelta(months=i)).strftime("%Y-%m"),
                        expected=0,
                        received=0,
                        outstanding=0,
                    )
                    for i in range(11, -1, -1)
                ],
                top_properties=[],
                alerts=AlertStats(
                    leases_expiring_30d=0,
                    leases_expiring_90d=0,
                    overdue_payments=0,
                    overdue_amount=0,
                    tenants_no_insurance=0,
                ),
                total_tenants=0,
                total_properties=0,
                total_leases_active=0,
            )

    if is_mandataire:
        # Mandataire : liste blanche = biens de SON agence (multi-tenant).
        from app.api.v1._isolation import agency_property_ids

        prop_ids_filter = list(await agency_property_ids(db, current_user))

    # Liste blanche de biens (GP + mandataire) ; None = tout (admin).
    whitelist = prop_ids_filter if (is_gp or is_mandataire) else None

    def _lease_scope(q):
        if whitelist is not None:
            return q.where(Lease.property_id.in_(whitelist))
        return q

    def _payment_scope(q):
        if whitelist is not None:
            return q.join(Lease, Payment.lease_id == Lease.id).where(
                Lease.property_id.in_(whitelist)
            )
        return q

    # ── Biens (un bien = un logement) ──────────────────────────────────────────
    if whitelist is not None:
        total_units_res = await db.execute(
            select(func.count(Property.id)).where(Property.id.in_(whitelist))
        )
    else:
        total_units_res = await db.execute(select(func.count(Property.id)))
    total_units = total_units_res.scalar_one() or 0

    occupied_units_res = await db.execute(
        _lease_scope(
            select(func.count(func.distinct(Lease.property_id))).where(
                _lease_active_in_month(today)
            )
        )
    )
    occupied_units = occupied_units_res.scalar_one() or 0
    vacant_units = max(0, total_units - occupied_units)
    occupancy_rate = round((occupied_units / total_units * 100) if total_units else 0, 1)

    # ── Finances ──────────────────────────────────────────────────────────────
    rent_expected_res = await db.execute(
        _lease_scope(
            select(func.sum(Lease.rent_amount + Lease.charges_amount)).where(
                _lease_active_in_month(today)
            )
        )
    )
    total_rent_expected = float(rent_expected_res.scalar_one() or 0)

    rent_received_res = await db.execute(
        _payment_scope(
            select(func.coalesce(func.sum(Payment.amount_paid), 0.0)).where(
                _received_status(),
                Payment.period_year == today.year,
                Payment.period_month == today.month,
            )
        )
    )
    total_rent_received = float(rent_received_res.scalar_one() or 0)
    total_rent_received += await _apurement_received(
        db, whitelist, year=today.year, month=today.month
    )

    outstanding_res = await db.execute(
        _payment_scope(
            select(func.sum(Payment.amount_due - Payment.amount_paid)).where(
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                Payment.due_date < today,
            )
        )
    )
    total_outstanding = float(outstanding_res.scalar_one() or 0)
    collection_rate = round(
        (total_rent_received / total_rent_expected * 100) if total_rent_expected else 0, 1
    )

    deposits_res = await db.execute(
        _lease_scope(select(func.sum(Lease.deposit_amount)).where(_lease_active_in_month(today)))
    )
    total_deposits = float(deposits_res.scalar_one() or 0)

    # ── Revenus mensuels (12 derniers mois) ───────────────────────────────────
    monthly_revenues = []
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - relativedelta(months=i)
        month_str = month_date.strftime("%Y-%m")
        month_start = month_date
        month_end = month_date + relativedelta(months=1)

        exp_res = await db.execute(
            _lease_scope(
                select(func.sum(Lease.rent_amount + Lease.charges_amount)).where(
                    Lease.is_active.is_(True),
                    # Bail actif SUR ce mois : commencé avant le mois suivant et pas
                    # encore terminé (sinon les baux futurs gonflent l'attendu).
                    Lease.start_date < month_end,
                    or_(Lease.end_date.is_(None), Lease.end_date >= month_start),
                )
            )
        )
        expected = float(exp_res.scalar_one() or 0)

        rec_res = await db.execute(
            _payment_scope(
                select(func.coalesce(func.sum(Payment.amount_paid), 0.0)).where(
                    _received_status(),
                    Payment.period_year == month_date.year,
                    Payment.period_month == month_date.month,
                )
            )
        )
        received = float(rec_res.scalar_one() or 0)
        received += await _apurement_received(
            db, whitelist, year=month_date.year, month=month_date.month
        )

        out_res = await db.execute(
            _payment_scope(
                select(func.sum(Payment.amount_due - Payment.amount_paid)).where(
                    Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                    Payment.due_date >= month_start,
                    Payment.due_date < month_end,
                )
            )
        )
        outstanding = float(out_res.scalar_one() or 0)

        monthly_revenues.append(
            MonthlyRevenue(
                month=month_str,
                expected=round(expected, 2),
                received=round(received, 2),
                outstanding=round(outstanding, 2),
            )
        )

    # ── Performance par bien (TOUS les biens du périmètre) ──────────────────────
    if whitelist is not None:
        props_res = await db.execute(select(Property).where(Property.id.in_(whitelist)))
    else:
        props_res = await db.execute(select(Property))
    properties = props_res.scalars().all()

    # Agrégats par bien en 2 requêtes groupées (au lieu de 3 requêtes par bien)
    prop_ids = [prop.id for prop in properties]
    occ_by_prop: dict = {}
    rev_by_prop: dict = {}
    out_by_prop: dict = {}
    if prop_ids:
        lease_rows = (
            await db.execute(
                select(
                    Lease.property_id,
                    func.count(Lease.id),
                    func.sum(Lease.rent_amount + Lease.charges_amount),
                )
                .where(Lease.property_id.in_(prop_ids), _lease_active_in_month(today))
                .group_by(Lease.property_id)
            )
        ).all()
        for pid, cnt, rev in lease_rows:
            occ_by_prop[pid] = cnt or 0
            rev_by_prop[pid] = float(rev or 0)

        out_rows = (
            await db.execute(
                select(
                    Lease.property_id,
                    func.sum(Payment.amount_due - Payment.amount_paid),
                )
                .join(Lease, Payment.lease_id == Lease.id)
                .where(
                    Lease.property_id.in_(prop_ids),
                    Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                    Payment.due_date < today,
                )
                .group_by(Lease.property_id)
            )
        ).all()
        for pid, out in out_rows:
            out_by_prop[pid] = float(out or 0)

    top_properties = [
        PropertyStats(
            property_id=str(prop.id),
            property_name=prop.name,
            units_count=1,  # un bien = un logement
            occupied_count=occ_by_prop.get(prop.id, 0),
            monthly_revenue=round(rev_by_prop.get(prop.id, 0.0), 2),
            outstanding=round(out_by_prop.get(prop.id, 0.0), 2),
        )
        for prop in properties
    ]

    top_properties.sort(key=lambda x: x.monthly_revenue, reverse=True)

    # ── Ventilation par propriétaire (réutilise les agrégats par bien) ──────────
    owner_acc: dict = {}
    for prop in properties:
        key = (prop.owner_name or "").strip() or "Sans propriétaire"
        a = owner_acc.setdefault(
            key,
            {
                "properties_count": 0,
                "occupied_count": 0,
                "monthly_revenue": 0.0,
                "outstanding": 0.0,
            },
        )
        a["properties_count"] += 1
        a["occupied_count"] += 1 if occ_by_prop.get(prop.id, 0) else 0
        a["monthly_revenue"] += rev_by_prop.get(prop.id, 0.0)
        a["outstanding"] += out_by_prop.get(prop.id, 0.0)
    by_owner = [
        OwnerBreakdown(
            owner_name=name,
            properties_count=v["properties_count"],
            occupied_count=v["occupied_count"],
            monthly_revenue=round(v["monthly_revenue"], 2),
            outstanding=round(v["outstanding"], 2),
        )
        for name, v in owner_acc.items()
    ]
    by_owner.sort(key=lambda x: x.monthly_revenue, reverse=True)

    # ── Alertes ───────────────────────────────────────────────────────────────
    expiring_30_res = await db.execute(
        _lease_scope(
            select(func.count(Lease.id)).where(
                Lease.is_active.is_(True),
                Lease.end_date.between(today, today + timedelta(days=30)),
            )
        )
    )
    expiring_30 = expiring_30_res.scalar_one() or 0

    expiring_90_res = await db.execute(
        _lease_scope(
            select(func.count(Lease.id)).where(
                Lease.is_active.is_(True),
                Lease.end_date.between(today, today + timedelta(days=90)),
            )
        )
    )
    expiring_90 = expiring_90_res.scalar_one() or 0

    overdue_count_res = await db.execute(
        _payment_scope(
            select(func.count(Payment.id)).where(
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                Payment.due_date < today,
            )
        )
    )
    overdue_payments = overdue_count_res.scalar_one() or 0

    overdue_amount_res = await db.execute(
        _payment_scope(
            select(func.sum(Payment.amount_due - Payment.amount_paid)).where(
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                Payment.due_date < today,
            )
        )
    )
    overdue_amount = float(overdue_amount_res.scalar_one() or 0)

    # ── Totaux généraux ───────────────────────────────────────────────────────
    if whitelist is not None:
        total_tenants_res = await db.execute(
            select(func.count(func.distinct(Lease.tenant_id))).where(
                Lease.property_id.in_(whitelist),
                Lease.is_active.is_(True),
            )
        )
    else:
        total_tenants_res = await db.execute(select(func.count(Tenant.id)))
    total_tenants = total_tenants_res.scalar_one() or 0

    if whitelist is not None:
        total_props = len(whitelist)
    else:
        total_props = (await db.execute(select(func.count(Property.id)))).scalar_one() or 0

    # Contrats actifs = baux actifs SUR le mois courant (les baux à venir sont comptés
    # à part, ci-dessous).
    active_leases_res = await db.execute(
        _lease_scope(select(func.count(Lease.id)).where(_lease_active_in_month(today)))
    )
    total_leases_active = active_leases_res.scalar_one() or 0

    # Contrats à venir = baux signés (actifs) démarrant le mois prochain ou plus tard.
    _next_month = today.replace(day=1) + relativedelta(months=1)
    future_leases_res = await db.execute(
        _lease_scope(
            select(func.count(Lease.id)).where(
                Lease.is_active.is_(True),
                Lease.start_date >= _next_month,
            )
        )
    )
    total_leases_future = future_leases_res.scalar_one() or 0

    # Répartition des contrats actifs (mois courant) par type (nu/meublé/…).
    type_rows = await db.execute(
        _lease_scope(
            select(Lease.lease_type, func.count(Lease.id))
            .where(_lease_active_in_month(today))
            .group_by(Lease.lease_type)
        )
    )
    active_leases_by_type = {row[0]: row[1] for row in type_rows.all()}

    # ── Occupation à venir (mois suivant) ──────────────────────────────────────
    # Unités qui auront un bail actif le mois prochain (inclut les baux qui démarrent
    # le mois prochain et exclut ceux qui se terminent d'ici là).
    occupied_next_res = await db.execute(
        _lease_scope(
            select(func.count(func.distinct(Lease.property_id))).where(
                _lease_active_in_month(today + relativedelta(months=1))
            )
        )
    )
    occupancy_next_occupied = occupied_next_res.scalar_one() or 0
    occupancy_next_rate = round(
        (occupancy_next_occupied / total_units * 100) if total_units else 0, 1
    )

    # ── Entretiens importants à venir (planifiés / en cours, dus sous 30 j ou en retard) ─
    from sqlalchemy.orm import selectinload as _selectinload

    from app.models.entretien import Entretien, EntretienStatus
    from app.schemas.dashboard import UpcomingEntretien

    ent_q = (
        select(Entretien)
        .options(_selectinload(Entretien.property))
        .where(
            Entretien.status.in_([EntretienStatus.PLANIFIE.value, EntretienStatus.EN_COURS.value]),
            Entretien.scheduled_date <= today + timedelta(days=30),
        )
    )
    if whitelist is not None:
        ent_q = ent_q.where(Entretien.property_id.in_(whitelist))
    ent_q = ent_q.order_by(Entretien.scheduled_date.asc()).limit(6)
    upcoming = [
        UpcomingEntretien(
            id=str(e.id),
            title=e.title,
            type=e.type,
            status=e.status,
            scheduled_date=e.scheduled_date,
            property_label=(e.property.address if e.property else None),
            overdue=e.scheduled_date < today,
        )
        for e in (await db.execute(ent_q)).scalars().all()
    ]

    return DashboardStats(
        occupancy=OccupancyStats(
            total_units=total_units,
            occupied_units=occupied_units,
            vacant_units=vacant_units,
            occupancy_rate=occupancy_rate,
        ),
        financial=FinancialStats(
            total_rent_expected=round(total_rent_expected, 2),
            total_rent_received=round(total_rent_received, 2),
            total_outstanding=round(total_outstanding, 2),
            collection_rate=collection_rate,
            total_deposits=round(total_deposits, 2),
        ),
        monthly_revenues=monthly_revenues,
        top_properties=top_properties,
        by_owner=by_owner,
        alerts=AlertStats(
            leases_expiring_30d=expiring_30,
            leases_expiring_90d=expiring_90,
            overdue_payments=overdue_payments,
            overdue_amount=round(overdue_amount, 2),
            tenants_no_insurance=0,
        ),
        total_tenants=total_tenants,
        total_properties=total_props,
        total_leases_active=total_leases_active,
        total_leases_future=total_leases_future,
        active_leases_by_type=active_leases_by_type,
        occupancy_next_rate=occupancy_next_rate,
        occupancy_next_occupied=occupancy_next_occupied,
    )


@router.get("/proprietaire-stats")
async def get_proprietaire_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Statistiques mensuelles pour le tableau de bord propriétaire."""
    from app.core.permissions import Role as R

    role = R(current_user.role)

    if role not in (R.PROPRIETAIRE, R.GESTIONNAIRE, R.GESTIONNAIRE_PROPRIO, R.ADMIN):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Accès refusé")

    proprietaire_id = current_user.id

    # Biens du propriétaire
    props_res = await db.execute(select(Property).where(Property.owner_user_id == proprietaire_id))
    properties = list(props_res.scalars().all())
    prop_ids = [p.id for p in properties]

    if not prop_ids:
        return {
            "monthly_revenue_expected": 0,
            "monthly_revenue_received": 0,
            "total_properties": 0,
            "active_leases": 0,
        }

    today = date.today()

    # Revenus attendus = somme loyers+charges des baux actifs SUR le mois courant
    expected_res = await db.execute(
        select(func.sum(Lease.rent_amount + Lease.charges_amount)).where(
            Lease.property_id.in_(prop_ids),
            _lease_active_in_month(today),
        )
    )
    monthly_expected = float(expected_res.scalar_one() or 0)

    # Revenus encaissés ce mois (par période, cohérent avec le dashboard gestionnaire)

    received_res = await db.execute(
        select(func.sum(Payment.amount_paid))
        .join(Lease, Payment.lease_id == Lease.id)
        .where(
            Lease.property_id.in_(prop_ids),
            _received_status(),
            Payment.period_year == today.year,
            Payment.period_month == today.month,
        )
    )
    monthly_received = float(received_res.scalar_one() or 0)
    monthly_received += await _apurement_received(db, prop_ids, year=today.year, month=today.month)

    active_leases_res = await db.execute(
        select(func.count(Lease.id)).where(
            Lease.property_id.in_(prop_ids), Lease.is_active.is_(True)
        )
    )
    active_leases = active_leases_res.scalar_one() or 0

    return {
        "monthly_revenue_expected": round(monthly_expected, 2),
        "monthly_revenue_received": round(monthly_received, 2),
        "total_properties": len(properties),
        "active_leases": active_leases,
    }


@router.get("/proprietaire-apurement")
async def get_proprietaire_apurement(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Échéances d'apurement encaissées sur les biens du propriétaire, sous forme
    de lignes de revenu (à fusionner avec « Mes revenus »)."""
    props_res = await db.execute(select(Property).where(Property.owner_user_id == current_user.id))
    properties = list(props_res.scalars().all())
    prop_ids = [p.id for p in properties]
    if not prop_ids:
        return {"items": []}

    prop_by_id = {p.id: p for p in properties}
    rows = await _apurement_installments(db, prop_ids)
    items = []
    for r in rows:
        pl = r["plan"]
        ten = await db.get(Tenant, pl.tenant_id)
        lease = await db.get(Lease, pl.lease_id)
        prop = prop_by_id.get(lease.property_id) if lease else None
        items.append(
            {
                "id": f"apur-{pl.id}-{r['seq']}",
                "period_label": f"Apurement · échéance {r['seq']}",
                "tenant_full_name": ten.full_name if ten else "",
                "property_name": prop.name if prop else "",
                "amount_due": r["amount"],
                "amount_paid": r["amount"],
                "status": "apurement",
                "settled_by_plan": False,
                "payment_date": r["date"].isoformat(),
            }
        )
    return {"items": items}


@router.get("/fiscal/{year}", response_model=FiscalRevenueFoncier)
async def get_fiscal_revenues(
    year: int,
    proprietaire_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Calcul des revenus fonciers pour la liasse fiscale."""
    from app.core.permissions import Role as R

    role = R(current_user.role)

    # Propriétaire (et gestionnaire_proprio) ne voient que leurs propres données
    if role in (R.PROPRIETAIRE, R.GESTIONNAIRE_PROPRIO):
        proprietaire_id = current_user.id

    # Trouver les biens du propriétaire
    q_props = select(Property)
    if proprietaire_id:
        q_props = q_props.where(Property.owner_user_id == proprietaire_id)
    props_res = await db.execute(q_props)
    properties = list(props_res.scalars().all())
    # Mandataire (et legacy lecture/comptable) : uniquement les biens de SON agence.
    if role in (R.GESTIONNAIRE, R.LECTURE, R.COMPTABLE):
        from app.api.v1._isolation import agency_property_ids

        _allowed = await agency_property_ids(db, current_user)
        properties = [p for p in properties if p.id in _allowed]
    prop_ids = [p.id for p in properties]

    if not prop_ids:
        from app.models.user import User

        owner = await db.get(User, proprietaire_id) if proprietaire_id else current_user
        return FiscalRevenueFoncier(
            year=year,
            proprietaire_id=str(proprietaire_id or current_user.id),
            proprietaire_name=current_user.full_name,
            gross_rent_revenue=0,
            charges_received=0,
            total_gross_revenue=0,
            repairs_charges=0,
            management_fees=0,
            insurance_charges=0,
            property_tax=0,
            other_charges=0,
            total_deductible=0,
            net_revenue=0,
            properties=[],
        )

    # ── Filtre commun : paiements perçus (PAID ou PARTIAL) sur l'année ─────────
    # On filtre par period_year (période du loyer) et non payment_date
    # pour être robuste aux saisies tardives.
    # Pour les paiements partiels, on pro-rate la part loyer/charges
    # sur le montant réellement encaissé (amount_paid).
    _base_filter = [
        Lease.property_id.in_(prop_ids),
        _received_status(),
        Payment.period_year == year,
    ]

    # Part loyer réellement perçue = amount_paid × (amount_rent / amount_due)
    rent_res = await db.execute(
        select(
            func.sum(
                case(
                    (
                        Payment.amount_due > 0,
                        Payment.amount_paid * Payment.amount_rent / Payment.amount_due,
                    ),
                    else_=0.0,
                )
            )
        )
        .join(Lease, Payment.lease_id == Lease.id)
        .where(*_base_filter)
    )
    gross_rent = float(rent_res.scalar_one() or 0)
    # Revenu reconnu via les échéances d'apurement encaissées dans l'année.
    gross_rent += await _apurement_received(db, prop_ids, year=year)

    # Part charges réellement perçue = amount_paid × (amount_charges / amount_due)
    charges_res = await db.execute(
        select(
            func.sum(
                case(
                    (
                        Payment.amount_due > 0,
                        Payment.amount_paid * Payment.amount_charges / Payment.amount_due,
                    ),
                    else_=0.0,
                )
            )
        )
        .join(Lease, Payment.lease_id == Lease.id)
        .where(*_base_filter)
    )
    charges_annual = float(charges_res.scalar_one() or 0)

    # Frais de gestion estimés (8% des loyers bruts — valeur par défaut)
    management_fees = round(gross_rent * 0.08, 2)

    # Détail par bien
    properties_detail = []
    for prop in properties:
        prop_rent_res = await db.execute(
            select(
                func.sum(
                    case(
                        (
                            Payment.amount_due > 0,
                            Payment.amount_paid * Payment.amount_rent / Payment.amount_due,
                        ),
                        else_=0.0,
                    )
                )
            )
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop.id,
                _received_status(),
                Payment.period_year == year,
            )
        )
        prop_rent = float(prop_rent_res.scalar_one() or 0)
        prop_rent += await _apurement_received(db, [prop.id], year=year)

        leases_res = await db.execute(
            select(func.count(Lease.id)).where(
                Lease.property_id == prop.id, Lease.is_active.is_(True)
            )
        )
        leases_count = leases_res.scalar_one() or 0

        properties_detail.append(
            {
                "property_id": str(prop.id),
                "property_name": prop.name,
                "address": prop.full_address,
                "annual_rent": round(prop_rent, 2),
                "active_leases": leases_count,
            }
        )

    total_gross = gross_rent + charges_annual
    total_deductible = management_fees
    net_revenue = total_gross - total_deductible

    return FiscalRevenueFoncier(
        year=year,
        proprietaire_id=str(proprietaire_id or current_user.id),
        proprietaire_name=current_user.full_name,
        gross_rent_revenue=round(gross_rent, 2),
        charges_received=round(charges_annual, 2),
        total_gross_revenue=round(total_gross, 2),
        repairs_charges=0,
        management_fees=round(management_fees, 2),
        insurance_charges=0,
        property_tax=0,
        other_charges=0,
        total_deductible=round(total_deductible, 2),
        net_revenue=round(net_revenue, 2),
        properties=properties_detail,
    )


@router.get("/proprietaire-performance/{year}")
async def get_proprietaire_performance(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Performance des biens du propriétaire : loyer théorique vs perçu, par mois."""
    from fastapi import HTTPException

    from app.core.permissions import Role as R

    role = R(current_user.role)

    if role not in (R.PROPRIETAIRE, R.GESTIONNAIRE, R.GESTIONNAIRE_PROPRIO, R.ADMIN):
        raise HTTPException(status_code=403, detail="Accès refusé")

    proprietaire_id = current_user.id

    props_res = await db.execute(select(Property).where(Property.owner_user_id == proprietaire_id))
    properties = list(props_res.scalars().all())

    today = date.today()
    months_elapsed = today.month if today.year == year else 12

    result_props = []
    for prop in properties:
        prop_id = prop.id

        # Historique COMPLET des baux du bien (actifs ET résiliés) : on mesure la
        # performance du BIEN, indépendamment des changements de locataire en cours
        # d'année.
        leases_rows = (
            await db.execute(
                select(
                    Lease.start_date,
                    Lease.end_date,
                    Lease.rent_amount,
                    Lease.charges_amount,
                ).where(Lease.property_id == prop_id)
            )
        ).all()

        def _rent_due(m: int, _leases=leases_rows) -> float:
            """Loyer + charges dus pour le mois `m` de l'année, tous baux confondus
            (0 si le bien était vacant ce mois-là)."""
            m_first = date(year, m, 1)
            next_first = m_first + relativedelta(months=1)
            total = 0.0
            for s, e, rent, charges in _leases:
                if s < next_first and (e is None or e >= m_first):
                    total += float(rent or 0) + float(charges or 0)
            return total

        # Encaissé YTD (period_year == year) : payé/partiel + mois reportés (part
        # déjà payée) + échéances d'apurement encaissées dans l'année.
        ytd_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop_id,
                _received_status(),
                Payment.period_year == year,
            )
        )
        ytd_received = float(ytd_res.scalar_one() or 0)
        ytd_received += await _apurement_received(db, [prop_id], year=year)

        # Détail mensuel + cumuls : le théorique d'un mois = loyer dû par le(s) bail(s)
        # qui couvraient ce mois ; un mois sans bail (vacance) ne compte pas.
        monthly_breakdown = []
        ytd_theoretical = 0.0
        active_months = 0
        for month in range(1, months_elapsed + 1):
            expected = _rent_due(month)
            if expected > 0:
                active_months += 1
            ytd_theoretical += expected
            m_res = await db.execute(
                select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
                .join(Lease, Payment.lease_id == Lease.id)
                .where(
                    Lease.property_id == prop_id,
                    _received_status(),
                    Payment.period_year == year,
                    Payment.period_month == month,
                )
            )
            monthly_breakdown.append(
                {
                    "month": month,
                    "expected": round(expected, 2),
                    "received": round(float(m_res.scalar_one() or 0), 2),
                }
            )

        # Loyer mensuel « courant » affiché (mois en cours, ou décembre pour une
        # année passée) — 0 si le bien est vacant ce mois-là.
        monthly_expected = _rent_due(months_elapsed) if months_elapsed >= 1 else 0.0

        collection_rate = round(
            (ytd_received / ytd_theoretical * 100) if ytd_theoretical > 0 else 0, 1
        )

        result_props.append(
            {
                "property_id": str(prop_id),
                "property_name": prop.name,
                "monthly_expected": round(monthly_expected, 2),
                "ytd_theoretical": round(ytd_theoretical, 2),
                "ytd_received": round(ytd_received, 2),
                "collection_rate": collection_rate,
                "months_elapsed": months_elapsed,
                "active_months": active_months,  # mois réellement sous contrat
                "monthly_breakdown": monthly_breakdown,
            }
        )

    total_theoretical = sum(p["ytd_theoretical"] for p in result_props)
    total_received = sum(p["ytd_received"] for p in result_props)
    global_rate = round(
        (total_received / total_theoretical * 100) if total_theoretical > 0 else 0, 1
    )

    return {
        "year": year,
        "months_elapsed": months_elapsed,
        "total_theoretical": round(total_theoretical, 2),
        "total_received": round(total_received, 2),
        "global_collection_rate": global_rate,
        "properties": result_props,
    }
