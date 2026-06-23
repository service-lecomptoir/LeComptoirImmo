import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class CoproAssembly(Base, TimestampMixin):
    """Assemblée générale de copropriété (ordinaire ou extraordinaire)."""

    __tablename__ = "copro_assemblies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # ordinaire | extraordinaire
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="ordinaire")
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # draft | convened | held | closed
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    resolutions: Mapped[list["CoproResolution"]] = relationship(
        "CoproResolution",
        back_populates="assembly",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )


class CoproResolution(Base, TimestampMixin):
    """Point de l'ordre du jour soumis au vote, avec sa règle de majorité."""

    __tablename__ = "copro_resolutions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assembly_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_assemblies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Règle de majorité (loi du 10/07/1965) : art24 | art25 | art26 | unanimite
    majority: Mapped[str] = mapped_column(
        String(12), nullable=False, default="art24", server_default="art24"
    )
    # pending | adopted | rejected (calculé au dépouillement)
    outcome: Mapped[str] = mapped_column(
        String(12), nullable=False, default="pending", server_default="pending"
    )

    assembly: Mapped["CoproAssembly"] = relationship("CoproAssembly", back_populates="resolutions")
    votes: Mapped[list["CoproVote"]] = relationship(
        "CoproVote",
        back_populates="resolution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )


class CoproVote(Base, TimestampMixin):
    """Vote d'un copropriétaire sur une résolution (pondéré par ses tantièmes)."""

    __tablename__ = "copro_votes"
    __table_args__ = (UniqueConstraint("resolution_id", "owner_id", name="uq_copro_vote_owner"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resolution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_resolutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # pour | contre | abstention
    choice: Mapped[str] = mapped_column(String(12), nullable=False)

    resolution: Mapped["CoproResolution"] = relationship("CoproResolution", back_populates="votes")
