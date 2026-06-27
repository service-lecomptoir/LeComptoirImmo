"""Audit EXHAUSTIF des écritures via les évènements SQLAlchemy.

Tout INSERT / UPDATE / DELETE passant par l'ORM produit automatiquement une ligne
dans `audit_logs` (action `db.create` / `db.update` / `db.delete`, entity_type =
table, détails = valeurs ou diff des champs), avec l'acteur courant
(app.core.audit_context). Aucun endpoint à instrumenter : impossible d'oublier.

Garanties :
- FAIL-SAFE : une erreur d'audit ne casse JAMAIS l'opération métier (try/except).
- Pas de récursion : les lignes d'audit sont insérées en Core (pas d'ORM) et la
  table `audit_logs` est exclue.
- Secrets exclus : les colonnes sensibles (mot de passe, jeton, secret…) ne sont
  jamais journalisées (valeur remplacée par « *** »).

Les évènements de domaine riches (payment.*, revision.*, lease.*) restent gérés
explicitement par audit_service : ils coexistent avec les `db.*` génériques.
"""

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

logger = logging.getLogger(__name__)

# Tables jamais auditées par le mécanisme générique (bruit / récursion).
_EXCLUDED_TABLES = {"audit_logs"}

# Fragments de noms de colonnes dont la valeur ne doit jamais être journalisée.
_SENSITIVE = (
    "password",
    "hashed",
    "secret",
    "token",
    "pin",
    "api_key",
    "apikey",
    "private_key",
    "webhook",
)


def _is_sensitive(col_name: str) -> bool:
    c = col_name.lower()
    return any(frag in c for frag in _SENSITIVE)


def _jsonable(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return "<bytes>"
    if isinstance(value, dict | list | str | int | float | bool) or value is None:
        return value
    return str(value)


def _auditable(obj) -> bool:
    table = getattr(obj, "__tablename__", None)
    return bool(table) and table not in _EXCLUDED_TABLES


def _pk(obj) -> uuid.UUID | None:
    """Identifiant principal s'il s'agit d'un UUID simple, sinon None.
    Lit la valeur sur l'attribut (peuplée après flush) plutôt que `identity`
    (encore None pendant l'évènement de flush)."""
    try:
        pk_cols = inspect(obj).mapper.primary_key
        if len(pk_cols) == 1:
            val = getattr(obj, pk_cols[0].key, None)
            if isinstance(val, uuid.UUID):
                return val
    except Exception:  # noqa: BLE001
        pass
    return None


def _snapshot(obj) -> dict:
    """Valeurs des colonnes (hors secrets), JSON-isables."""
    out = {}
    try:
        mapper = inspect(obj).mapper
        for col in mapper.columns:
            key = col.key
            if _is_sensitive(key):
                out[key] = "***"
                continue
            out[key] = _jsonable(getattr(obj, key, None))
    except Exception:  # noqa: BLE001
        return {}
    return out


def _diff(obj) -> dict:
    """Champs modifiés : {champ: {old, new}} (hors secrets, hors no-op)."""
    changes = {}
    try:
        mapper = inspect(obj).mapper
        for col in mapper.columns:
            key = col.key
            hist = get_history(obj, key)
            if not hist.has_changes():
                continue
            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else None
            if old == new:
                continue
            if _is_sensitive(key):
                changes[key] = {"old": "***", "new": "***"}
            else:
                changes[key] = {"old": _jsonable(old), "new": _jsonable(new)}
    except Exception:  # noqa: BLE001
        return {}
    return changes


@event.listens_for(Session, "before_flush")
def _capture_before_flush(session, flush_context, instances):
    """Capture les changements TANT QUE l'historique des attributs est disponible."""
    try:
        pend = session.info.setdefault("_audit_pending", [])
        for obj in session.new:
            if _auditable(obj):
                pend.append(("db.create", obj, None))
        for obj in session.dirty:
            if not _auditable(obj):
                continue
            changes = _diff(obj)
            if changes:  # une modif sans changement réel de colonne n'est pas auditée
                pend.append(("db.update", obj, {"changes": changes}))
        for obj in session.deleted:
            if _auditable(obj):
                pend.append(("db.delete", obj, {"snapshot": _snapshot(obj)}))
    except Exception:  # noqa: BLE001
        logger.warning("[audit] capture before_flush échouée (non bloquant)", exc_info=True)


@event.listens_for(Session, "after_flush")
def _write_after_flush(session, flush_context):
    """Écrit les lignes d'audit (PK disponibles) en Core, sans casser le flush."""
    pend = session.info.pop("_audit_pending", None)
    if not pend:
        return
    try:
        from app.core.audit_context import get_actor
        from app.models.audit_log import AuditLog

        actor = get_actor()
        rows = []
        for action, obj, extra in pend:
            details = extra
            if action == "db.create":
                details = {"snapshot": _snapshot(obj)}
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": actor.get("user_id"),
                    "user_email": actor.get("user_email"),
                    "action": action,
                    "entity_type": getattr(obj, "__tablename__", None),
                    "entity_id": _pk(obj),
                    "details": details,
                    "ip_address": actor.get("ip"),
                }
            )
        if rows:
            session.execute(AuditLog.__table__.insert(), rows)
    except Exception:  # noqa: BLE001
        # Un échec d'audit ne doit JAMAIS casser l'opération métier.
        logger.warning("[audit] écriture after_flush échouée (non bloquant)", exc_info=True)


def install_audit_listeners() -> None:
    """No-op : l'import du module enregistre déjà les écouteurs (décorateurs).
    Sert de point d'appel explicite au démarrage pour garantir l'import."""
    logger.info("Audit exhaustif (db.*) activé via les évènements SQLAlchemy ✓")
