"""API Contacts — carnet d'adresses prestataires."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire
from app.core.permissions import Role
from app.database import get_db
from app.models.contact import Contact, ContactCategory
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactResponse, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["Contacts"])


async def _check_contact_access(contact: Contact, current_user: User, db: AsyncSession) -> None:
    """Vérifie que l'utilisateur a le droit d'accéder à ce contact."""
    role = Role(current_user.role)
    if role == Role.ADMIN:
        return
    if role == Role.GESTIONNAIRE_PROPRIO:
        if contact.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Accès refusé")
    elif role == Role.GESTIONNAIRE:
        # Un mandataire n'accède qu'aux contacts de SON agence
        from app.api.v1._isolation import agency_member_ids

        members = await agency_member_ids(db, current_user)
        if contact.created_by not in members:
            raise HTTPException(status_code=403, detail="Accès refusé")


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    search: str | None = Query(None),
    category: ContactCategory | None = Query(None),
    favorites_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    role = Role(current_user.role)
    q = select(Contact)

    # ── Scope par rôle ────────────────────────────────────────────────────────
    if role == Role.GESTIONNAIRE_PROPRIO:
        # GP voit uniquement ses propres contacts
        q = q.where(Contact.created_by == current_user.id)
    elif role == Role.GESTIONNAIRE:
        # Mandataire : uniquement les contacts de SON agence
        from app.api.v1._isolation import agency_member_ids

        members = await agency_member_ids(db, current_user)
        q = q.where(Contact.created_by.in_(members)) if members else q.where(False)
    # Admin : pas de filtre

    # ── Filtres utilisateur ───────────────────────────────────────────────────
    if search:
        term = f"%{search}%"
        q = q.where(
            or_(
                Contact.last_name.ilike(term),
                Contact.first_name.ilike(term),
                Contact.company_name.ilike(term),
                Contact.phone.ilike(term),
                Contact.email.ilike(term),
                Contact.city.ilike(term),
            )
        )
    if category:
        q = q.where(Contact.category == category)
    if favorites_only:
        q = q.where(Contact.is_favorite.is_(True))
    q = q.order_by(Contact.last_name, Contact.first_name).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    contact = Contact(**data.model_dump(), created_by=current_user.id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    await _check_contact_access(contact, current_user, db)
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    await _check_contact_access(contact, current_user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    await _check_contact_access(contact, current_user, db)
    await db.delete(contact)
    await db.commit()


@router.post("/{contact_id}/toggle-favorite", response_model=ContactResponse)
async def toggle_favorite(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    await _check_contact_access(contact, current_user, db)
    contact.is_favorite = not contact.is_favorite
    await db.commit()
    await db.refresh(contact)
    return contact
