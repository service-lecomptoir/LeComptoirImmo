"""Service d'audit — enregistre les actions critiques dans audit_logs."""
import logging
import uuid
from typing import Optional

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
USER_CREATE = "user.create"
USER_BLOCK = "user.block"
USER_UNBLOCK = "user.unblock"
DOCUMENT_UPLOAD = "document.upload"
DOCUMENT_DELETE = "document.delete"


async def log(
    db: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    user_email: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
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
