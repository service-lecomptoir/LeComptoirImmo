"""Schémas pour le dashboard avancé."""

from datetime import date

from pydantic import BaseModel


class UpcomingEntretien(BaseModel):
    id: str
    title: str
    type: str
    status: str
    scheduled_date: date
    property_label: str | None = None
    overdue: bool = False


class OccupancyStats(BaseModel):
    total_units: int
    occupied_units: int
    vacant_units: int
    occupancy_rate: float  # %


class FinancialStats(BaseModel):
    total_rent_expected: float
    total_rent_received: float
    total_outstanding: float
    collection_rate: float  # %
    total_deposits: float


class MonthlyRevenue(BaseModel):
    month: str  # "2026-01"
    expected: float
    received: float
    outstanding: float


class PropertyStats(BaseModel):
    property_id: str
    property_name: str
    units_count: int
    occupied_count: int
    monthly_revenue: float
    outstanding: float


class OwnerBreakdown(BaseModel):
    """Ventilation des indicateurs par propriétaire (vue mandataire)."""

    owner_name: str
    properties_count: int
    occupied_count: int
    monthly_revenue: float
    outstanding: float


class AlertStats(BaseModel):
    leases_expiring_30d: int
    leases_expiring_90d: int
    overdue_payments: int
    overdue_amount: float
    tenants_no_insurance: int


class DashboardStats(BaseModel):
    occupancy: OccupancyStats
    financial: FinancialStats
    monthly_revenues: list[MonthlyRevenue]
    top_properties: list[PropertyStats]
    by_owner: list[OwnerBreakdown] = []
    alerts: AlertStats
    total_tenants: int
    total_properties: int
    total_leases_active: int
    upcoming_entretiens: list[UpcomingEntretien] = []


class FiscalRevenueFoncier(BaseModel):
    year: int
    proprietaire_id: str
    proprietaire_name: str

    # Revenus bruts
    gross_rent_revenue: float
    charges_received: float
    total_gross_revenue: float

    # Charges déductibles
    repairs_charges: float
    management_fees: float
    insurance_charges: float
    property_tax: float
    other_charges: float
    total_deductible: float

    # Net
    net_revenue: float

    # Détail par bien
    properties: list[dict]
