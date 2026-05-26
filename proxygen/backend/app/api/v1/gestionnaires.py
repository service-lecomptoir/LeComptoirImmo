import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from sqlalchemy import or_

from app.database import get_db
from app.models.admin import ProxygenAdmin
from app.models.license import ProxygenLicense
from app.models.plan import ProxygenPlan
from app.models.leci import LeciUser, LeciProperty
from app.schemas.gestionnaire import GestionnaireCreate, GestionnaireUpdate, GestionnaireOut, GestionnairePropertyOut

logger = logging.getLogger(__name__)


async def _notify_leci_webhook(
    user_id: uuid.UUID,
    event: str,
    is_blocked: bool,
    plan_name: Optional[str] = None,
    property_limit: Optional[int] = None,
) -> None:
    """Notifie LeCI d'un changement de statut ou de plan (fire & forget)."""
    try:
        import httpx
        from app.config import get_settings
        cfg = get_settings()
        payload = {
            "user_id": str(user_id),
            "event": event,
            "is_blocked": is_blocked,
            "plan_name": plan_name,
            "property_limit": property_limit,
        }
        async with httpx.AsyncClient(timeout=5.0) as hc:
            resp = await hc.post(
                f"{cfg.LECI_URL}/api/v1/internal/webhook/proxygen",
                json=payload,
                headers={"X-Internal-Key": cfg.INTERNAL_API_KEY},
            )
        if resp.status_code not in (200, 204):
            logger.warning("LeCI webhook réponse inattendue: %s", resp.status_code)
    except Exception as exc:
        logger.warning("Impossible de notifier LeCI via webhook: %s", exc)

def _manager_roles():
    """Filtre WHERE couvrant les deux rôles gestionnaire de LeCI."""
    return or_(
        LeciUser.role_eq("gestionnaire"),
        LeciUser.role_eq("gestionnaire_proprio"),
    )
from app.schemas.license import LicenseOut
from app.schemas.plan import PlanOut
from app.core.security import hash_password
from app.core.deps import get_current_proxygen_admin
from app.services.block_service import block_gestionnaire, unblock_gestionnaire

router = APIRouter(prefix="/gestionnaires", tags=["Gestionnaires"])

_executor = ThreadPoolExecutor(max_workers=2)


async def _build_gestionnaire_out(
    db: AsyncSession,
    user: LeciUser,
    license: Optional[ProxygenLicense],
    plan: Optional[ProxygenPlan],
) -> GestionnaireOut:
    """Construit le schéma de sortie pour un gestionnaire."""
    # Nb de biens créés
    count_result = await db.execute(
        select(func.count(LeciProperty.id)).where(LeciProperty.created_by == user.id)
    )
    property_count = count_result.scalar_one_or_none() or 0

    # Limite effective
    effective_limit: Optional[int] = None
    if license and license.property_limit_override is not None:
        effective_limit = license.property_limit_override
    elif plan and plan.property_limit is not None:
        effective_limit = plan.property_limit

    license_out = LicenseOut.model_validate(license) if license else None
    plan_out = PlanOut.model_validate(plan) if plan else None

    return GestionnaireOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        license=license_out,
        plan=plan_out,
        effective_property_limit=effective_limit,
        property_count=property_count,
    )


@router.get("", response_model=List[GestionnaireOut])
async def list_gestionnaires(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Liste tous les gestionnaires avec leur licence et plan."""
    users_result = await db.execute(
        select(LeciUser)
        .where(_manager_roles())
        .order_by(LeciUser.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = users_result.scalars().all()

    output = []
    for user in users:
        lic_result = await db.execute(
            select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == user.id)
        )
        license = lic_result.scalar_one_or_none()

        plan = None
        if license and license.plan_id:
            plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == license.plan_id))
            plan = plan_result.scalar_one_or_none()

        output.append(await _build_gestionnaire_out(db, user, license, plan))

    return output


@router.post("", response_model=GestionnaireOut, status_code=status.HTTP_201_CREATED)
async def create_gestionnaire(
    data: GestionnaireCreate,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Crée un compte gestionnaire dans LeCI + sa licence ProxyGen."""
    # Vérifie unicité email
    existing = await db.execute(select(LeciUser).where(LeciUser.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"L'email '{data.email}' est déjà utilisé")

    # Hash du mot de passe dans un thread (bcrypt est synchrone)
    loop = asyncio.get_event_loop()
    hashed = await loop.run_in_executor(_executor, hash_password, data.password)

    # Créer le user dans LeCI
    new_user = LeciUser(
        id=uuid.uuid4(),
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed,
        role=data.role,
        is_active=True,
        phone=data.phone,
        address=data.address,
    )
    db.add(new_user)
    await db.flush()

    # Créer la licence ProxyGen
    license = ProxygenLicense(
        id=uuid.uuid4(),
        gestionnaire_user_id=new_user.id,
        plan_id=data.plan_id,
        property_limit_override=data.property_limit_override,
        monthly_price_override=data.monthly_price_override,
        notes=data.notes,
        phone=data.phone,
        address=data.address,
        is_blocked=False,
        blocked_user_ids=[],
    )
    db.add(license)
    await db.flush()

    # Récupérer le plan si assigné
    plan = None
    if data.plan_id:
        plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == data.plan_id))
        plan = plan_result.scalar_one_or_none()

    return await _build_gestionnaire_out(db, new_user, license, plan)


@router.get("/{gestionnaire_id}", response_model=GestionnaireOut)
async def get_gestionnaire(
    gestionnaire_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Détail d'un gestionnaire."""
    user_result = await db.execute(
        select(LeciUser).where(LeciUser.id == gestionnaire_id, _manager_roles())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable")

    lic_result = await db.execute(
        select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == gestionnaire_id)
    )
    license = lic_result.scalar_one_or_none()

    plan = None
    if license and license.plan_id:
        plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == license.plan_id))
        plan = plan_result.scalar_one_or_none()

    return await _build_gestionnaire_out(db, user, license, plan)


@router.patch("/{gestionnaire_id}", response_model=GestionnaireOut)
async def update_gestionnaire(
    gestionnaire_id: uuid.UUID,
    data: GestionnaireUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Modifie les informations d'un gestionnaire et/ou sa licence."""
    user_result = await db.execute(
        select(LeciUser).where(LeciUser.id == gestionnaire_id, _manager_roles())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable")

    # Mise à jour user (+ coordonnées profil LeCI)
    if data.email is not None:
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.address is not None:
        user.address = data.address

    # Mise à jour licence
    lic_result = await db.execute(
        select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == gestionnaire_id)
    )
    license = lic_result.scalar_one_or_none()
    if not license:
        # Créer licence si inexistante
        license = ProxygenLicense(
            id=uuid.uuid4(),
            gestionnaire_user_id=gestionnaire_id,
            blocked_user_ids=[],
        )
        db.add(license)

    plan_fields_changed = any(
        getattr(data, f, None) is not None
        for f in ("plan_id", "property_limit_override", "monthly_price_override")
    )
    for field in ("plan_id", "property_limit_override", "monthly_price_override", "notes", "phone", "address"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(license, field, value)

    await db.flush()

    plan = None
    if license.plan_id:
        plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == license.plan_id))
        plan = plan_result.scalar_one_or_none()

    if plan_fields_changed:
        plan_name = plan.name if plan else None
        eff_limit = license.property_limit_override if license.property_limit_override is not None else (plan.property_limit if plan else None)
        background_tasks.add_task(
            _notify_leci_webhook, gestionnaire_id, "plan_changed", license.is_blocked, plan_name, eff_limit
        )

    return await _build_gestionnaire_out(db, user, license, plan)


@router.post("/{gestionnaire_id}/block", response_model=GestionnaireOut)
async def block_gestionnaire_endpoint(
    gestionnaire_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Bloque un gestionnaire et tous ses propriétaires/locataires en cascade."""
    user_result = await db.execute(
        select(LeciUser).where(LeciUser.id == gestionnaire_id, _manager_roles())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable")

    lic_result = await db.execute(
        select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == gestionnaire_id)
    )
    license = lic_result.scalar_one_or_none()
    if not license:
        # Créer une licence vide si nécessaire
        license = ProxygenLicense(
            id=uuid.uuid4(),
            gestionnaire_user_id=gestionnaire_id,
            blocked_user_ids=[],
        )
        db.add(license)
        await db.flush()

    if license.is_blocked:
        raise HTTPException(status_code=400, detail="Ce gestionnaire est déjà bloqué")

    await block_gestionnaire(db, license, gestionnaire_id)
    await db.flush()

    plan = None
    if license.plan_id:
        plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == license.plan_id))
        plan = plan_result.scalar_one_or_none()

    plan_name = plan.name if plan else None
    background_tasks.add_task(
        _notify_leci_webhook, gestionnaire_id, "blocked", True, plan_name, None
    )

    # Re-fetch user après mise à jour is_active
    user_result2 = await db.execute(select(LeciUser).where(LeciUser.id == gestionnaire_id))
    user = user_result2.scalar_one_or_none()

    return await _build_gestionnaire_out(db, user, license, plan)


@router.post("/{gestionnaire_id}/unblock", response_model=GestionnaireOut)
async def unblock_gestionnaire_endpoint(
    gestionnaire_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Débloque un gestionnaire et ses propriétaires/locataires."""
    user_result = await db.execute(
        select(LeciUser).where(LeciUser.id == gestionnaire_id, _manager_roles())
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable")

    lic_result = await db.execute(
        select(ProxygenLicense).where(ProxygenLicense.gestionnaire_user_id == gestionnaire_id)
    )
    license = lic_result.scalar_one_or_none()
    if not license or not license.is_blocked:
        raise HTTPException(status_code=400, detail="Ce gestionnaire n'est pas bloqué")

    await unblock_gestionnaire(db, license, gestionnaire_id)
    await db.flush()

    plan = None
    if license.plan_id:
        plan_result = await db.execute(select(ProxygenPlan).where(ProxygenPlan.id == license.plan_id))
        plan = plan_result.scalar_one_or_none()

    plan_name = plan.name if plan else None
    background_tasks.add_task(
        _notify_leci_webhook, gestionnaire_id, "unblocked", False, plan_name, None
    )

    user_result2 = await db.execute(select(LeciUser).where(LeciUser.id == gestionnaire_id))
    user = user_result2.scalar_one_or_none()

    return await _build_gestionnaire_out(db, user, license, plan)


@router.get("/{gestionnaire_id}/properties", response_model=List[GestionnairePropertyOut])
async def get_gestionnaire_properties(
    gestionnaire_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: ProxygenAdmin = Depends(get_current_proxygen_admin),
):
    """Liste des biens créés par ce gestionnaire."""
    user_result = await db.execute(
        select(LeciUser).where(LeciUser.id == gestionnaire_id, _manager_roles())
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable")

    result = await db.execute(
        select(LeciProperty).where(LeciProperty.created_by == gestionnaire_id)
        .order_by(LeciProperty.name)
    )
    properties = result.scalars().all()
    return [GestionnairePropertyOut.model_validate(p) for p in properties]
