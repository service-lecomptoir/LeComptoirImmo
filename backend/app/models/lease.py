import uuid
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.property import Property
    from app.models.tenant import Tenant


# ── Association co-titulaires (locataires secondaires d'un contrat) ────────────
# Le locataire PRINCIPAL reste Lease.tenant_id. Cette table porte les secondaires.
lease_tenants = Table(
    "lease_tenants",
    Base.metadata,
    Column(
        "lease_id",
        UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tenant_id",
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class LeaseType(str, Enum):
    VIDE = "vide"
    MEUBLE = "meuble"
    MOBILITE = "mobilite"
    COMMERCIAL = "commercial"


class PaymentMethod(str, Enum):
    VIREMENT = "virement"
    CHEQUE = "cheque"
    PRELEVEMENT = "prelevement"
    ESPECES = "especes"
    CARTE = "carte"  # paiement en ligne (Stripe / SumUp)


class RentCallRule(str, Enum):
    """Règle d'appel de loyer : période contractuelle (basée sur la date d'entrée du
    bail) ou période calendaire (du 1er au dernier jour du mois)."""

    CONTRACTUELLE = "contractuelle"
    CALENDRIER = "calendrier"


class PaymentFrequency(str, Enum):
    """Fréquence d'appel du loyer."""

    MENSUELLE = "mensuelle"
    BIMESTRIELLE = "bimestrielle"
    TRIMESTRIELLE = "trimestrielle"
    SEMESTRIELLE = "semestrielle"
    ANNUELLE = "annuelle"


class Lease(Base, TimestampMixin):
    __tablename__ = "leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Liens ─────────────────────────────────────────────────────────────────
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Type de contrat ───────────────────────────────────────────────────────
    lease_type: Mapped[str] = mapped_column(
        SAEnum(
            LeaseType,
            name="lease_type_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=LeaseType.VIDE,
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notice_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Finances ──────────────────────────────────────────────────────────────
    rent_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    charges_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_method: Mapped[str] = mapped_column(
        SAEnum(
            PaymentMethod,
            name="payment_method_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PaymentMethod.VIREMENT,
    )
    # Règle d'appel de loyer (stockée en texte pour éviter un type enum PG dédié)
    rent_call_rule: Mapped[str] = mapped_column(
        String(20), nullable=False, default="calendrier", server_default="calendrier"
    )
    # Fréquence d'appel du loyer (texte, comme rent_call_rule)
    payment_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="mensuelle", server_default="mensuelle"
    )

    # ── Révision du loyer (IRL) ─────────────────────────────────────────────────
    # Trimestre de référence (1..4) et indice IRL de référence (valeur au dernier
    # calage), + date de la dernière révision. Révision annuelle à l'anniversaire.
    irl_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    irl_base_index: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    last_revision_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── APL ───────────────────────────────────────────────────────────────────
    apl_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    apl_tiers_payant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Garant ────────────────────────────────────────────────────────────────
    has_guarantor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guarantor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guarantor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guarantor_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ── État ──────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Suivi de la relation locataire (scoring) ────────────────────────────────
    # Liste d'événements éditables : [{id, date, kind, note, author_name, created_at}].
    # Le « kind » porte une polarité/poids qui alimente le score de qualité de payeur.
    relationship_events: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="leases")
    # Co-titulaires secondaires (le principal est `tenant` ci-dessus)
    co_tenants: Mapped[list["Tenant"]] = relationship(
        "Tenant",
        secondary=lease_tenants,
        lazy="selectin",
    )
    parent_property: Mapped["Property"] = relationship("Property", back_populates="leases")
    inspections: Mapped[list["Inspection"]] = relationship(
        "Inspection", back_populates="lease", lazy="select", cascade="all, delete-orphan"
    )

    @property
    def total_monthly(self) -> float:
        return float(self.rent_amount) + float(self.charges_amount)

    @property
    def net_rent(self) -> float:
        """Loyer net après déduction APL tiers-payant."""
        if self.apl_tiers_payant and self.apl_amount:
            return max(0.0, float(self.rent_amount) - float(self.apl_amount))
        return float(self.rent_amount)

    @property
    def all_tenants(self) -> list["Tenant"]:
        """Locataires du contrat : principal en premier, puis co-titulaires."""
        result = [self.tenant] if self.tenant else []
        result += list(self.co_tenants or [])
        return result

    @property
    def all_tenant_names(self) -> str:
        """Noms de tous les co-titulaires, séparés par ' & '."""
        return " & ".join(t.full_name for t in self.all_tenants)

    def __repr__(self) -> str:
        return f"<Lease {self.id} : actif={self.is_active}>"
