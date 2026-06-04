import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_gestionnaire
from app.core.features import require_feature
from app.config import get_settings
from app.models.user import User
from app.models.telegram_link import TelegramLink
from app.services import agent_team_service
from app.services.telegram_service import send_message

router = APIRouter(tags=["Agents IA"])

_LINK_HELP = ("Pour activer vos agents, générez un code dans l'application "
              "(Mes informations → Agents IA) puis envoyez « /start <code> » ici.")


def _now():
    return datetime.now(timezone.utc)


def _gen_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


async def _get_or_create_link(db: AsyncSession, user_id) -> TelegramLink:
    link = (await db.execute(
        select(TelegramLink).where(TelegramLink.user_id == user_id)
    )).scalar_one_or_none()
    if not link:
        link = TelegramLink(user_id=user_id)
        db.add(link)
    return link


# ── Webhook entrant (appelé par Telegram — pas d'auth applicative) ───────────
@router.post("/telegram/webhook", summary="Webhook Telegram (équipe d'agents)")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    # Sécurité : vérifier le secret d'en-tête configuré côté Telegram.
    if s.TELEGRAM_WEBHOOK_SECRET:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != s.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Secret invalide")
    data = await request.json()
    msg = (data or {}).get("message") or (data or {}).get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id")) if chat.get("id") is not None else None
    text = (msg.get("text") or "").strip()
    if not chat_id:
        return {"ok": True}

    # Liaison via « /start <code> »
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""
        if code:
            link = (await db.execute(
                select(TelegramLink).where(TelegramLink.link_code == code)
            )).scalar_one_or_none()
            if link:
                link.chat_id = chat_id
                link.verified_at = _now()
                link.link_code = None
                link.opt_in = True
                await db.commit()
                await send_message(chat_id, "✅ Compte lié avec succès !\n\n" + agent_team_service._help())
                return {"ok": True}
        existing = (await db.execute(
            select(TelegramLink).where(TelegramLink.chat_id == chat_id)
        )).scalar_one_or_none()
        if existing and existing.opt_in:
            await send_message(chat_id, agent_team_service._help())
        else:
            await send_message(chat_id, _LINK_HELP)
        return {"ok": True}

    # Message courant : nécessite un compte lié
    link = (await db.execute(
        select(TelegramLink).where(TelegramLink.chat_id == chat_id)
    )).scalar_one_or_none()
    if not link or not link.opt_in:
        await send_message(chat_id, _LINK_HELP)
        return {"ok": True}
    user = await db.get(User, link.user_id)
    if not user:
        await send_message(chat_id, _LINK_HELP)
        return {"ok": True}
    link.last_inbound_at = _now()
    await db.commit()
    try:
        reply = await _handle_message(db, link, user, text)
    except Exception:
        reply = "Désolé, une erreur est survenue. Réessayez plus tard."
    await send_message(chat_id, reply)
    return {"ok": True}


async def _handle_message(db, link, user, text: str) -> str:
    """Oriente le message : confirmation d'action, proposition d'action, ou Q&R."""
    from app.services import agent_action_service as actions

    # 1) Une action est en attente de confirmation ?
    if link.pending_action:
        if actions.is_confirmation(text):
            pending = link.pending_action
            link.pending_action = None
            link.pending_action_at = None
            await db.commit()
            return await actions.execute(db, user, pending)
        if actions.is_cancellation(text):
            link.pending_action = None
            link.pending_action_at = None
            await db.commit()
            return "Action annulée. 👍"
        # Ni oui ni non : on abandonne l'action en cours et on traite le nouveau message.
        link.pending_action = None
        link.pending_action_at = None
        await db.commit()

    # 2) Le message demande-t-il une action ? (propose + confirmation)
    proposal = await actions.interpret(db, user, text)
    if proposal is not None:
        if proposal.get("pending"):
            link.pending_action = proposal["pending"]
            link.pending_action_at = _now()
            await db.commit()
        return proposal["reply"]

    # 3) Sinon : question → réponse informative (Phase 2 / Phase 1)
    return await agent_team_service.answer(db, user, text)


# ── Liaison côté gestionnaire (gated par l'option « Agents IA ») ─────────────
@router.post("/agents/telegram/link-code", summary="Générer un code de liaison Telegram")
async def generate_link_code(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
    _feat: User = Depends(require_feature("agents_ia")),
):
    link = await _get_or_create_link(db, current_user.id)
    link.link_code = _gen_code()
    await db.commit()
    s = get_settings()
    username = s.TELEGRAM_BOT_USERNAME or None
    deep = f"https://t.me/{username}?start={link.link_code}" if username else None
    return {
        "code": link.link_code,
        "bot_username": username,
        "deep_link": deep,
        "linked": link.chat_id is not None,
        "enabled": s.telegram_enabled,
    }


@router.get("/agents/telegram/status", summary="Statut de la liaison Telegram")
async def telegram_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
    _feat: User = Depends(require_feature("agents_ia")),
):
    link = (await db.execute(
        select(TelegramLink).where(TelegramLink.user_id == current_user.id)
    )).scalar_one_or_none()
    s = get_settings()
    return {
        "linked": bool(link and link.chat_id and link.opt_in),
        "bot_username": s.TELEGRAM_BOT_USERNAME or None,
        "enabled": s.telegram_enabled,
    }


@router.post("/agents/telegram/unlink", summary="Délier Telegram")
async def telegram_unlink(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
    _feat: User = Depends(require_feature("agents_ia")),
):
    link = (await db.execute(
        select(TelegramLink).where(TelegramLink.user_id == current_user.id)
    )).scalar_one_or_none()
    if link:
        link.chat_id = None
        link.opt_in = False
        link.link_code = None
        await db.commit()
    return {"linked": False}
