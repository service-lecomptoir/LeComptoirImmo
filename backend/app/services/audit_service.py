"""Service d'audit — enregistre les actions critiques dans audit_logs."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Actions canoniques
LOGIN = "login"
LOGIN_FAILED = "login_failed"
PROPERTY_CREATE = "property.create"
PROPERTY_DELETE = "property.delete"
LEASE_CREATE = "lease.create"
LEASE_TERMINATE = "lease.terminate"
PAYMENT_RECORD = "payment.record"
PAYMENT_DELETE = "payment.delete"
PAYMENT_CREATE = "payment.create"
PAYMENT_GENERATE = "payment.generate"
PAYMENT_DECLARE = "payment.declare"
PAYMENT_CANCEL = "payment.cancel"
PAYMENT_REFUSE = "payment.refuse_declaration"
USER_CREATE = "user.create"
USER_BLOCK = "user.block"
USER_UNBLOCK = "user.unblock"
DOCUMENT_UPLOAD = "document.upload"
DOCUMENT_DELETE = "document.delete"
# RGPD : droit d'accès (export) et droit à l'effacement (anonymisation)
RGPD_EXPORT = "rgpd.export"
RGPD_ERASE = "rgpd.erase"
# Révisions de loyer / charges (réévaluations datées)
REVISION_SCHEDULE = "revision.schedule"  # création d'une réévaluation programmée
REVISION_REPLACE = "revision.replace"  # remplacement d'une réévaluation déjà programmée
REVISION_DELETE = "revision.delete"  # suppression (manuelle, ou remplacée)
REVISION_PURGE = "revision.purge"  # suppression automatique (correction d'un bail non débuté)


async def log(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Insère une ligne dans audit_logs. Silencieux en cas d'erreur pour ne pas bloquer."""
    try:
        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
    except Exception as exc:
        logger.warning("audit_service.log failed (non-bloquant): %s", exc)
