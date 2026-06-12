import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, UserPasswordUpdate
from app.core.security import hash_password, verify_password
from app.core.exceptions import (
    NotFoundException, ConflictException, BadRequestException
)
from app.utils.address import normalize_address_fields


class UserService:

    @staticmethod
    async def create(
        db: AsyncSession,
        data: UserCreate,
        created_by: Optional[uuid.UUID] = None,
    ) -> User:
        """Crée un nouvel utilisateur après vérification de l'unicité de l'email."""
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise ConflictException(f"L'email '{data.email}' est déjà utilisé")

        # Agence : un sous-compte hérite de l'agence de son créateur ; un compte
        # principal (sans créateur) est sa propre agence.
        agency_id = None
        if created_by is not None:
            creator = (await db.execute(select(User).where(User.id == created_by))).scalar_one_or_none()
            if creator is not None:
                agency_id = creator.agency_id or creator.id

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            created_by=created_by,
            agency_id=agency_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        # Compte principal : son agence est lui-même.
        if user.agency_id is None:
            user.agency_id = user.id
            await db.flush()

        # Templates de documents par défaut pour les comptes qui génèrent des documents
        # (gestionnaire / GP / admin). N'échoue jamais la création de compte.
        try:
            from app.services.document_template_service import (
                TEMPLATE_OWNER_ROLES, ensure_default_templates,
            )
            role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
            if role_val in TEMPLATE_OWNER_ROLES:
                await ensure_default_templates(db, user.id)
        except Exception:
            pass

        return user

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("Utilisateur", str(user_id))
        return user

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> List[User]:
        result = await db.execute(select(User).order_by(User.full_name))
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession, user_id: uuid.UUID, data: UserUpdate
    ) -> User:
        user = await UserService.get_by_id(db, user_id)

        if data.email and data.email != user.email:
            existing = await UserService.get_by_email(db, data.email)
            if existing:
                raise ConflictException(f"L'email '{data.email}' est déjà utilisé")
            user.email = data.email

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.is_active is not None:
            user.is_active = data.is_active
        # Coordonnées du compte (agence/gestionnaire). Le RIB du bailleur est
        # désormais porté par la fiche propriétaire (table owners), pas le compte.
        if data.phone is not None:
            user.phone = data.phone or None
            # Le téléphone du compte est lié à la fiche locataire rattachée : on
            # propage la modif (« Mes informations » du locataire → fiche locataire).
            from app.models.tenant import Tenant
            linked = (await db.execute(
                select(Tenant).where(Tenant.user_id == user.id)
            )).scalar_one_or_none()
            if linked is not None and (linked.phone or None) != (user.phone or None):
                linked.phone = user.phone or None
        if data.address is not None:
            user.address = data.address or None
        if getattr(data, "zip_code", None) is not None:
            user.zip_code = data.zip_code or None
        if getattr(data, "city", None) is not None:
            user.city = data.city or None
        if getattr(data, "country", None) is not None:
            user.country = data.country or None
        # Normalisation « comme via l'autocomplétion » : si l'adresse est combinée
        # (rue + CP + ville d'un seul tenant) ou duplique le CP, on la découpe.
        user.address, user.zip_code, user.city = normalize_address_fields(
            user.address, user.zip_code, user.city
        )
        if getattr(data, "template_pinned_vars", None) is not None:
            user.template_pinned_vars = data.template_pinned_vars or None
        if getattr(data, "owner_kind", None) in ("personne", "societe"):
            user.owner_kind = data.owner_kind
        if getattr(data, "owner_full_name", None) is not None:
            user.owner_full_name = data.owner_full_name or None
        if getattr(data, "owner_company", None) is not None:
            user.owner_company = data.owner_company or None
        if getattr(data, "owner_national_id", None) is not None:
            user.owner_national_id = data.owner_national_id or None
        if getattr(data, "signature", None) is not None:
            user.signature = data.signature or None

        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_role(
        db: AsyncSession, user_id: uuid.UUID, data: UserRoleUpdate
    ) -> User:
        user = await UserService.get_by_id(db, user_id)
        user.role = data.role
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_password(
        db: AsyncSession, user: User, data: UserPasswordUpdate
    ) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise BadRequestException("Mot de passe actuel incorrect")
        user.hashed_password = hash_password(data.new_password)
        await db.flush()

    @staticmethod
    async def admin_set_password(
        db: AsyncSession, user_id: uuid.UUID, new_password: str
    ) -> None:
        """Réinitialise le mot de passe sans vérifier l'ancien (action gestionnaire/admin)."""
        user = await UserService.get_by_id(db, user_id)
        user.hashed_password = hash_password(new_password)
        await db.flush()

    @staticmethod
    async def delete(db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await UserService.get_by_id(db, user_id)
        await db.delete(user)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(User.id)))
        return result.scalar_one()
