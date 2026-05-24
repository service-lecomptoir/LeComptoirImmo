"""API Templates — gestion des modèles de documents."""
import uuid
import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.document_template import DocumentTemplate, TemplateType
from app.schemas.document_template import (
    DocumentTemplateCreate, DocumentTemplateUpdate, DocumentTemplateResponse
)

router = APIRouter(prefix="/templates", tags=["Templates"])

UPLOAD_DIR = "uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Templates par défaut incorporés
DEFAULT_TEMPLATES = {
    TemplateType.AVIS_ECHEANCE: {
        "name": "Avis d'échéance standard",
        "content_html": """<h2>AVIS D'ÉCHÉANCE</h2>
<p>Cher(e) {{tenant_name}},</p>
<p>Nous vous rappelons que votre loyer du mois de <strong>{{month}}</strong> est à régler avant le <strong>{{due_date}}</strong>.</p>
<table>
  <tr><td>Loyer :</td><td>{{rent_amount}} €</td></tr>
  <tr><td>Charges :</td><td>{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide personnelle au logement :</td><td>- {{apl_amount}} €</td></tr>{{/if}}
  <tr><td><strong>Total à payer :</strong></td><td><strong>{{total_due}} €</strong></td></tr>
</table>
<p>Bien :</p>
<p>{{property_name}} — {{unit_ref}}</p>
<p>Cordialement,<br>{{company_name}}</p>""",
        "footer_text": "Ce document est généré automatiquement. Pour toute question, contactez votre gestionnaire.",
    },
    TemplateType.QUITTANCE: {
        "name": "Quittance de loyer standard",
        "content_html": """<h2>QUITTANCE DE LOYER</h2>
<p>Je soussigné(e) {{company_name}}, gestionnaire du bien sis <strong>{{property_address}}</strong>,</p>
<p>déclare avoir reçu de <strong>{{tenant_name}}</strong>, locataire dudit bien,</p>
<p>la somme de <strong>{{amount_paid}} €</strong> au titre du loyer et charges du mois de <strong>{{month}}</strong>.</p>
<br/>
<table>
  <tr><td>Loyer :</td><td>{{rent_amount}} €</td></tr>
  <tr><td>Charges :</td><td>{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide personnelle au logement :</td><td>- {{apl_amount}} €</td></tr>{{/if}}
  <tr><td><strong>Montant reçu :</strong></td><td><strong>{{amount_paid}} €</strong></td></tr>
</table>
<p>Et lui en donne bonne et valable quittance.</p>
<p>Fait le {{date}}</p>""",
        "footer_text": "Cette quittance est valable sous réserve d'encaissement.",
    },
    TemplateType.LETTRE_RELANCE: {
        "name": "Lettre de relance standard",
        "content_html": """<h2>MISE EN DEMEURE DE PAYER</h2>
<p>Cher(e) {{tenant_name}},</p>
<p>Sauf erreur ou omission de notre part, nous constatons que votre loyer du mois de <strong>{{month}}</strong> d'un montant de <strong>{{amount}} €</strong> n'a pas été réglé à ce jour.</p>
<p>Nous vous demandons de bien vouloir régulariser cette situation dans les <strong>8 jours</strong>.</p>
<p>Sans réponse de votre part, nous nous verrons dans l'obligation d'engager les procédures légales en vigueur.</p>
<p>Cordialement,<br>{{company_name}}</p>""",
        "footer_text": "Lettre recommandée avec accusé de réception.",
    },
    TemplateType.LETTRE_RESILIATION: {
        "name": "Lettre de résiliation standard",
        "content_html": """<h2>CONGÉ DONNÉ PAR LE BAILLEUR</h2>
<p>Cher(e) {{tenant_name}},</p>
<p>Nous vous informons par la présente que nous mettons fin à votre contrat de location concernant le logement situé au :</p>
<p><strong>{{property_address}}</strong></p>
<p>Ce congé prend effet à la date d'échéance du bail suivant le délai légal de préavis.</p>
<p>Nous vous remercions de bien vouloir libérer les lieux à cette date et de nous restituer les clés.</p>
<p>Cordialement,<br>{{company_name}}</p>""",
        "footer_text": "Lettre recommandée avec accusé de réception.",
    },
    TemplateType.CONTRAT_BAIL: {
        "name": "Contrat de bail standard",
        "content_html": """<h2>CONTRAT DE LOCATION</h2>
<p><strong>ENTRE LES SOUSSIGNÉS :</strong></p>
<p>Le bailleur : <strong>{{company_name}}</strong>, ci-après dénommé « le Bailleur »,</p>
<p>ET</p>
<p>Le preneur : <strong>{{tenant_name}}</strong>, ci-après dénommé « le Locataire »,</p>
<p><strong>IL A ÉTÉ CONVENU CE QUI SUIT :</strong></p>
<p><strong>Article 1 — Objet du bail</strong></p>
<p>Le Bailleur loue au Locataire le logement désigné ci-après : <strong>{{unit_ref}}</strong> situé à <strong>{{property_address}}</strong>.</p>
<p><strong>Article 2 — Durée</strong></p>
<p>Le présent bail est consenti pour une durée de 3 ans, à compter du <strong>{{date}}</strong>.</p>
<p><strong>Article 3 — Loyer</strong></p>
<p>Le loyer mensuel est fixé à <strong>{{rent_amount}} €</strong> hors charges, auxquelles s'ajoutent des provisions sur charges de <strong>{{charges_amount}} €</strong>, soit un total de <strong>{{total_due}} €</strong> par mois.</p>
<p>Le loyer est payable le {{due_date}} de chaque mois.</p>
<p>Fait en deux exemplaires,<br>{{company_name}}</p>""",
        "footer_text": "Document établi conformément à la loi n° 89-462 du 6 juillet 1989.",
    },
    TemplateType.ETAT_DES_LIEUX: {
        "name": "État des lieux standard",
        "content_html": """<h2>ÉTAT DES LIEUX</h2>
<p><strong>Logement :</strong> {{unit_ref}} — {{property_address}}</p>
<p><strong>Locataire :</strong> {{tenant_name}}</p>
<p><strong>Date :</strong> {{date}}</p>
<hr/>
<h3>ÉTAT GÉNÉRAL DU LOGEMENT</h3>
<table style="width:100%;border-collapse:collapse;">
  <tr style="background:#f3f4f6;">
    <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">Pièce</th>
    <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">État</th>
    <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">Observations</th>
  </tr>
  <tr>
    <td style="padding:8px;border:1px solid #e5e7eb;">Entrée</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
  </tr>
  <tr>
    <td style="padding:8px;border:1px solid #e5e7eb;">Séjour</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
  </tr>
  <tr>
    <td style="padding:8px;border:1px solid #e5e7eb;">Cuisine</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
  </tr>
  <tr>
    <td style="padding:8px;border:1px solid #e5e7eb;">Chambre</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
  </tr>
  <tr>
    <td style="padding:8px;border:1px solid #e5e7eb;">Salle de bain</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
    <td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td>
  </tr>
</table>
<br/>
<p>Signatures :</p>
<p>Le Bailleur : __________________ Le Locataire : __________________</p>""",
        "footer_text": "Cet état des lieux a été établi contradictoirement entre le bailleur et le locataire.",
    },
}


@router.get("", response_model=List[DocumentTemplateResponse])
async def list_templates(
    template_type: Optional[TemplateType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    q = select(DocumentTemplate)
    if template_type:
        q = q.where(DocumentTemplate.template_type == template_type)
    q = q.where(DocumentTemplate.is_active.is_(True)).order_by(
        DocumentTemplate.template_type, DocumentTemplate.name
    )
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/initialize-defaults", status_code=status.HTTP_200_OK)
async def initialize_defaults(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    """Crée les templates par défaut s'ils n'existent pas."""
    created = 0
    for ttype, defaults in DEFAULT_TEMPLATES.items():
        existing = await db.execute(
            select(DocumentTemplate)
            .where(DocumentTemplate.template_type == ttype)
            .where(DocumentTemplate.is_default.is_(True))
        )
        if existing.scalar_one_or_none() is None:
            tmpl = DocumentTemplate(
                template_type=ttype,
                is_default=True,
                is_active=True,
                **defaults,
            )
            db.add(tmpl)
            created += 1
    await db.commit()
    return {"created": created, "message": f"{created} template(s) par défaut créé(s)"}


@router.post("", response_model=DocumentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: DocumentTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    # Si nouveau défaut, désactiver l'ancien
    if data.is_default:
        await _unset_default(db, data.template_type)

    tmpl = DocumentTemplate(**data.model_dump())
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=DocumentTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    return tmpl


@router.patch("/{template_id}", response_model=DocumentTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: DocumentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")

    if data.is_default:
        await _unset_default(db, tmpl.template_type, exclude_id=template_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.post("/{template_id}/upload-logo", response_model=DocumentTemplateResponse)
async def upload_logo(
    template_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")

    # Valider le type
    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(status_code=400, detail="Format d'image non supporté (PNG, JPG, SVG, WebP)")

    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"logo_{template_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    tmpl.logo_path = filepath
    tmpl.logo_url = f"/uploads/logos/{filename}"
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    if tmpl.is_default:
        raise HTTPException(status_code=400, detail="Le template par défaut ne peut pas être supprimé")
    await db.delete(tmpl)
    await db.commit()


async def _unset_default(db, template_type: TemplateType, exclude_id: uuid.UUID = None):
    """Désactive le statut 'défaut' des autres templates du même type."""
    q = select(DocumentTemplate).where(
        DocumentTemplate.template_type == template_type,
        DocumentTemplate.is_default.is_(True),
    )
    if exclude_id:
        q = q.where(DocumentTemplate.id != exclude_id)
    result = await db.execute(q)
    for tmpl in result.scalars().all():
        tmpl.is_default = False
    await db.flush()
