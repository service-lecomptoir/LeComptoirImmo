"""
Modèles SQLAlchemy légers qui mappent les tables existantes de LeComptoirImmo.
Alice les utilise en lecture/écriture (blocage cascade) sans modifier le schéma LeCI.
Ces modèles utilisent une Base séparée pour éviter les conflits avec la Base de Alice.
"""
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum, cast, literal
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func


class LeciBase(DeclarativeBase):
    """Base séparée pour les modèles LeCI — évite les conflits de métadonnées."""
    pass


class LeciUser(LeciBase):
    __tablename__ = "users"
    # Indique à SQLAlchemy de ne pas essayer de créer/modifier cette table
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # user_role est un enum PostgreSQL dans LeCI. On le mappe sur le MÊME type enum
    # (create_type=False) pour que les INSERT émettent le bon cast ::user_role.
    # Les WHERE continuent d'utiliser cast(..., String) via role_eq().
    role: Mapped[str] = mapped_column(
        SAEnum(
            "admin", "gestionnaire", "gestionnaire_proprio",
            "proprietaire", "locataire", "lecture",
            name="user_role", create_type=False,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Coordonnées (profil LeCI) — peuplées depuis Alice à la création
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LeciUser {self.email} [{self.role}]>"

    @classmethod
    def role_eq(cls, role_value: str):
        """Retourne un filtre WHERE compatible avec l'enum user_role de PostgreSQL.

        Ex: select(LeciUser).where(LeciUser.role_eq('gestionnaire'))
        """
        return cast(cls.role, String) == role_value


class LeciProperty(LeciBase):
    __tablename__ = "properties"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # created_by = ID du gestionnaire qui a créé ce bien
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    # owner_user_id = ID du propriétaire associé
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<LeciProperty {self.name}>"


class LeciUnit(LeciBase):
    __tablename__ = "units"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False
    )

    def __repr__(self) -> str:
        return f"<LeciUnit {self.id}>"


class LeciTenant(LeciBase):
    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<LeciTenant {self.id}>"


class LeciLease(LeciBase):
    __tablename__ = "leases"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id"), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<LeciLease {self.id}>"
