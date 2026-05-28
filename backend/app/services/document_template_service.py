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
        "content_html": """<h2>Avis d'échéance</h2>
<p style="text-align:center;color:#6b7280;margin-top:0;">Loyer · {{month}}</p>
<p>Madame, Monsieur,</p>
<p>Nous vous prions de bien vouloir procéder au règlement de votre loyer, selon le détail ci-dessous, à échéance du <strong>{{due_date}}</strong>.</p>
<h3>Détail du loyer</h3>
<table>
  <tr><td>Loyer hors charges</td><td style="text-align:right;">{{rent_amount}} €</td></tr>
  <tr><td>Provision pour charges</td><td style="text-align:right;">{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide personnelle au logement</td><td style="text-align:right;">&minus; {{apl_amount}} €</td></tr>{{/if}}
  <tr><td style="border-top:2px solid #0d2f5c;"><strong>Total à payer</strong></td><td style="text-align:right;border-top:2px solid #0d2f5c;"><strong>{{total_due}} €</strong></td></tr>
</table>
<p style="color:#6b7280;">Nous vous remercions de votre confiance et restons à votre disposition pour toute question.</p>""",
        "footer_text": "Document généré par Le Comptoir Immo. Pour toute question, contactez votre gestionnaire.",
    },
    TemplateType.QUITTANCE: {
        "name": "Quittance de loyer standard",
        "content_html": """<h2>Quittance de loyer</h2>
<p style="text-align:center;color:#6b7280;margin-top:0;">{{month}}</p>
<p>Madame, Monsieur,</p>
<p>Nous accusons réception de la somme de <strong>{{amount_paid}} €</strong> au titre du loyer et des charges du mois de <strong>{{month}}</strong>, et vous en donnons quittance.</p>
<h3>Détail</h3>
<table>
  <tr><td>Loyer hors charges</td><td style="text-align:right;">{{rent_amount}} €</td></tr>
  <tr><td>Provision pour charges</td><td style="text-align:right;">{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide personnelle au logement</td><td style="text-align:right;">&minus; {{apl_amount}} €</td></tr>{{/if}}
  <tr><td style="border-top:2px solid #0d2f5c;"><strong>Montant réglé</strong></td><td style="text-align:right;border-top:2px solid #0d2f5c;"><strong>{{amount_paid}} €</strong></td></tr>
</table>
<p>La présente quittance annule tous les reçus établis précédemment pour la même période.</p>
<p style="color:#6b7280;">Fait le {{date}}.</p>""",
        "footer_text": "Quittance délivrée conformément à l'article 21 de la loi n°89-462 du 6 juillet 1989. Valable sous réserve d'encaissement.",
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


async def backfill_all_managers(db: AsyncSession) -> int:
    """Seed les templates par défaut pour TOUS les comptes gestionnaire existants qui
    n'en ont pas encore (comptes créés avant l'auto-seed). Idempotent. Retourne le
    nombre de gestionnaires nouvellement dotés."""
    from app.models.user import User
    users = (await db.execute(
        select(User.id, User.role)
    )).all()
    seeded = 0
    for uid, role in users:
        role_val = role.value if hasattr(role, "value") else str(role)
        if role_val in TEMPLATE_OWNER_ROLES:
            n = await ensure_default_templates(db, uid)
            if n:
                seeded += 1
    return seeded


async def refresh_default_bodies(db: AsyncSession) -> int:
    """Met à jour le contenu des templates PAR DÉFAUT (avis / quittance) vers le modèle
    canonique courant, pour propager une refonte de mise en page aux comptes existants.
    Idempotent (n'écrit que si le contenu diffère). Ne touche QUE les templates is_default
    de ces 2 types ; les templates personnalisés (non-défaut) ne sont jamais modifiés."""
    updated = 0
    for ttype in (TemplateType.AVIS_ECHEANCE, TemplateType.QUITTANCE):
        d = DEFAULT_TEMPLATES[ttype]
        rows = (await db.execute(
            select(DocumentTemplate).where(
                DocumentTemplate.template_type == ttype,
                DocumentTemplate.is_default.is_(True),
            )
        )).scalars().all()
        for t in rows:
            if t.content_html != d["content_html"] or t.footer_text != d["footer_text"]:
                t.content_html = d["content_html"]
                t.footer_text = d["footer_text"]
                updated += 1
    if updated:
        await db.flush()
    return updated


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
