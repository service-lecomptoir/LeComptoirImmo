import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager, get_current_user
from app.api.v1._isolation import agency_owner_ids as _agency_owner_ids
from app.api.v1._isolation import assert_manager_scope
from app.core.features import require_any_feature, require_feature
from app.core.permissions import Role
from app.database import get_db
from app.models.document import EntityType
from app.models.owner import Owner
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.schemas.owner import OwnerCreate, OwnerListItem, OwnerResponse, OwnerUpdate
from app.schemas.owner_reversement import ReversementCreate, ReversementResponse
from app.services.document_service import DocumentService
from app.services.mandant_service import MandantService
from app.services.owner_service import OwnerService

router = APIRouter(prefix="/owners", tags=["Propriétaires"])


@router.get("", response_model=dict, summary="Liste des propriétaires")
async def list_owners(
    search: str | None = Query(None, description="Recherche par nom, société, email, téléphone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    available_only: bool = Query(
        False, description="Exclure les propriétaires déjà rattachés à un bien"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste paginée des fiches propriétaire (réservé aux rôles de gestion)."""
    role = Role(current_user.role)
    if role in (Role.LOCATAIRE, Role.PROPRIETAIRE):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    owners, _ = await OwnerService.list_all(db, search=search, skip=0, limit=2000)

    if role == Role.GESTIONNAIRE:
        # Gestionnaire mandataire : uniquement les propriétaires de SON agence
        allowed = await _agency_owner_ids(db, current_user)
        owners = [o for o in owners if o.id in allowed]
    elif role == Role.GESTIONNAIRE_PROPRIO:
        owners = [o for o in owners if o.created_by == current_user.id]

    if available_only:
        from app.models.property import Property

        linked_ids = {
            oid
            for oid in (
                await db.execute(select(Property.owner_id).where(Property.owner_id.isnot(None)))
            )
            .scalars()
            .all()
        }
        owners = [o for o in owners if o.id not in linked_ids]

    total = len(owners)
    page = owners[skip : skip + limit]
    return {
        "items": [OwnerListItem.model_validate(o) for o in page],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("", response_model=OwnerResponse, status_code=201, summary="Créer un propriétaire")
async def create_owner(
    data: OwnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    return await OwnerService.create(db, data, created_by=current_user.id)


@router.get("/me", response_model=Optional[OwnerResponse], summary="Ma fiche propriétaire")
async def get_my_owner(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fiche propriétaire liée au compte connecté (ou null). Sert au propriétaire/GP
    pour consulter et éditer ses coordonnées de règlement (RIB) depuis son profil."""
    owner = (
        (await db.execute(select(Owner).where(Owner.user_id == current_user.id))).scalars().first()
    )
    return owner


@router.patch("/me", response_model=OwnerResponse, summary="Modifier ma fiche propriétaire")
async def update_my_owner(
    data: OwnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le propriétaire/GP met à jour sa propre fiche (coordonnées + RIB)."""
    owner = (
        (await db.execute(select(Owner).where(Owner.user_id == current_user.id))).scalars().first()
    )
    if not owner:
        raise HTTPException(status_code=404, detail="Aucune fiche propriétaire liée à ce compte")
    # Un propriétaire ne change pas son propre rattachement de compte via son profil.
    data.user_id = None
    payload = data.model_dump(exclude_unset=True)
    payload.pop("user_id", None)
    return await OwnerService.update(db, owner.id, OwnerUpdate(**payload))


@router.get("/{owner_id}", response_model=OwnerResponse, summary="Fiche propriétaire")
async def get_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "cette fiche propriétaire")
    resp = OwnerResponse.model_validate(owner)
    # La visibilité « espace propriétaire » ne concerne qu'un compte de rôle propriétaire.
    if owner.user_id:
        linked = await db.get(User, owner.user_id)
        resp.user_is_proprietaire = bool(linked and str(linked.role) == "proprietaire")
    return resp


@router.put("/{owner_id}", response_model=OwnerResponse, summary="Modifier un propriétaire")
async def update_owner(
    owner_id: uuid.UUID,
    data: OwnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "cette fiche propriétaire")
    return await OwnerService.update(db, owner_id, data)


@router.delete("/{owner_id}", status_code=204, summary="Supprimer un propriétaire")
async def delete_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "cette fiche propriétaire")
    await OwnerService.delete(db, owner_id)


# ── Finances par propriétaire (réservé aux gestionnaires) ──────────────────────
@router.get("/{owner_id}/finances", summary="Finances d'un propriétaire (revenus, biens, fiscal)")
async def owner_finances(
    owner_id: uuid.UUID,
    year: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
    _feat: User = Depends(require_any_feature("finances", "performance_biens", "liasse_fiscale")),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    return await OwnerService.get_finances(db, owner_id, year)


@router.get("/{owner_id}/fiscal/pdf", summary="Liasse fiscale (PDF) d'un propriétaire")
async def owner_fiscal_pdf(
    owner_id: uuid.UUID,
    year: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
    _feat: User = Depends(require_feature("liasse_fiscale")),
):
    from fastapi.responses import Response

    from app.services.pdf_service import html_to_pdf, render_template
    from app.services.template_layout_service import get_layout
    from app.utils.filename import doc_filename

    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    data = await OwnerService.get_finances(db, owner_id, year)
    html = render_template(
        "liasse_fiscale.html.j2",
        {
            "data": data,
            "layout": get_layout(),
            "signature_uri": (getattr(current_user, "signature", None) or ""),
        },
    )
    pdf = html_to_pdf(html)
    filename = doc_filename("liasse_fiscale", tenant=data["owner_name"], year=year)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Compta mandant : compte rendu de gestion + reversements ────────────────────
@router.get("/{owner_id}/mandant", summary="Compte mandant (CRG) d'un propriétaire")
async def owner_mandant_account(
    owner_id: uuid.UUID,
    year: int = Query(..., ge=2000, le=2100),
    period: str = Query("annuel", pattern="^(mensuel|trimestriel|semestriel|annuel)$"),
    index: int = Query(1, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
    _feat: User = Depends(require_feature("compta_mandant")),
):
    """Encaissé, honoraires (HT/TVA/TTC), net dû, reversé et solde à reverser,
    pour la périodicité demandée (mensuel/trimestriel/semestriel/annuel)."""
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    return await MandantService.get_account(db, owner_id, year, period, index)


@router.get(
    "/{owner_id}/reversements",
    response_model=list[ReversementResponse],
    summary="Reversements d'un propriétaire",
)
async def list_owner_reversements(
    owner_id: uuid.UUID,
    year: int | None = Query(None, ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
    _feat: User = Depends(require_feature("compta_mandant")),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    return await MandantService.list_reversements(db, owner_id, year)


@router.post(
    "/{owner_id}/reversements",
    response_model=ReversementResponse,
    status_code=201,
    summary="Enregistrer un reversement au propriétaire",
)
async def create_owner_reversement(
    owner_id: uuid.UUID,
    data: ReversementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
    _feat: User = Depends(require_feature("compta_mandant")),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    return await MandantService.create_reversement(db, owner_id, data, created_by=current_user.id)


@router.delete(
    "/{owner_id}/reversements/{reversement_id}",
    status_code=204,
    summary="Supprimer un reversement",
)
async def delete_owner_reversement(
    owner_id: uuid.UUID,
    reversement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
    _feat: User = Depends(require_feature("compta_mandant")),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    await MandantService.delete_reversement(db, owner_id, reversement_id)


@router.get("/{owner_id}/crg/pdf", summary="Compte rendu de gestion (PDF)")
async def owner_crg_pdf(
    owner_id: uuid.UUID,
    year: int = Query(..., ge=2000, le=2100),
    period: str = Query("annuel", pattern="^(mensuel|trimestriel|semestriel|annuel)$"),
    index: int = Query(1, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
    _feat: User = Depends(require_feature("compta_mandant")),
):
    from fastapi.responses import Response

    from app.services.pdf_service import html_to_pdf, render_template
    from app.services.template_layout_service import get_layout
    from app.utils.filename import _slug as _slug_name
    from app.utils.filename import simple_doc_filename

    owner = await OwnerService.get_by_id(db, owner_id)
    await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    account = await MandantService.get_account(db, owner_id, year, period, index)
    html = render_template(
        "crg.html.j2",
        {
            "account": account,
            "layout": get_layout(),
            "period_label": account["period_label"],
            "manager_name": current_user.full_name or "",
            "manager_address": getattr(current_user, "full_address", None) or "",
            "signature_uri": (getattr(current_user, "signature", None) or ""),
            "tampon_uri": (getattr(current_user, "tampon", None) or ""),
        },
    )
    pdf = html_to_pdf(html)
    # Nom de fichier : CRG-<proprio>-<periode>-<aaaa>.pdf (ex. CRG-DUPONT-T1-2026).
    period_tag = {
        "mensuel": f"{account['month_start']:02d}",
        "trimestriel": f"T{index}",
        "semestriel": f"S{index}",
        "annuel": "ANNUEL",
    }.get(period, "ANNUEL")
    filename = simple_doc_filename("crg", _slug_name(account["owner_name"]), period_tag, year)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Documents du propriétaire ──────────────────────────────────────────────────
@router.get("/{owner_id}/documents", response_model=list[DocumentResponse])
async def list_owner_documents(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner = await OwnerService.get_by_id(db, owner_id)
    # Le propriétaire lui-même OU un gestionnaire dans son périmètre.
    if str(getattr(owner, "user_id", None)) != str(current_user.id):
        await assert_manager_scope(db, current_user, owner.created_by, "ce propriétaire")
    return await DocumentService.list_by_entity(db, EntityType.OWNER, owner_id)
