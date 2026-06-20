import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager, get_current_user
from app.api.v1._isolation import agency_property_ids, assert_manager_scope
from app.core.permissions import Role
from app.database import get_db
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyListItem, PropertyResponse, PropertyUpdate
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["Biens immobiliers"])


async def _enrich_properties(db, properties):
    """Un bien = un logement : unit_count=1, occupied_count selon is_occupied."""
    items = []
    for prop in properties:
        item_dict = PropertyListItem.model_validate(prop).model_dump()
        item_dict["unit_count"] = 1
        item_dict["occupied_count"] = 1 if prop.is_occupied else 0
        items.append(item_dict)
    return items


@router.get("", response_model=dict, summary="Liste des biens")
async def list_properties(
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = Role(current_user.role)

    # Propriétaire / Gestionnaire-Propriétaire : uniquement ses biens
    if role in (Role.PROPRIETAIRE, Role.GESTIONNAIRE_PROPRIO):
        props = (
            (
                await db.execute(
                    select(Property)
                    .where(Property.owner_user_id == current_user.id)
                    .order_by(func.lower(Property.name))
                )
            )
            .scalars()
            .all()
        )
        items = await _enrich_properties(db, props)
        return {"items": items, "total": len(items), "skip": 0, "limit": limit}

    # Locataire : accès interdit à la liste des biens
    if role == Role.LOCATAIRE:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    # Gestionnaire mandataire : uniquement les biens de SON agence
    if role == Role.GESTIONNAIRE:
        allowed = await agency_property_ids(db, current_user)
        all_props, _ = await PropertyService.list_all(db, search=search, skip=0, limit=2000)
        filtered = [p for p in all_props if p.id in allowed]
        items = await _enrich_properties(db, filtered)
        return {"items": items, "total": len(items), "skip": 0, "limit": limit}

    # Admin / autres
    properties, total = await PropertyService.list_all(db, search=search, skip=skip, limit=limit)
    items = await _enrich_properties(db, properties)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=PropertyResponse, status_code=201, summary="Créer un bien")
async def create_property(
    data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    # ── Vérification limite de biens via Alice ─────────────────────────────
    import logging

    from fastapi import HTTPException

    _log = logging.getLogger(__name__)

    role = Role(current_user.role)
    if role in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        try:
            import httpx

            from app.config import get_settings as _cfg_fn

            _cfg = _cfg_fn()
            async with httpx.AsyncClient(timeout=5.0) as _hc:
                _resp = await _hc.get(
                    f"{_cfg.ALICE_URL}/api/v1/internal/license/{current_user.id}",
                    headers={"X-Internal-Key": _cfg.ALICE_INTERNAL_KEY},
                )
            if _resp.status_code == 404:
                raise HTTPException(
                    status_code=403,
                    detail="Aucune licence Alice associée à votre compte. Contactez l'administrateur.",
                )
            if _resp.status_code != 200:
                raise HTTPException(
                    status_code=503, detail="Service de licences indisponible. Réessayez."
                )

            _lic = _resp.json()
            effective_limit: int | None = _lic.get("property_limit")

            if effective_limit is not None:
                current_count = (
                    await db.execute(
                        select(func.count(Property.id)).where(
                            Property.created_by == current_user.id
                        )
                    )
                ).scalar_one_or_none() or 0
                if current_count >= effective_limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Limite de biens atteinte ({current_count}/{effective_limit}). Passez à un plan supérieur.",
                    )
        except HTTPException:
            raise
        except Exception as exc:
            _log.warning(f"Alice license check error for {current_user.id}: {exc}")
            raise HTTPException(
                status_code=503, detail="Service de licences indisponible. Réessayez."
            )
    # ─────────────────────────────────────────────────────────────────────────
    prop = await PropertyService.create(db, data, created_by=current_user.id)
    from app.services import audit_service

    await audit_service.log(
        db,
        action=audit_service.PROPERTY_CREATE,
        user_id=current_user.id,
        user_email=current_user.email,
        entity_type="property",
        entity_id=prop.id,
        details={"name": prop.name},
    )
    return prop


@router.get("/{property_id}", response_model=PropertyResponse, summary="Détail d'un bien")
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    prop = await PropertyService.get_by_id(db, property_id)
    await assert_manager_scope(db, current_user, prop.created_by, "ce bien")
    resp = PropertyResponse.model_validate(prop)
    resp.unit_count = 1
    resp.occupied_count = 1 if prop.is_occupied else 0
    return resp


@router.put("/{property_id}", response_model=PropertyResponse, summary="Modifier un bien")
async def update_property(
    property_id: uuid.UUID,
    data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    prop = await PropertyService.get_by_id(db, property_id)
    await assert_manager_scope(db, current_user, prop.created_by, "ce bien")
    return await PropertyService.update(db, property_id, data)


@router.delete("/{property_id}", status_code=204, summary="Supprimer un bien")
async def delete_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    prop = await PropertyService.get_by_id(db, property_id)
    await assert_manager_scope(db, current_user, prop.created_by, "ce bien")
    await PropertyService.delete(db, property_id)


@router.get("/{property_id}/occupancy", summary="Taux d'occupation")
async def get_occupancy(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    prop = await PropertyService.get_by_id(db, property_id)
    await assert_manager_scope(db, current_user, prop.created_by, "ce bien")
    return await PropertyService.get_occupancy(db, property_id)
