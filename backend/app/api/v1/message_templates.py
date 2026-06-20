"""API Modèles de courrier multilingues (onglet Communication)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire
from app.database import get_db
from app.models.message_template import TEMPLATE_LANGS, MessageTemplate
from app.models.user import User

router = APIRouter(prefix="/message-templates", tags=["Modèles de courrier"])


class MTCreate(BaseModel):
    rule_type: str
    name: str
    content: dict[str, Any] = {}
    is_selected: bool = False


class MTUpdate(BaseModel):
    name: str | None = None
    content: dict[str, Any] | None = None
    is_active: bool | None = None


class MTResponse(BaseModel):
    id: uuid.UUID
    gestionnaire_id: uuid.UUID | None = None
    rule_type: str
    name: str
    content: dict[str, Any] = {}
    is_selected: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


def _clean_content(content: dict[str, Any]) -> dict[str, Any]:
    """Ne garde que les langues connues et les clés subject/body/sms (chaînes)."""
    out: dict[str, Any] = {}
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
    rows = (
        (
            await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.gestionnaire_id == user_id,
                    MessageTemplate.rule_type == rule_type,
                    MessageTemplate.is_selected.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    for r in rows:
        if r.id != keep_id:
            r.is_selected = False


@router.get("", response_model=list[MTResponse])
async def list_templates(
    rule_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    q = select(MessageTemplate).where(MessageTemplate.gestionnaire_id == current_user.id)
    if rule_type:
        q = q.where(MessageTemplate.rule_type == rule_type)
    q = q.order_by(MessageTemplate.rule_type, MessageTemplate.name)
    rows = list((await db.execute(q)).scalars().all())
    # Masquer les modèles dont la fonctionnalité n'est pas incluse au plan.
    from app.core.features import get_plan_features, rule_type_allowed

    feats = await get_plan_features(db, current_user.id)
    return [t for t in rows if rule_type_allowed(t.rule_type, feats)]


@router.post("", response_model=MTResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: MTCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    tpl = MessageTemplate(
        gestionnaire_id=current_user.id,
        rule_type=data.rule_type,
        name=data.name,
        content=_clean_content(data.content),
        is_selected=data.is_selected,
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


class AIAssistIn(BaseModel):
    rule_type: str
    langs: list[str] = ["fr"]
    base_text: str | None = None  # consigne / brouillon fourni par le gestionnaire
    tone: str | None = None  # ex. « courtois », « ferme »


@router.post("/ai-assist")
async def ai_assist(
    data: AIAssistIn,
    current_user: User = Depends(get_current_gestionnaire),
):
    """Assistance IA : génère/traduit le contenu d'un modèle pour les langues
    demandées. Repli sur les modèles par défaut si le LLM n'est pas configuré."""
    import json

    from app.services import llm_service
    from app.services.message_template_defaults import TYPE_PLACEHOLDERS, default_content

    langs = [l for l in data.langs if l in TEMPLATE_LANGS] or ["fr"]
    type_label = data.rule_type
    placeholders = TYPE_PLACEHOLDERS.get(data.rule_type, "{{tenant_name}} {{period}}")
    lang_names = {
        "fr": "français",
        "en": "anglais",
        "pt-BR": "portugais du Brésil",
        "ht": "créole haïtien",
        "srn": "sranan tongo (taki-taki)",
    }
    fallback = {
        l: default_content(data.rule_type).get(l) or default_content(data.rule_type).get("fr") or {}
        for l in langs
    }

    if llm_service.enabled():
        wanted = ", ".join(f'"{l}"' for l in langs)
        sys = (
            "Tu rédiges des courriers de gestion locative (e-mail + SMS) pour un bailleur, "
            "courtois et professionnels, courts. Tu DOIS conserver telles quelles les variables "
            f"entre doubles accolades : {placeholders}. Réponds UNIQUEMENT en JSON valide."
        )
        user = (
            f"Type de courrier : {type_label}.\n"
            f"Langues demandées (codes) : {wanted}.\n"
            f"{'Consigne/brouillon : ' + data.base_text if data.base_text else ''}\n"
            f"{'Ton souhaité : ' + data.tone if data.tone else ''}\n"
            'Pour CHAQUE langue, fournis un objet {"subject":..., "body":..., "sms":...} '
            "(sms = version courte, ~160 caractères). "
            'Renvoie un JSON: {"<code_langue>": {"subject":"","body":"","sms":""}, ...} '
            f"avec exactement ces langues : {', '.join(lang_names.get(l, l) for l in langs)}."
        )
        raw = await llm_service.chat(
            [{"role": "system", "content": sys}, {"role": "user", "content": user}],
            temperature=0.4,
            max_tokens=1400,
        )
        if raw:
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.strip("`")
                txt = txt[txt.find("{") : txt.rfind("}") + 1] if "{" in txt else txt
            try:
                parsed = json.loads(txt[txt.find("{") : txt.rfind("}") + 1])
                out = {}
                for l in langs:
                    b = parsed.get(l) or {}
                    if isinstance(b, dict):
                        out[l] = {k: str(b.get(k) or "") for k in ("subject", "body", "sms")}
                if out:
                    return {"content": out, "source": "ia"}
            except Exception:  # noqa: BLE001 : JSON invalide → repli
                pass
    return {"content": fallback, "source": "defaut"}


@router.delete("/{tpl_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    tpl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    tpl = await _owned(db, tpl_id, current_user)
    await db.delete(tpl)
    await db.commit()
