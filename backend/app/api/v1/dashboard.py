"""API Dashboard — statistiques avancées pour aide à la décision."""
import uuid
from typing import Optional
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.property import Property
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.tenant import Tenant
from app.schemas.dashboard import (
    DashboardStats, OccupancyStats, FinancialStats,
    MonthlyRevenue, PropertyStats, AlertStats, FiscalRevenueFoncier
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    today = date.today()
    role = Role(current_user.role)

    # ── Périmètre ─────────────────────────────────────────────────────────────
    prop_ids_filter: list = []   # GP : liste blanche de ses biens
    excluded_prop_ids: list = [] # Mandataire : biens GP à exclure
    is_gp = role == Role.GESTIONNAIRE_PROPRIO
    is_mandataire = role == Role.GESTIONNAIRE

    if is_gp:
        res = await db.execute(
            select(Property.id).where(Property.created_by == current_user.id)
        )
        prop_ids_filter = list(res.scalars().all())
        if not prop_ids_filter:
            return DashboardStats(
                occupancy=OccupancyStats(total_units=0, occupied_units=0, vacant_units=0, occupancy_rate=0),
                financial=FinancialStats(total_rent_expected=0, total_rent_received=0,
                                         total_outstanding=0, collection_rate=0, total_deposits=0),
                monthly_revenues=[
                    MonthlyRevenue(
                        month=(today.replace(day=1) - relativedelta(months=i)).strftime("%Y-%m"),
                        expected=0, received=0, outstanding=0,
                    )
                    for i in range(11, -1, -1)
                ],
                top_properties=[],
                alerts=AlertStats(leases_expiring_30d=0, leases_expiring_90d=0,
                                   overdue_payments=0, overdue_amount=0, tenants_no_insurance=0),
                total_tenants=0,
                total_properties=0,
                total_leases_active=0,
            )

    if is_mandataire:
        from app.api.v1._isolation import _gp_user_ids
        gp_ids = await _gp_user_ids(db)
        if gp_ids:
            res = await db.execute(
                select(Property.id).where(Property.created_by.in_(gp_ids))
            )
            excluded_prop_ids = list(res.scalars().all())

    def _lease_scope(q):
        if is_gp:
            return q.where(Lease.property_id.in_(prop_ids_filter))
        if is_mandataire and excluded_prop_ids:
            return q.where(Lease.property_id.notin_(excluded_prop_ids))
        return q

    def _payment_scope(q):
        if is_gp:
            return q.join(Lease, Payment.lease_id == Lease.id).where(
                Lease.property_id.in_(prop_ids_filter)
            )
        if is_mandataire and excluded_prop_ids:
            return q.join(Lease, Payment.lease_id == Lease.id).where(
                Lease.property_id.notin_(excluded_prop_ids)
            )
        return q

    # ── Biens (un bien = un logement) ──────────────────────────────────────────
    if is_gp:
        total_units_res = await db.execute(
            select(func.count(Property.id)).where(Property.id.in_(prop_ids_filter))
        )
    elif is_mandataire and excluded_prop_ids:
        total_units_res = await db.execute(
            select(func.count(Property.id)).where(Property.id.notin_(excluded_prop_ids))
        )
    else:
        total_units_res = await db.execute(select(func.count(Property.id)))
    total_units = total_units_res.scalar_one() or 0

    occupied_units_res = await db.execute(
        _lease_scope(
            select(func.count(func.distinct(Lease.property_id))).where(Lease.is_active.is_(True))
        )
    )
    occupied_units = occupied_units_res.scalar_one() or 0
    vacant_units = max(0, total_units - occupied_units)
    occupancy_rate = round((occupied_units / total_units * 100) if total_units else 0, 1)

    # ── Finances ──────────────────────────────────────────────────────────────
    rent_expected_res = await db.execute(
        _lease_scope(
            select(func.sum(Lease.rent_amount + Lease.charges_amount)).where(Lease.is_active.is_(True))
        )
    )
    total_rent_expected = float(rent_expected_res.scalar_one() or 0)

    rent_received_res = await db.execute(
        _payment_scope(
            select(func.coalesce(func.sum(Payment.amount_paid), 0.0)).where(
                Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                Payment.period_year == today.year,
                Payment.period_month == today.month,
            )
        )
    )
    total_rent_received = float(rent_received_res.scalar_one() or 0)

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
        _lease_scope(
            select(func.sum(Lease.deposit_amount)).where(Lease.is_active.is_(True))
        )
    )
    total_deposits = float(deposits_res.scalar_one() or 0)

    # ── Revenus mensuels (12 derniers mois) ───────────────────────────────────
    monthly_revenues = []
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - relativedelta(months=i)
        month_str = month_date.strftime("%Y-%m")
        month_start = month_date
        month_end = (month_date + relativedelta(months=1))

        exp_res = await db.execute(
            _lease_scope(
                select(func.sum(Lease.rent_amount + Lease.charges_amount)).where(
                    Lease.is_active.is_(True),
                    Lease.start_date <= month_end,
                )
            )
        )
        expected = float(exp_res.scalar_one() or 0)

        rec_res = await db.execute(
            _payment_scope(
                select(func.coalesce(func.sum(Payment.amount_paid), 0.0)).where(
                    Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                    Payment.period_year == month_date.year,
                    Payment.period_month == month_date.month,
                )
            )
        )
        received = float(rec_res.scalar_one() or 0)

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

        monthly_revenues.append(MonthlyRevenue(
            month=month_str,
            expected=round(expected, 2),
            received=round(received, 2),
            outstanding=round(outstanding, 2),
        ))

    # ── Performance par bien (TOUS les biens du périmètre) ──────────────────────
    if is_gp:
        props_res = await db.execute(
            select(Property).where(Property.id.in_(prop_ids_filter))
        )
    elif is_mandataire and excluded_prop_ids:
        props_res = await db.execute(
            select(Property).where(Property.id.notin_(excluded_prop_ids))
        )
    else:
        props_res = await db.execute(select(Property))
    properties = props_res.scalars().all()

    top_properties = []
    for prop in properties:
        units_count = 1  # un bien = un logement

        occ_res = await db.execute(
            select(func.count(Lease.id)).where(
                Lease.property_id == prop.id, Lease.is_active.is_(True)
            )
        )
        occ_count = occ_res.scalar_one() or 0

        rev_res = await db.execute(
            select(func.sum(Lease.rent_amount + Lease.charges_amount))
            .where(Lease.property_id == prop.id, Lease.is_active.is_(True))
        )
        monthly_rev = float(rev_res.scalar_one() or 0)

        out_prop_res = await db.execute(
            select(func.sum(Payment.amount_due - Payment.amount_paid))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop.id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.LATE]),
                Payment.due_date < today,
            )
        )
        outstanding_prop = float(out_prop_res.scalar_one() or 0)

        top_properties.append(PropertyStats(
            property_id=str(prop.id),
            property_name=prop.name,
            units_count=units_count,
            occupied_count=occ_count,
            monthly_revenue=round(monthly_rev, 2),
            outstanding=round(outstanding_prop, 2),
        ))

    top_properties.sort(key=lambda x: x.monthly_revenue, reverse=True)

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
    if is_gp:
        total_tenants_res = await db.execute(
            select(func.count(func.distinct(Lease.tenant_id))).where(
                Lease.property_id.in_(prop_ids_filter),
                Lease.is_active.is_(True),
            )
        )
    elif is_mandataire and excluded_prop_ids:
        total_tenants_res = await db.execute(
            select(func.count(func.distinct(Lease.tenant_id))).where(
                Lease.property_id.notin_(excluded_prop_ids),
                Lease.is_active.is_(True),
            )
        )
    else:
        total_tenants_res = await db.execute(select(func.count(Tenant.id)))
    total_tenants = total_tenants_res.scalar_one() or 0

    if is_gp:
        total_props = len(prop_ids_filter)
    elif is_mandataire and excluded_prop_ids:
        total_props = (await db.execute(
            select(func.count(Property.id)).where(Property.id.notin_(excluded_prop_ids))
        )).scalar_one() or 0
    else:
        total_props = (await db.execute(select(func.count(Property.id)))).scalar_one() or 0

    active_leases_res = await db.execute(
        _lease_scope(
            select(func.count(Lease.id)).where(Lease.is_active.is_(True))
        )
    )
    total_leases_active = active_leases_res.scalar_one() or 0

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
    props_res = await db.execute(
        select(Property).where(Property.owner_user_id == proprietaire_id)
    )
    properties = list(props_res.scalars().all())
    prop_ids = [p.id for p in properties]

    if not prop_ids:
        return {
            "monthly_revenue_expected": 0,
            "monthly_revenue_received": 0,
            "total_properties": 0,
            "active_leases": 0,
        }

    # Revenus attendus = somme loyers+charges baux actifs
    expected_res = await db.execute(
        select(func.sum(Lease.rent_amount + Lease.charges_amount))
        .where(
            Lease.property_id.in_(prop_ids),
            Lease.is_active.is_(True),
        )
    )
    monthly_expected = float(expected_res.scalar_one() or 0)

    # Revenus encaissés ce mois (par période, cohérent avec le dashboard gestionnaire)
    today = date.today()

    received_res = await db.execute(
        select(func.sum(Payment.amount_paid))
        .join(Lease, Payment.lease_id == Lease.id)
        .where(
            Lease.property_id.in_(prop_ids),
            Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            Payment.period_year == today.year,
            Payment.period_month == today.month,
        )
    )
    monthly_received = float(received_res.scalar_one() or 0)

    active_leases_res = await db.execute(
        select(func.count(Lease.id))
        .where(Lease.property_id.in_(prop_ids), Lease.is_active.is_(True))
    )
    active_leases = active_leases_res.scalar_one() or 0

    return {
        "monthly_revenue_expected": round(monthly_expected, 2),
        "monthly_revenue_received": round(monthly_received, 2),
        "total_properties": len(properties),
        "active_leases": active_leases,
    }


@router.get("/fiscal/{year}", response_model=FiscalRevenueFoncier)
async def get_fiscal_revenues(
    year: int,
    proprietaire_id: Optional[uuid.UUID] = Query(None),
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
        Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
        Payment.period_year == year,
    ]

    # Part loyer réellement perçue = amount_paid × (amount_rent / amount_due)
    rent_res = await db.execute(
        select(
            func.sum(
                case(
                    (Payment.amount_due > 0,
                     Payment.amount_paid * Payment.amount_rent / Payment.amount_due),
                    else_=0.0,
                )
            )
        )
        .join(Lease, Payment.lease_id == Lease.id)
        .where(*_base_filter)
    )
    gross_rent = float(rent_res.scalar_one() or 0)

    # Part charges réellement perçue = amount_paid × (amount_charges / amount_due)
    charges_res = await db.execute(
        select(
            func.sum(
                case(
                    (Payment.amount_due > 0,
                     Payment.amount_paid * Payment.amount_charges / Payment.amount_due),
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
                        (Payment.amount_due > 0,
                         Payment.amount_paid * Payment.amount_rent / Payment.amount_due),
                        else_=0.0,
                    )
                )
            )
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop.id,
                Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                Payment.period_year == year,
            )
        )
        prop_rent = float(prop_rent_res.scalar_one() or 0)

        leases_res = await db.execute(
            select(func.count(Lease.id))
            .where(Lease.property_id == prop.id, Lease.is_active.is_(True))
        )
        leases_count = leases_res.scalar_one() or 0

        properties_detail.append({
            "property_id": str(prop.id),
            "property_name": prop.name,
            "address": prop.full_address,
            "annual_rent": round(prop_rent, 2),
            "active_leases": leases_count,
        })

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
    from app.core.permissions import Role as R
    from fastapi import HTTPException
    role = R(current_user.role)

    if role not in (R.PROPRIETAIRE, R.GESTIONNAIRE, R.GESTIONNAIRE_PROPRIO, R.ADMIN):
        raise HTTPException(status_code=403, detail="Accès refusé")

    proprietaire_id = current_user.id

    props_res = await db.execute(
        select(Property).where(Property.owner_user_id == proprietaire_id)
    )
    properties = list(props_res.scalars().all())

    today = date.today()
    months_elapsed = today.month if today.year == year else 12

    result_props = []
    for prop in properties:
        prop_id = prop.id

        # Loyer mensuel théorique = somme des baux actifs
        leases_res = await db.execute(
            select(
                func.coalesce(func.sum(Lease.rent_amount + Lease.charges_amount), 0.0)
            ).where(
                Lease.property_id == prop_id,
                Lease.is_active.is_(True),
            )
        )
        monthly_expected = float(leases_res.scalar_one() or 0)
        ytd_theoretical = monthly_expected * months_elapsed

        # Encaissé YTD (period_year == year, PAID ou PARTIAL)
        ytd_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop_id,
                Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                Payment.period_year == year,
            )
        )
        ytd_received = float(ytd_res.scalar_one() or 0)

        # Détail mensuel
        monthly_breakdown = []
        for month in range(1, months_elapsed + 1):
            m_res = await db.execute(
                select(func.coalesce(func.sum(Payment.amount_paid), 0.0))
                .join(Lease, Payment.lease_id == Lease.id)
                .where(
                    Lease.property_id == prop_id,
                    Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
                    Payment.period_year == year,
                    Payment.period_month == month,
                )
            )
            monthly_breakdown.append({
                "month": month,
                "expected": round(monthly_expected, 2),
                "received": round(float(m_res.scalar_one() or 0), 2),
            })

        collection_rate = round(
            (ytd_received / ytd_theoretical * 100) if ytd_theoretical > 0 else 0, 1
        )

        result_props.append({
            "property_id": str(prop_id),
            "property_name": prop.name,
            "monthly_expected": round(monthly_expected, 2),
            "ytd_theoretical": round(ytd_theoretical, 2),
            "ytd_received": round(ytd_received, 2),
            "collection_rate": collection_rate,
            "months_elapsed": months_elapsed,
            "monthly_breakdown": monthly_breakdown,
        })

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
