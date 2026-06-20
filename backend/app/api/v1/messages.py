"""API Messages — communication propriétaire ↔ gestionnaire."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.permissions import Role
from app.database import get_db
from app.models.message import ProprietaireMessage
from app.models.user import User

router = APIRouter(prefix="/proprietaire-messages", tags=["Messages propriétaire"])


class MessageCreate(BaseModel):
    content: str
    proprietaire_id: uuid.UUID | None = None  # Requis si gestionnaire envoie le message


def _serialize(msg: ProprietaireMessage) -> dict:
    return {
        "id": str(msg.id),
        "proprietaire_id": str(msg.proprietaire_id),
        "sender_id": str(msg.sender_id),
        "sender_name": msg.sender.full_name if msg.sender else None,
        "content": msg.content,
        "is_from_gestionnaire": msg.is_from_gestionnaire,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.get("")
async def list_messages(
    proprietaire_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    - Propriétaire : liste ses propres messages avec le gestionnaire
    - Gestionnaire/Admin : liste les messages d'un propriétaire donné (proprietaire_id requis)
    """
    role = Role(current_user.role)

    if role == Role.PROPRIETAIRE:
        target_id = current_user.id
        # Marquer comme lus les messages du gestionnaire à destination du propriétaire
        await db.execute(
            update(ProprietaireMessage)
            .where(
                ProprietaireMessage.proprietaire_id == target_id,
                ProprietaireMessage.is_from_gestionnaire.is_(True),
                ProprietaireMessage.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await db.commit()
    elif role in (Role.GESTIONNAIRE, Role.ADMIN):
        # Mandataire : limiter aux propriétaires de SON agence (owner.created_by ∈ agence).
        allowed_prop_ids = None  # None = admin (tous)
        if role == Role.GESTIONNAIRE:
            from app.api.v1._isolation import agency_member_ids
            from app.models.owner import Owner

            members = await agency_member_ids(db, current_user)
            rows = await db.execute(
                select(Owner.user_id).where(
                    Owner.created_by.in_(members), Owner.user_id.isnot(None)
                )
            )
            allowed_prop_ids = {str(u) for u in rows.scalars().all()}
        if not proprietaire_id:
            # Retourner la liste des conversations (un résumé par propriétaire)
            res = await db.execute(
                select(ProprietaireMessage.proprietaire_id)
                .distinct()
                .order_by(ProprietaireMessage.proprietaire_id)
            )
            ids = [row[0] for row in res.all()]
            if allowed_prop_ids is not None:
                ids = [pid for pid in ids if str(pid) in allowed_prop_ids]
            conversations = []
            for pid in ids:
                # Dernier message
                last_res = await db.execute(
                    select(ProprietaireMessage)
                    .options(selectinload(ProprietaireMessage.sender))
                    .options(selectinload(ProprietaireMessage.proprietaire))
                    .where(ProprietaireMessage.proprietaire_id == pid)
                    .order_by(ProprietaireMessage.created_at.desc())
                    .limit(1)
                )
                last = last_res.scalar_one_or_none()
                if last:
                    unread_res = await db.execute(
                        select(ProprietaireMessage).where(
                            ProprietaireMessage.proprietaire_id == pid,
                            ProprietaireMessage.is_from_gestionnaire.is_(False),
                            ProprietaireMessage.is_read.is_(False),
                        )
                    )
                    unread = len(list(unread_res.scalars().all()))
                    conversations.append(
                        {
                            "proprietaire_id": str(pid),
                            "proprietaire_name": last.proprietaire.full_name
                            if last.proprietaire
                            else "?",
                            "last_message": last.content[:80],
                            "last_message_at": last.created_at.isoformat()
                            if last.created_at
                            else None,
                            "unread_count": unread,
                        }
                    )
            return {"conversations": conversations}
        if allowed_prop_ids is not None and str(proprietaire_id) not in allowed_prop_ids:
            raise HTTPException(status_code=403, detail="Accès refusé")
        target_id = proprietaire_id
    else:
        raise HTTPException(status_code=403, detail="Accès refusé")

    result = await db.execute(
        select(ProprietaireMessage)
        .options(selectinload(ProprietaireMessage.sender))
        .where(ProprietaireMessage.proprietaire_id == target_id)
        .order_by(ProprietaireMessage.created_at.asc())
    )
    messages = list(result.scalars().all())
    return {"messages": [_serialize(m) for m in messages]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envoyer un message."""
    role = Role(current_user.role)

    if role == Role.PROPRIETAIRE:
        proprietaire_id = current_user.id
        is_from_gestionnaire = False
    elif role in (Role.GESTIONNAIRE, Role.ADMIN):
        if not data.proprietaire_id:
            raise HTTPException(
                status_code=400, detail="proprietaire_id requis pour le gestionnaire"
            )
        # Vérifier que le propriétaire existe
        owner = await db.get(User, data.proprietaire_id)
        if not owner:
            raise HTTPException(status_code=404, detail="Propriétaire introuvable")
        proprietaire_id = data.proprietaire_id
        is_from_gestionnaire = True
    else:
        raise HTTPException(status_code=403, detail="Accès refusé")

    msg = ProprietaireMessage(
        proprietaire_id=proprietaire_id,
        sender_id=current_user.id,
        content=data.content.strip(),
        is_from_gestionnaire=is_from_gestionnaire,
        is_read=False,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg, ["sender"])
    return _serialize(msg)


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nombre de messages non lus."""
    role = Role(current_user.role)
    if role == Role.PROPRIETAIRE:
        res = await db.execute(
            select(ProprietaireMessage).where(
                ProprietaireMessage.proprietaire_id == current_user.id,
                ProprietaireMessage.is_from_gestionnaire.is_(True),
                ProprietaireMessage.is_read.is_(False),
            )
        )
        count = len(list(res.scalars().all()))
    elif role in (Role.GESTIONNAIRE, Role.ADMIN):
        res = await db.execute(
            select(ProprietaireMessage).where(
                ProprietaireMessage.is_from_gestionnaire.is_(False),
                ProprietaireMessage.is_read.is_(False),
            )
        )
        count = len(list(res.scalars().all()))
    else:
        count = 0
    return {"unread": count}
