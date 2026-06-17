"""API Modèles de courrier multilingues (onglet Communication)."""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_gestionnaire
from app.models.user import User
from app.models.message_template import MessageTemplate, TEMPLATE_LANGS

router = APIRouter(prefix="/message-templates", tags=["Modèles de courrier"])


class MTCreate(BaseModel):
    rule_type: str
    name: str
    content: Dict[str, Any] = {}
    is_selected: bool = False


class MTUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MTResponse(BaseModel):
    id: uuid.UUID
    gestionnaire_id: Optional[uuid.UUID] = None
    rule_type: str
    name: str
    content: Dict[str, Any] = {}
    is_selected: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


def _clean_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """Ne garde que les langues connues et les clés subject/body/sms (chaînes)."""
    out: Dict[str, Any] = {}
    for lang, v in (content or {}).items():
        if lang not in TEMPLATE_LANGS or not isinstance(v, dict):
            continue
        out[lang] = {k: (str(v.get(k) or "")) for k in ("subject", "body", "sms")}
    return out


async def _owned(db: AsyncSession, tpl_id: uuid.UUID, user: User) -> MessageTemplate:
    tpl = await db.get(MessageTemplate, tpl_id)
    if tpl is None or tpl.gestionnaire_id != user.id:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return tpl


async def _unselect_others(db: AsyncSession, user_id, rule_type: str, keep_id) -> None:
    rows = (await db.execute(select(MessageTemplate).where(
        MessageTemplate.gestionnaire_id == user_id,
        MessageTemplate.rule_type == rule_type,
        MessageTemplate.is_selected.is_(True),
    ))).scalars().all()
    for r in rows:
        if r.id != keep_id:
            r.is_selected = False


@router.get("", response_model=List[MTResponse])
async def list_templates(
    rule_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    q = select(MessageTemplate).where(MessageTemplate.gestionnaire_id == current_user.id)
    if rule_type:
        q = q.where(MessageTemplate.rule_type == rule_type)
    q = q.order_by(MessageTemplate.rule_type, MessageTemplate.name)
    return list((await db.execute(q)).scalars().all())


@router.post("", response_model=MTResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: MTCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    tpl = MessageTemplate(
        gestionnaire_id=current_user.id, rule_type=data.rule_type, name=data.name,
        content=_clean_content(data.content), is_selected=data.is_selected,
    )
    db.add(tpl)
    await db.flush()
    if data.is_selected:
        await _unselect_others(db, current_user.id, data.rule_type, tpl.id)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.patch("/{tpl_id}", response_model=MTResponse)
async def update_template(
    tpl_id: uuid.UUID,
    data: MTUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    tpl = await _owned(db, tpl_id, current_user)
    if data.name is not None:
        tpl.name = data.name
    if data.content is not None:
        tpl.content = _clean_content(data.content)
    if data.is_active is not None:
        tpl.is_active = data.is_active
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.post("/{tpl_id}/select", response_model=MTResponse)
async def select_template(
    tpl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Marque ce modèle comme celui utilisé pour son type (désélectionne les autres)."""
    tpl = await _owned(db, tpl_id, current_user)
    tpl.is_selected = True
    tpl.is_active = True
    await _unselect_others(db, current_user.id, tpl.rule_type, tpl.id)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/{tpl_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    tpl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    tpl = await _owned(db, tpl_id, current_user)
    await db.delete(tpl)
    await db.commit()
