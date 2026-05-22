"""API Contacts — carnet d'adresses prestataires."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.contact import Contact, ContactCategory
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    search: Optional[str] = Query(None),
    category: Optional[ContactCategory] = Query(None),
    favorites_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(Contact)
    if search:
        term = f"%{search}%"
        q = q.where(or_(
            Contact.last_name.ilike(term),
            Contact.first_name.ilike(term),
            Contact.company_name.ilike(term),
            Contact.phone.ilike(term),
            Contact.email.ilike(term),
            Contact.city.ilike(term),
        ))
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
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    contact = Contact(**data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    await db.delete(contact)
    await db.commit()


@router.post("/{contact_id}/toggle-favorite", response_model=ContactResponse)
async def toggle_favorite(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    contact.is_favorite = not contact.is_favorite
    await db.commit()
    await db.refresh(contact)
    return contact
