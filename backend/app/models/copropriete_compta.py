import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class CoproBudget(Base, TimestampMixin):
    """Budget prévisionnel annuel d'une copropriété, ventilé en postes rattachés
    à des clés de répartition. Les appels de fonds en découlent."""

    __tablename__ = "copro_budgets"
    __table_args__ = (UniqueConstraint("copropriete_id", "year", name="uq_copro_budget_year"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Périodicité des appels de fonds : mensuel | trimestriel | semestriel | annuel.
    periodicity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="trimestriel", server_default="trimestriel"
    )
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    lines: Mapped[list["CoproBudgetLine"]] = relationship(
        "CoproBudgetLine",
        back_populates="budget",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )
    calls: Mapped[list["CoproFundCall"]] = relationship(
        "CoproFundCall",
        back_populates="budget",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )


class CoproBudgetLine(Base, TimestampMixin):
    """Poste de budget (ex. « Ascenseur : entretien ») rattaché à une clé de
    répartition (détermine la ventilation par lot)."""

    __tablename__ = "copro_budget_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_repartition_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    budget: Mapped["CoproBudget"] = relationship("CoproBudget", back_populates="lines")


class CoproFundCall(Base, TimestampMixin):
    """Appel de fonds pour une période (campagne) : génère un item par lot."""

    __tablename__ = "copro_fund_calls"
    __table_args__ = (UniqueConstraint("budget_id", "period_index", name="uq_copro_call_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..n selon périodicité
    period_label: Mapped[str] = mapped_column(String(40), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    budget: Mapped["CoproBudget"] = relationship("CoproBudget", back_populates="calls")
    items: Mapped[list["CoproFundCallItem"]] = relationship(
        "CoproFundCallItem",
        back_populates="call",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )


class CoproFundCallItem(Base, TimestampMixin):
    """Quote-part d'un appel de fonds pour un lot / copropriétaire : dû et payé."""

    __tablename__ = "copro_fund_call_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_fund_calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("copro_lots.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="pending", server_default="pending"
    )  # pending | partial | paid

    call: Mapped["CoproFundCall"] = relationship("CoproFundCall", back_populates="items")
    payments: Mapped[list["CoproPayment"]] = relationship(
        "CoproPayment",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )


class CoproExpense(Base, TimestampMixin):
    """Dépense réelle de la copropriété pour une année, rattachée à une clé de
    répartition. Sert à la régularisation annuelle (réel vs provisions appelées)."""

    __tablename__ = "copro_expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_repartition_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CoproPayment(Base, TimestampMixin):
    """Encaissement d'un copropriétaire sur une quote-part d'appel de fonds."""

    __tablename__ = "copro_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_fund_call_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    item: Mapped["CoproFundCallItem"] = relationship("CoproFundCallItem", back_populates="payments")
