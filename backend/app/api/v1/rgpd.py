"""API RGPD — droit d'accès (export) et droit à l'effacement (anonymisation).

Réservé aux gestionnaires/admin. Un gestionnaire n'agit que sur SES locataires
(created_by) ; l'admin sur tous. Chaque opération est tracée au journal d'audit.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_active_admin
from app.core.permissions import Role
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.user import User
from app.models.tenant import Tenant
from app.services import rgpd_service, audit_service

router = APIRouter(prefix="/rgpd", tags=["RGPD"])


async def _get_owned_tenant(db: AsyncSession, user: User, tenant_id: uuid.UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundException("Locataire introuvable")
    is_admin = str(user.role) == Role.ADMIN.value
    if not is_admin and tenant.created_by != user.id:
        raise ForbiddenException("Ce locataire ne dépend pas de votre compte")
    return tenant


@router.get("/tenants/{tenant_id}/export", summary="Exporter les données d'un locataire (RGPD)")
async def export_tenant_data(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_admin),
):
    """Droit d'accès (art. 15) : renvoie l'ensemble des données du locataire."""
    tenant = await _get_owned_tenant(db, user, tenant_id)
    data = await rgpd_service.export_tenant(db, tenant)
    await audit_service.log(
        db, action=audit_service.RGPD_EXPORT, user_id=user.id, user_email=user.email,
        entity_type="tenant", entity_id=tenant.id,
        ip_address=getattr(getattr(request, "client", None), "host", None),
    )
    await db.commit()
    return data


@router.post("/tenants/{tenant_id}/erase", summary="Effacer (anonymiser) un locataire (RGPD)")
async def erase_tenant_data(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_admin),
):
    """Droit à l'effacement (art. 17) : pseudonymise l'identité et supprime les
    pièces justificatives. L'historique comptable (légal) est conservé."""
    tenant = await _get_owned_tenant(db, user, tenant_id)
    result = await rgpd_service.anonymize_tenant(db, tenant)
    if not result.get("already"):
        await audit_service.log(
            db, action=audit_service.RGPD_ERASE, user_id=user.id, user_email=user.email,
            entity_type="tenant", entity_id=tenant.id, details=result,
            ip_address=getattr(getattr(request, "client", None), "host", None),
        )
    await db.commit()
    return {"status": "anonymise", **result}
