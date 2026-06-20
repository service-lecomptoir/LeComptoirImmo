import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.tenant import Tenant


class AvisEcheanceStatus(str, Enum):
    BROUILLON = "brouillon"  # Généré, pas encore envoyé
    ENVOYE = "envoye"  # Marqué comme envoyé
    ACQUITTE = "acquitte"  # Loyer payé


class AvisEcheance(Base, TimestampMixin):
    __tablename__ = "avis_echeances"
    __table_args__ = (
        # Unicité d'un avis de LOYER par bail/période (index partiel : les avis
        # d'apurement, kind='apurement', ne sont pas concernés et peuvent coexister
        # sur la même période ; ils sont dédupliqués par (plan_id, installment_seq)).
        Index(
            "uq_avis_loyer_period",
            "lease_id",
            "period_year",
            "period_month",
            unique=True,
            postgresql_where=text("kind = 'loyer'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Liens ─────────────────────────────────────────────────────────────────
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Période ───────────────────────────────────────────────────────────────
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Période réellement couverte (selon la règle d'appel + prorata d'entrée/sortie).
    # Nullable pour compat avec les avis générés avant cette fonctionnalité.
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Montants ──────────────────────────────────────────────────────────────
    amount_rent: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_charges: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    amount_apl: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    amount_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # ── Type d'avis ───────────────────────────────────────────────────────────
    # 'loyer' (appel de loyer classique) ou 'apurement' (échéance d'un plan).
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="loyer")
    # Pour un avis d'apurement : plan + n° d'échéance (sinon NULL).
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    installment_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Statut & envoi ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        SAEnum(
            AvisEcheanceStatus,
            name="avis_echeance_status_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AvisEcheanceStatus.BROUILLON,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    # NULL = généré automatiquement par le scheduler
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    lease: Mapped["Lease"] = relationship("Lease", lazy="select")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")

    @property
    def period_label(self) -> str:
        months = [
            "",
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
            "Juillet",
            "Août",
            "Septembre",
            "Octobre",
            "Novembre",
            "Décembre",
        ]
        return f"{months[self.period_month]} {self.period_year}"

    @property
    def period_range_label(self) -> str:
        """Période réellement couverte, ex. « du 15/01/2026 au 14/02/2026 »
        (ou le mois si les dates ne sont pas renseignées : anciens avis)."""
        if self.period_start and self.period_end:
            return (
                f"du {self.period_start.strftime('%d/%m/%Y')} "
                f"au {self.period_end.strftime('%d/%m/%Y')}"
            )
        return self.period_label

    @property
    def is_auto_generated(self) -> bool:
        return self.generated_by is None

    def __repr__(self) -> str:
        return f"<AvisEcheance {self.period_label} : {self.status}>"
