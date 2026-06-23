import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestionnaire, get_current_manager
from app.api.v1._isolation import agency_member_ids, assert_manager_scope
from app.core.permissions import Role
from app.database import get_db
from app.models.copropriete import CoproLot, CoproLotTantieme
from app.models.user import User
from app.schemas.copropriete import (
    CoproprieteCreate,
    CoproprieteDetail,
    CoproprieteListItem,
    CoproprieteUpdate,
    LotCreate,
    LotResponse,
    LotUpdate,
    RepartitionKeyCreate,
    RepartitionKeyResponse,
    RepartitionKeyUpdate,
)
from app.schemas.copropriete_ag import (
    AssemblyCreate,
    AssemblyDetail,
    AssemblyListItem,
    AssemblyUpdate,
    ResolutionCreate,
    ResolutionUpdate,
    VoteIn,
    VoterRow,
)
from app.schemas.copropriete_compta import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CoproAccountRow,
    CoproPaymentIn,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    FundCallGenerate,
    FundCallResponse,
    RegularizationResult,
)
from app.schemas.copropriete_extras import (
    MaintenanceCreate,
    MaintenanceResponse,
    MaintenanceUpdate,
    WorksFundEntryCreate,
    WorksFundEntryResponse,
    WorksFundSummary,
)
from app.services.copro_ag_service import CoproAGService
from app.services.copro_compta_service import CoproComptaService
from app.services.copro_extras_service import CoproExtrasService
from app.services.copropriete_service import CoproprieteService

router = APIRouter(prefix="/coproprietes", tags=["Syndic (copropriété)"])


async def _scope_member_ids(db: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """Périmètre de visibilité : None = tout (admin) ; sinon set d'ids autorisés."""
    role = Role(user.role)
    if role == Role.ADMIN:
        return None
    if role == Role.GESTIONNAIRE_PROPRIO:
        return {user.id}
    # Gestionnaire mandataire / comptable : périmètre agence.
    return await agency_member_ids(db, user)


async def _serialize_lot(db: AsyncSession, lot: CoproLot) -> LotResponse:
    rows = (
        (await db.execute(select(CoproLotTantieme).where(CoproLotTantieme.lot_id == lot.id)))
        .scalars()
        .all()
    )
    return LotResponse(
        id=lot.id,
        numero=lot.numero,
        lot_type=lot.lot_type,
        floor=lot.floor,
        description=lot.description,
        owner_id=lot.owner_id,
        owner_name=await CoproprieteService.owner_name(db, lot.owner_id),
        property_id=lot.property_id,
        tantiemes={str(r.key_id): float(r.tantiemes or 0) for r in rows},
    )


# ── Copropriétés ───────────────────────────────────────────────────────────────
@router.get("", response_model=list[CoproprieteListItem], summary="Liste des copropriétés")
async def list_coproprietes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    member_ids = await _scope_member_ids(db, current_user)
    return await CoproprieteService.list_for_member_ids(db, member_ids)


@router.post("", response_model=CoproprieteDetail, status_code=201, summary="Créer une copropriété")
async def create_copropriete(
    data: CoproprieteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.create(db, data, created_by=current_user.id)
    return await CoproprieteService.get_detail(db, copro.id)


@router.get("/{copro_id}", response_model=CoproprieteDetail, summary="Détail d'une copropriété")
async def get_copropriete(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    return await CoproprieteService.get_detail(db, copro_id)


@router.put("/{copro_id}", response_model=CoproprieteDetail, summary="Modifier une copropriété")
async def update_copropriete(
    copro_id: uuid.UUID,
    data: CoproprieteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    await CoproprieteService.update(db, copro_id, data)
    return await CoproprieteService.get_detail(db, copro_id)


@router.delete("/{copro_id}", status_code=204, summary="Supprimer une copropriété")
async def delete_copropriete(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, current_user, copro.created_by, "cette copropriété")
    await CoproprieteService.delete(db, copro_id)


# ── Clés de répartition ────────────────────────────────────────────────────────
async def _assert_copro(db: AsyncSession, user: User, copro_id: uuid.UUID):
    copro = await CoproprieteService.get_by_id(db, copro_id)
    await assert_manager_scope(db, user, copro.created_by, "cette copropriété")
    return copro


@router.post(
    "/{copro_id}/keys",
    response_model=RepartitionKeyResponse,
    status_code=201,
    summary="Ajouter une clé de répartition",
)
async def add_key(
    copro_id: uuid.UUID,
    data: RepartitionKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    key = await CoproprieteService.add_key(db, copro_id, data)
    return RepartitionKeyResponse(
        id=key.id,
        name=key.name,
        total_tantiemes=key.total_tantiemes,
        is_general=key.is_general,
        position=key.position,
        assigned_tantiemes=0,
        balanced=(key.total_tantiemes == 0),
    )


@router.put(
    "/{copro_id}/keys/{key_id}",
    response_model=RepartitionKeyResponse,
    summary="Modifier une clé de répartition",
)
async def update_key(
    copro_id: uuid.UUID,
    key_id: uuid.UUID,
    data: RepartitionKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    key = await CoproprieteService.update_key(db, copro_id, key_id, data)
    return RepartitionKeyResponse(
        id=key.id,
        name=key.name,
        total_tantiemes=key.total_tantiemes,
        is_general=key.is_general,
        position=key.position,
    )


@router.delete("/{copro_id}/keys/{key_id}", status_code=204, summary="Supprimer une clé")
async def delete_key(
    copro_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproprieteService.delete_key(db, copro_id, key_id)


# ── Lots ───────────────────────────────────────────────────────────────────────
@router.post(
    "/{copro_id}/lots",
    response_model=LotResponse,
    status_code=201,
    summary="Ajouter un lot",
)
async def create_lot(
    copro_id: uuid.UUID,
    data: LotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    lot = await CoproprieteService.create_lot(db, copro_id, data)
    return await _serialize_lot(db, lot)


@router.put("/{copro_id}/lots/{lot_id}", response_model=LotResponse, summary="Modifier un lot")
async def update_lot(
    copro_id: uuid.UUID,
    lot_id: uuid.UUID,
    data: LotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    lot = await CoproprieteService.update_lot(db, copro_id, lot_id, data)
    return await _serialize_lot(db, lot)


@router.delete("/{copro_id}/lots/{lot_id}", status_code=204, summary="Supprimer un lot")
async def delete_lot(
    copro_id: uuid.UUID,
    lot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproprieteService.delete_lot(db, copro_id, lot_id)


# ── Comptabilité copro : budget ──────────────────────────────────────────────
@router.get("/{copro_id}/budget", summary="Budget d'une année (null si absent)")
async def get_budget(
    copro_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.get_budget(db, copro_id, year)


@router.post(
    "/{copro_id}/budgets", response_model=BudgetResponse, status_code=201, summary="Créer un budget"
)
async def create_budget(
    copro_id: uuid.UUID,
    data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.create_budget(db, copro_id, data, created_by=current_user.id)


@router.put(
    "/{copro_id}/budgets/{budget_id}", response_model=BudgetResponse, summary="Modifier un budget"
)
async def update_budget(
    copro_id: uuid.UUID,
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.update_budget(db, copro_id, budget_id, data)


@router.delete("/{copro_id}/budgets/{budget_id}", status_code=204, summary="Supprimer un budget")
async def delete_budget(
    copro_id: uuid.UUID,
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproComptaService.delete_budget(db, copro_id, budget_id)


# ── Comptabilité copro : appels de fonds ─────────────────────────────────────
@router.get(
    "/{copro_id}/budgets/{budget_id}/calls",
    response_model=list[FundCallResponse],
    summary="Appels de fonds d'un budget",
)
async def list_calls(
    copro_id: uuid.UUID,
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.list_calls(db, copro_id, budget_id)


@router.post(
    "/{copro_id}/budgets/{budget_id}/calls",
    response_model=FundCallResponse,
    status_code=201,
    summary="Générer un appel de fonds",
)
async def generate_call(
    copro_id: uuid.UUID,
    budget_id: uuid.UUID,
    data: FundCallGenerate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.generate_call(
        db, copro_id, budget_id, data.period_index, data.due_date, created_by=current_user.id
    )


@router.delete(
    "/{copro_id}/calls/{call_id}", status_code=204, summary="Supprimer un appel de fonds"
)
async def delete_call(
    copro_id: uuid.UUID,
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproComptaService.delete_call(db, copro_id, call_id)


# ── Comptabilité copro : encaissements + comptes ─────────────────────────────
@router.post("/{copro_id}/call-items/{item_id}/payments", summary="Encaisser une quote-part")
async def record_copro_payment(
    copro_id: uuid.UUID,
    item_id: uuid.UUID,
    data: CoproPaymentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.record_payment(
        db, copro_id, item_id, data, created_by=current_user.id
    )


@router.get(
    "/{copro_id}/accounts",
    response_model=list[CoproAccountRow],
    summary="Comptes copropriétaires (appelé / payé / solde)",
)
async def copro_accounts(
    copro_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.accounts(db, copro_id, year)


@router.get(
    "/{copro_id}/call-items/{item_id}/appel/pdf", summary="Appel de fonds (PDF) d'un copropriétaire"
)
async def copro_appel_pdf(
    copro_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    from fastapi.responses import Response

    from app.services.pdf_service import html_to_pdf, render_template
    from app.services.template_layout_service import get_layout
    from app.utils.filename import _slug as _slug_name
    from app.utils.filename import simple_doc_filename

    await _assert_copro(db, current_user, copro_id)
    ctx = await CoproComptaService.appel_pdf_context(db, copro_id, item_id)
    html = render_template(
        "copro_appel.html.j2",
        {
            "ctx": ctx,
            "layout": get_layout(),
            "manager_name": current_user.full_name or "",
            "manager_address": getattr(current_user, "full_address", None) or "",
            "signature_uri": (getattr(current_user, "signature", None) or ""),
            "tampon_uri": (getattr(current_user, "tampon", None) or ""),
        },
    )
    pdf = html_to_pdf(html)
    filename = simple_doc_filename(
        "appel-fonds", _slug_name(ctx["owner_name"]), _slug_name(ctx["period_label"])
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Régularisation : dépenses réelles + décompte ─────────────────────────────
@router.get(
    "/{copro_id}/expenses",
    response_model=list[ExpenseResponse],
    summary="Dépenses réelles d'une année",
)
async def list_expenses(
    copro_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.list_expenses(db, copro_id, year)


@router.post(
    "/{copro_id}/expenses",
    response_model=ExpenseResponse,
    status_code=201,
    summary="Ajouter une dépense",
)
async def create_expense(
    copro_id: uuid.UUID,
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.create_expense(db, copro_id, data, created_by=current_user.id)


@router.put(
    "/{copro_id}/expenses/{expense_id}",
    response_model=ExpenseResponse,
    summary="Modifier une dépense",
)
async def update_expense(
    copro_id: uuid.UUID,
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.update_expense(db, copro_id, expense_id, data)


@router.delete(
    "/{copro_id}/expenses/{expense_id}", status_code=204, summary="Supprimer une dépense"
)
async def delete_expense(
    copro_id: uuid.UUID,
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproComptaService.delete_expense(db, copro_id, expense_id)


@router.get(
    "/{copro_id}/regularization",
    response_model=RegularizationResult,
    summary="Régularisation annuelle (réel vs appelé) par copropriétaire",
)
async def regularization(
    copro_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproComptaService.regularization(db, copro_id, year)


@router.get("/{copro_id}/regularization/{owner_id}/pdf", summary="Décompte de régularisation (PDF)")
async def regularization_pdf(
    copro_id: uuid.UUID,
    owner_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    from fastapi.responses import Response

    from app.services.pdf_service import html_to_pdf, render_template
    from app.services.template_layout_service import get_layout
    from app.utils.filename import _slug as _slug_name
    from app.utils.filename import simple_doc_filename

    await _assert_copro(db, current_user, copro_id)
    ctx = await CoproComptaService.regul_pdf_context(db, copro_id, owner_id, year)
    html = render_template(
        "copro_regul.html.j2",
        {
            "ctx": ctx,
            "layout": get_layout(),
            "manager_name": current_user.full_name or "",
            "manager_address": getattr(current_user, "full_address", None) or "",
            "signature_uri": (getattr(current_user, "signature", None) or ""),
            "tampon_uri": (getattr(current_user, "tampon", None) or ""),
        },
    )
    pdf = html_to_pdf(html)
    filename = simple_doc_filename("regularisation", _slug_name(ctx["owner_name"]), year)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Assemblées générales ─────────────────────────────────────────────────────
@router.get(
    "/{copro_id}/voters",
    response_model=list[VoterRow],
    summary="Copropriétaires votants (tantièmes)",
)
async def list_voters(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.voters(db, copro_id)


@router.get(
    "/{copro_id}/assemblies", response_model=list[AssemblyListItem], summary="Liste des assemblées"
)
async def list_assemblies(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.list_assemblies(db, copro_id)


@router.post(
    "/{copro_id}/assemblies",
    response_model=AssemblyDetail,
    status_code=201,
    summary="Créer une assemblée",
)
async def create_assembly(
    copro_id: uuid.UUID,
    data: AssemblyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.create_assembly(db, copro_id, data, created_by=current_user.id)


@router.get(
    "/{copro_id}/assemblies/{assembly_id}",
    response_model=AssemblyDetail,
    summary="Détail d'une assemblée",
)
async def get_assembly(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.get_detail(db, copro_id, assembly_id)


@router.put(
    "/{copro_id}/assemblies/{assembly_id}",
    response_model=AssemblyDetail,
    summary="Modifier une assemblée",
)
async def update_assembly(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    data: AssemblyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.update_assembly(db, copro_id, assembly_id, data)


@router.delete(
    "/{copro_id}/assemblies/{assembly_id}", status_code=204, summary="Supprimer une assemblée"
)
async def delete_assembly(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproAGService.delete_assembly(db, copro_id, assembly_id)


@router.post(
    "/{copro_id}/assemblies/{assembly_id}/resolutions",
    response_model=AssemblyDetail,
    status_code=201,
    summary="Ajouter une résolution",
)
async def add_resolution(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    data: ResolutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.add_resolution(db, copro_id, assembly_id, data)


@router.put(
    "/{copro_id}/assemblies/{assembly_id}/resolutions/{resolution_id}",
    response_model=AssemblyDetail,
    summary="Modifier une résolution",
)
async def update_resolution(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    resolution_id: uuid.UUID,
    data: ResolutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.update_resolution(db, copro_id, assembly_id, resolution_id, data)


@router.delete(
    "/{copro_id}/assemblies/{assembly_id}/resolutions/{resolution_id}",
    status_code=204,
    summary="Supprimer une résolution",
)
async def delete_resolution(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    resolution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproAGService.delete_resolution(db, copro_id, assembly_id, resolution_id)


@router.post(
    "/{copro_id}/assemblies/{assembly_id}/resolutions/{resolution_id}/vote",
    response_model=AssemblyDetail,
    summary="Enregistrer un vote",
)
async def set_vote(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    resolution_id: uuid.UUID,
    data: VoteIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.set_vote(
        db, copro_id, assembly_id, resolution_id, data.owner_id, data.choice
    )


@router.delete(
    "/{copro_id}/assemblies/{assembly_id}/resolutions/{resolution_id}/vote/{owner_id}",
    response_model=AssemblyDetail,
    summary="Retirer un vote",
)
async def clear_vote(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    resolution_id: uuid.UUID,
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproAGService.clear_vote(db, copro_id, assembly_id, resolution_id, owner_id)


@router.get(
    "/{copro_id}/assemblies/{assembly_id}/convocation/pdf", summary="Convocation d'assemblée (PDF)"
)
async def assembly_convocation_pdf(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    return await _assembly_pdf(db, current_user, copro_id, assembly_id, "convocation")


@router.get(
    "/{copro_id}/assemblies/{assembly_id}/pv/pdf", summary="Procès-verbal d'assemblée (PDF)"
)
async def assembly_pv_pdf(
    copro_id: uuid.UUID,
    assembly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    return await _assembly_pdf(db, current_user, copro_id, assembly_id, "pv")


# ── Fonds de travaux (ALUR) ──────────────────────────────────────────────────
@router.get(
    "/{copro_id}/works-fund", response_model=WorksFundSummary, summary="Fonds de travaux (solde)"
)
async def works_fund(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproExtrasService.works_fund(db, copro_id)


@router.post(
    "/{copro_id}/works-fund",
    response_model=WorksFundEntryResponse,
    status_code=201,
    summary="Ajouter un mouvement de fonds de travaux",
)
async def add_works_entry(
    copro_id: uuid.UUID,
    data: WorksFundEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproExtrasService.add_works_entry(db, copro_id, data, created_by=current_user.id)


@router.delete(
    "/{copro_id}/works-fund/{entry_id}", status_code=204, summary="Supprimer un mouvement"
)
async def delete_works_entry(
    copro_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproExtrasService.delete_works_entry(db, copro_id, entry_id)


# ── Carnet d'entretien ───────────────────────────────────────────────────────
@router.get(
    "/{copro_id}/maintenance",
    response_model=list[MaintenanceResponse],
    summary="Carnet d'entretien",
)
async def list_maintenance(
    copro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproExtrasService.list_maintenance(db, copro_id)


@router.post(
    "/{copro_id}/maintenance",
    response_model=MaintenanceResponse,
    status_code=201,
    summary="Ajouter une entrée d'entretien",
)
async def add_maintenance(
    copro_id: uuid.UUID,
    data: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproExtrasService.add_maintenance(db, copro_id, data, created_by=current_user.id)


@router.put(
    "/{copro_id}/maintenance/{maint_id}",
    response_model=MaintenanceResponse,
    summary="Modifier une entrée d'entretien",
)
async def update_maintenance(
    copro_id: uuid.UUID,
    maint_id: uuid.UUID,
    data: MaintenanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    return await CoproExtrasService.update_maintenance(db, copro_id, maint_id, data)


@router.delete(
    "/{copro_id}/maintenance/{maint_id}",
    status_code=204,
    summary="Supprimer une entrée d'entretien",
)
async def delete_maintenance(
    copro_id: uuid.UUID,
    maint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    await _assert_copro(db, current_user, copro_id)
    await CoproExtrasService.delete_maintenance(db, copro_id, maint_id)


async def _assembly_pdf(db, current_user, copro_id, assembly_id, doc: str):
    from fastapi.responses import Response

    from app.services.pdf_service import html_to_pdf, render_template
    from app.services.template_layout_service import get_layout
    from app.utils.filename import _slug as _slug_name
    from app.utils.filename import simple_doc_filename

    await _assert_copro(db, current_user, copro_id)
    ctx = await CoproAGService.pdf_context(db, copro_id, assembly_id)
    template = "copro_convocation.html.j2" if doc == "convocation" else "copro_pv.html.j2"
    html = render_template(
        template,
        {
            "ctx": ctx,
            "layout": get_layout(),
            "manager_name": current_user.full_name or "",
            "manager_address": getattr(current_user, "full_address", None) or "",
            "signature_uri": (getattr(current_user, "signature", None) or ""),
            "tampon_uri": (getattr(current_user, "tampon", None) or ""),
        },
    )
    pdf = html_to_pdf(html)
    prefix = "convocation-ag" if doc == "convocation" else "pv-ag"
    filename = simple_doc_filename(prefix, _slug_name(ctx["copro_name"]), _slug_name(ctx["title"]))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
