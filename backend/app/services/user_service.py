import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, UserPasswordUpdate
from app.core.security import hash_password, verify_password
from app.core.permissions import Role
from app.core.exceptions import (
    NotFoundException, ConflictException, BadRequestException
)


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

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            created_by=created_by,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
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
        # Coordonnées (servent au règlement du locataire)
        if data.phone is not None:
            user.phone = data.phone or None
        if data.address is not None:
            user.address = data.address or None
        # RIB (coordonnées bancaires du propriétaire)
        if data.iban is not None:
            user.iban = data.iban or None
        if data.bic is not None:
            user.bic = data.bic or None
        if data.bank_holder is not None:
            user.bank_holder = data.bank_holder or None

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
    async def delete(db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await UserService.get_by_id(db, user_id)
        await db.delete(user)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(User.id)))
        return result.scalar_one()
