"""Acteur courant pour l'audit (ContextVar, isolé par requête/tâche).

Posé par le middleware (IP) puis complété par la dépendance d'auth (utilisateur).
Lu par les écouteurs SQLAlchemy (app.core.audit_listeners) pour estampiller chaque
écriture. En dehors d'une requête (planificateur, scripts), l'acteur est vide →
l'action est journalisée comme « système ».
"""

import contextvars
import uuid

_actor: contextvars.ContextVar[dict | None] = contextvars.ContextVar("audit_actor", default=None)


def set_actor(
    *, user_id: uuid.UUID | None = None, user_email: str | None = None, ip: str | None = None
) -> None:
    _actor.set({"user_id": user_id, "user_email": user_email, "ip": ip})


def update_actor(
    *, user_id: uuid.UUID | None = None, user_email: str | None = None, ip: str | None = None
) -> None:
    """Complète l'acteur existant (sans écraser les champs déjà posés)."""
    cur = dict(_actor.get() or {})
    if user_id is not None:
        cur["user_id"] = user_id
    if user_email is not None:
        cur["user_email"] = user_email
    if ip is not None:
        cur["ip"] = ip
    _actor.set(cur)


def get_actor() -> dict:
    return _actor.get() or {}


def reset_actor() -> None:
    _actor.set(None)
