"""Seed des templates de documents par défaut pour un gestionnaire.

Utilisé à la création d'un compte gestionnaire (UserService.create) et par
l'endpoint POST /templates/initialize-defaults.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_template import DocumentTemplate, TemplateType

# Rôles qui génèrent des documents → reçoivent les templates par défaut.
TEMPLATE_OWNER_ROLES = {"admin", "gestionnaire", "gestionnaire_proprio"}


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
<p>{{property_name}} — {{property_address}}</p>
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
  <tr><td style="padding:8px;border:1px solid #e5e7eb;">Entrée</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td></tr>
  <tr><td style="padding:8px;border:1px solid #e5e7eb;">Séjour</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td></tr>
  <tr><td style="padding:8px;border:1px solid #e5e7eb;">Cuisine</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td></tr>
  <tr><td style="padding:8px;border:1px solid #e5e7eb;">Chambre</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td></tr>
  <tr><td style="padding:8px;border:1px solid #e5e7eb;">Salle de bain</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td><td style="padding:8px;border:1px solid #e5e7eb;">&nbsp;</td></tr>
</table>
<br/>
<p>Signatures :</p>
<p>Le Bailleur : __________________ Le Locataire : __________________</p>""",
        "footer_text": "Cet état des lieux a été établi contradictoirement entre le bailleur et le locataire.",
    },
}


async def ensure_default_templates(db: AsyncSession, gestionnaire_id: uuid.UUID) -> int:
    """Crée les templates par défaut manquants pour ce gestionnaire. Idempotent.
    N'effectue PAS de commit (laissé à l'appelant). Retourne le nombre créé."""
    created = 0
    for ttype, defaults in DEFAULT_TEMPLATES.items():
        existing = await db.execute(
            select(DocumentTemplate)
            .where(DocumentTemplate.template_type == ttype)
            .where(DocumentTemplate.is_default.is_(True))
            .where(DocumentTemplate.gestionnaire_id == gestionnaire_id)
        )
        if existing.scalar_one_or_none() is None:
            db.add(DocumentTemplate(
                template_type=ttype,
                is_default=True,
                is_active=True,
                gestionnaire_id=gestionnaire_id,
                **defaults,
            ))
            created += 1
    if created:
        await db.flush()
    return created
