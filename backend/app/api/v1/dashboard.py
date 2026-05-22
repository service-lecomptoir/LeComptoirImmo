"""API Dashboard — statistiques avancées pour aide à la décision."""
import uuid
from typing import Optional
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.property import Property
from app.models.unit import Unit
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

    # ── Propriétés & Unités ───────────────────────────────────────────────────
    total_units_res = await db.execute(select(func.count(Unit.id)))
    total_units = total_units_res.scalar_one() or 0

    occupied_units_res = await db.execute(
        select(func.count(func.distinct(Lease.unit_id)))
        .where(Lease.is_active.is_(True))
    )
    occupied_units = occupied_units_res.scalar_one() or 0
    vacant_units = max(0, total_units - occupied_units)
    occupancy_rate = round((occupied_units / total_units * 100) if total_units else 0, 1)

    # ── Finances ──────────────────────────────────────────────────────────────
    # Loyers attendus ce mois
    rent_expected_res = await db.execute(
        select(func.sum(Lease.rent_amount + Lease.charges_amount))
        .where(Lease.is_active.is_(True))
    )
    total_rent_expected = float(rent_expected_res.scalar_one() or 0)

    # Paiements reçus ce mois
    start_month = date(today.year, today.month, 1)
    rent_received_res = await db.execute(
        select(func.sum(Payment.amount_paid))
        .where(
            Payment.status == PaymentStatus.PAYE,
            Payment.payment_date >= start_month,
        )
    )
    total_rent_received = float(rent_received_res.scalar_one() or 0)

    # Impayés (montant total des paiements en retard)
    outstanding_res = await db.execute(
        select(func.sum(Payment.amount_due - Payment.amount_paid))
        .where(
            Payment.status.in_([PaymentStatus.EN_ATTENTE, PaymentStatus.RETARD]),
            Payment.due_date < today,
        )
    )
    total_outstanding = float(outstanding_res.scalar_one() or 0)
    collection_rate = round(
        (total_rent_received / total_rent_expected * 100) if total_rent_expected else 0, 1
    )

    # Dépôts de garantie
    deposits_res = await db.execute(
        select(func.sum(Lease.deposit_amount)).where(Lease.is_active.is_(True))
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
            select(func.sum(Lease.rent_amount + Lease.charges_amount))
            .where(
                Lease.is_active.is_(True),
                Lease.start_date <= month_end,
            )
        )
        expected = float(exp_res.scalar_one() or 0)

        rec_res = await db.execute(
            select(func.sum(Payment.amount_paid))
            .where(
                Payment.status == PaymentStatus.PAYE,
                Payment.payment_date >= month_start,
                Payment.payment_date < month_end,
            )
        )
        received = float(rec_res.scalar_one() or 0)

        out_res = await db.execute(
            select(func.sum(Payment.amount_due - Payment.amount_paid))
            .where(
                Payment.status.in_([PaymentStatus.EN_ATTENTE, PaymentStatus.RETARD]),
                Payment.due_date >= month_start,
                Payment.due_date < month_end,
            )
        )
        outstanding = float(out_res.scalar_one() or 0)

        monthly_revenues.append(MonthlyRevenue(
            month=month_str,
            expected=round(expected, 2),
            received=round(received, 2),
            outstanding=round(outstanding, 2),
        ))

    # ── Top propriétés ────────────────────────────────────────────────────────
    props_res = await db.execute(select(Property).limit(10))
    properties = props_res.scalars().all()
    top_properties = []
    for prop in properties:
        units_res = await db.execute(
            select(func.count(Unit.id)).where(Unit.property_id == prop.id)
        )
        units_count = units_res.scalar_one() or 0

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
                Payment.status.in_([PaymentStatus.EN_ATTENTE, PaymentStatus.RETARD]),
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
        select(func.count(Lease.id)).where(
            Lease.is_active.is_(True),
            Lease.end_date.between(today, today + timedelta(days=30)),
        )
    )
    expiring_30 = expiring_30_res.scalar_one() or 0

    expiring_90_res = await db.execute(
        select(func.count(Lease.id)).where(
            Lease.is_active.is_(True),
            Lease.end_date.between(today, today + timedelta(days=90)),
        )
    )
    expiring_90 = expiring_90_res.scalar_one() or 0

    overdue_count_res = await db.execute(
        select(func.count(Payment.id)).where(
            Payment.status.in_([PaymentStatus.EN_ATTENTE, PaymentStatus.RETARD]),
            Payment.due_date < today,
        )
    )
    overdue_payments = overdue_count_res.scalar_one() or 0

    overdue_amount_res = await db.execute(
        select(func.sum(Payment.amount_due - Payment.amount_paid)).where(
            Payment.status.in_([PaymentStatus.EN_ATTENTE, PaymentStatus.RETARD]),
            Payment.due_date < today,
        )
    )
    overdue_amount = float(overdue_amount_res.scalar_one() or 0)

    # ── Totaux généraux ───────────────────────────────────────────────────────
    total_tenants_res = await db.execute(select(func.count(Tenant.id)))
    total_tenants = total_tenants_res.scalar_one() or 0

    total_props_res = await db.execute(select(func.count(Property.id)))
    total_props = total_props_res.scalar_one() or 0

    active_leases_res = await db.execute(
        select(func.count(Lease.id)).where(Lease.is_active.is_(True))
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
        top_properties=top_properties[:5],
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

    # Propriétaire ne voit que ses propres données
    if role == R.PROPRIETAIRE:
        proprietaire_id = current_user.id

    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

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

    # Loyers encaissés
    rent_res = await db.execute(
        select(func.sum(Payment.amount_paid))
        .join(Lease, Payment.lease_id == Lease.id)
        .where(
            Lease.property_id.in_(prop_ids),
            Payment.status == PaymentStatus.PAYE,
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
        )
    )
    gross_rent = float(rent_res.scalar_one() or 0)

    # Charges récupérables encaissées
    charges_res = await db.execute(
        select(func.sum(Lease.charges_amount))
        .where(
            Lease.property_id.in_(prop_ids),
            Lease.is_active.is_(True),
        )
    )
    charges_annual = float(charges_res.scalar_one() or 0) * 12

    # Frais de gestion estimés (8% des loyers bruts — valeur par défaut)
    management_fees = round(gross_rent * 0.08, 2)

    # Détail par bien
    properties_detail = []
    for prop in properties:
        prop_rent_res = await db.execute(
            select(func.sum(Payment.amount_paid))
            .join(Lease, Payment.lease_id == Lease.id)
            .where(
                Lease.property_id == prop.id,
                Payment.status == PaymentStatus.PAYE,
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
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
