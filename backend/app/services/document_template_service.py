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
<p style="text-align:center;color:#6b7280;margin:0 0 14px;">Loyer du {{month}}</p>

<table>
  <tr><td style="color:#6b7280;width:35%;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Période</td><td>{{month}}</td></tr>
  <tr><td style="color:#6b7280;">Échéance</td><td><strong>{{due_date}}</strong></td></tr>
</table>

<p>Madame, Monsieur,</p>
<p>Nous avons l'honneur de vous adresser ci-dessous votre avis d'échéance pour la période visée. Nous vous remercions de bien vouloir procéder à son règlement avant la date d'échéance mentionnée ci-dessus.</p>

<h3>Décompte</h3>
<table>
  <tr><td>Loyer hors charges</td><td style="text-align:right;">{{rent_amount}} €</td></tr>
  <tr><td>Provisions sur charges</td><td style="text-align:right;">{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide au logement (APL — tiers payant)</td><td style="text-align:right;color:#047857;">&minus; {{apl_amount}} €</td></tr>{{/if}}
  <tr><td style="border-top:2px solid #0d2f5c;"><strong>Total à régler</strong></td><td style="border-top:2px solid #0d2f5c;text-align:right;"><strong>{{total_due}} €</strong></td></tr>
</table>

<h3>Modalités de règlement</h3>
<p>Vous pouvez régler votre loyer par <strong>virement bancaire</strong> en mentionnant votre nom et la période en référence, ou par tout autre moyen convenu avec votre gestionnaire. Les coordonnées bancaires vous ont été communiquées à la signature du bail et peuvent vous être renvoyées sur simple demande.</p>

<p style="color:#6b7280;">Nous restons à votre disposition pour tout renseignement complémentaire et vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>

<p style="text-align:right;margin-top:22px;"><strong>{{company_name}}</strong></p>""",
        "footer_text": "Avis d'échéance — document généré par votre gestionnaire. Toute correspondance est à adresser à l'agence.",
    },
    TemplateType.QUITTANCE: {
        "name": "Quittance de loyer standard",
        "content_html": """<h2>Quittance de loyer</h2>
<p style="text-align:center;color:#6b7280;margin:0 0 14px;">{{month}}</p>

<table>
  <tr><td style="color:#6b7280;width:35%;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Période</td><td>{{month}}</td></tr>
</table>

<p>Je soussigné(e), <strong>{{company_name}}</strong>, agissant en qualité de mandataire du bailleur, déclare avoir reçu de <strong>{{tenant_name}}</strong> la somme indiquée ci-dessous au titre du loyer et des charges du logement désigné ci-dessus, et lui en donne quittance pour la période concernée.</p>

<h3>Détail du règlement</h3>
<table>
  <tr><td>Loyer hors charges</td><td style="text-align:right;">{{rent_amount}} €</td></tr>
  <tr><td>Provisions sur charges</td><td style="text-align:right;">{{charges_amount}} €</td></tr>
  {{#if apl_amount}}<tr><td>Aide au logement (APL — tiers payant)</td><td style="text-align:right;color:#047857;">&minus; {{apl_amount}} €</td></tr>{{/if}}
  <tr><td style="border-top:2px solid #0d2f5c;"><strong>Montant encaissé</strong></td><td style="border-top:2px solid #0d2f5c;text-align:right;"><strong>{{amount_paid}} €</strong></td></tr>
</table>

<p style="color:#6b7280;margin-top:18px;">La présente quittance annule tous les reçus qui auraient pu être délivrés précédemment au titre de la même période. Elle est délivrée sous réserve d'encaissement effectif des sommes mentionnées ci-dessus.</p>

<p style="text-align:right;margin-top:22px;">Fait le {{date}}<br/><strong>{{company_name}}</strong></p>""",
        "footer_text": "Quittance délivrée en application de l'article 21 de la loi n° 89-462 du 6 juillet 1989. Sous réserve d'encaissement.",
    },
    TemplateType.LETTRE_RELANCE: {
        "name": "Lettre de relance standard",
        "content_html": """<h2>Mise en demeure de payer</h2>

<table>
  <tr><td style="color:#6b7280;width:35%;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Période en retard</td><td>{{month}}</td></tr>
</table>

<p><strong>Objet :</strong> Mise en demeure de payer — Loyer impayé</p>

<p>Madame, Monsieur,</p>
<p>Sauf erreur ou omission de notre part, nous constatons que le loyer du mois de <strong>{{month}}</strong>, d'un montant de <strong>{{total_due}} €</strong>, n'a pas été réglé à ce jour malgré l'avis d'échéance qui vous a été adressé.</p>

<p>En conséquence, nous vous mettons en demeure de procéder à son règlement intégral dans un délai de <strong>8 jours</strong> à compter de la réception de la présente.</p>

<p>À défaut, et conformément aux stipulations de votre bail, nous nous verrons contraints d'engager toutes procédures utiles — notamment la délivrance d'un commandement de payer par voie d'huissier et, le cas échéant, la résiliation du bail aux torts du locataire, sans préjudice de toutes sommes dues.</p>

<p>Nous vous rappelons que tout retard de paiement peut entraîner l'application d'intérêts de retard conformément aux clauses du contrat de location.</p>

<p style="color:#6b7280;">Nous restons à votre disposition pour étudier toute solution amiable et vous prions d'agréer, Madame, Monsieur, nos salutations distinguées.</p>

<p style="text-align:right;margin-top:22px;"><strong>{{company_name}}</strong></p>""",
        "footer_text": "Lettre recommandée avec accusé de réception. Loi n° 89-462 du 6 juillet 1989.",
    },
    TemplateType.LETTRE_RESILIATION: {
        "name": "Lettre de résiliation standard",
        "content_html": """<h2>Congé donné par le bailleur</h2>

<table>
  <tr><td style="color:#6b7280;width:35%;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Date</td><td>{{date}}</td></tr>
</table>

<p><strong>Objet :</strong> Congé donné par le bailleur</p>

<p>Madame, Monsieur,</p>
<p>Nous avons l'honneur de vous notifier, par la présente, le congé concernant le logement objet de votre bail :</p>

<p style="background:#f9fafb;border-left:3px solid #0d2f5c;padding:10px 14px;margin:14px 0;"><strong>{{property_name}}</strong><br/>{{property_address}}</p>

<p>Conformément aux dispositions de la loi n° 89-462 du 6 juillet 1989, ce congé est donné avec un préavis légal de <strong>six mois</strong> avant la date d'échéance du bail. Le motif du présent congé vous sera précisé dans les formes prévues par la loi.</p>

<p>Nous vous remercions de bien vouloir libérer les lieux à l'issue du préavis et de procéder à la restitution des clés, ainsi qu'à l'établissement contradictoire de l'état des lieux de sortie.</p>

<p style="color:#6b7280;">Nous restons à votre disposition pour organiser les modalités de votre départ et vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>

<p style="text-align:right;margin-top:22px;"><strong>{{company_name}}</strong></p>""",
        "footer_text": "Lettre recommandée avec accusé de réception. Loi n° 89-462 du 6 juillet 1989.",
    },
    TemplateType.CONTRAT_BAIL: {
        "name": "Contrat de bail standard",
        "content_html": """<h2>Contrat de location à usage d'habitation</h2>

<table>
  <tr><td style="color:#6b7280;width:35%;">Bailleur</td><td><strong>{{company_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Date d'entrée</td><td>{{date}}</td></tr>
</table>

<h3>Article 1 — Objet du bail</h3>
<p>Le bailleur loue au locataire, qui accepte, le logement désigné ci-dessus, à usage exclusif d'habitation principale.</p>

<h3>Article 2 — Durée</h3>
<p>Le présent bail est conclu pour une durée de <strong>trois ans</strong> à compter du {{date}}. Il est reconductible tacitement aux conditions prévues par la loi n° 89-462 du 6 juillet 1989.</p>

<h3>Article 3 — Loyer et charges</h3>
<table>
  <tr><td>Loyer mensuel hors charges</td><td style="text-align:right;"><strong>{{rent_amount}} €</strong></td></tr>
  <tr><td>Provisions sur charges</td><td style="text-align:right;">{{charges_amount}} €</td></tr>
  <tr><td style="border-top:2px solid #0d2f5c;"><strong>Total mensuel</strong></td><td style="border-top:2px solid #0d2f5c;text-align:right;"><strong>{{total_due}} €</strong></td></tr>
</table>
<p>Le loyer est payable à terme échu, le {{due_date}} de chaque mois.</p>

<h3>Article 4 — Révision du loyer</h3>
<p>Le loyer fera l'objet d'une révision annuelle selon l'évolution de l'Indice de Référence des Loyers (IRL) publié par l'INSEE.</p>

<h3>Article 5 — Dépôt de garantie</h3>
<p>Un dépôt de garantie sera versé par le locataire à la signature du présent contrat, dans les conditions et limites fixées par la loi.</p>

<p style="margin-top:22px;">Fait en deux exemplaires originaux, le {{date}}.</p>

<table style="margin-top:14px;">
  <tr>
    <td style="text-align:center;width:50%;"><strong>Le Bailleur</strong><br/><br/>{{company_name}}</td>
    <td style="text-align:center;"><strong>Le Locataire</strong><br/><br/>{{tenant_name}}</td>
  </tr>
</table>""",
        "footer_text": "Contrat établi conformément à la loi n° 89-462 du 6 juillet 1989. Annexes obligatoires : DPE, état des risques (ERP), notice d'information.",
    },
    TemplateType.ETAT_DES_LIEUX: {
        "name": "État des lieux standard",
        "content_html": """<h2>État des lieux</h2>

<table>
  <tr><td style="color:#6b7280;width:35%;">Locataire</td><td><strong>{{tenant_name}}</strong></td></tr>
  <tr><td style="color:#6b7280;">Logement</td><td>{{property_name}}</td></tr>
  <tr><td style="color:#6b7280;">Adresse</td><td>{{property_address}}</td></tr>
  <tr><td style="color:#6b7280;">Date</td><td>{{date}}</td></tr>
  <tr><td style="color:#6b7280;">Type</td><td>État des lieux d'entrée / de sortie (à préciser)</td></tr>
</table>

<h3>Caractéristiques générales</h3>
<p>Compteurs (électricité, eau, gaz), nombre de clés et badges, équipements communs : à compléter contradictoirement entre les parties.</p>

<h3>État pièce par pièce</h3>
<table>
  <tr style="background:#f3f4f6;">
    <td><strong>Pièce</strong></td>
    <td><strong>État (B / M / U)</strong></td>
    <td><strong>Observations</strong></td>
  </tr>
  <tr><td>Entrée</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Séjour / salon</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Cuisine</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Chambre 1</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Chambre 2</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Salle de bain</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>WC</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  <tr><td>Annexes (cave, parking, balcon)</td><td>&nbsp;</td><td>&nbsp;</td></tr>
</table>
<p style="color:#6b7280;font-size:0.95em;">B : bon état · M : état moyen · U : usé / à remettre en état.</p>

<p style="margin-top:22px;">Le présent état des lieux est dressé contradictoirement entre les parties et fait foi sauf preuve contraire.</p>

<table style="margin-top:14px;">
  <tr>
    <td style="text-align:center;width:50%;"><strong>Le Bailleur</strong><br/><br/>{{company_name}}</td>
    <td style="text-align:center;"><strong>Le Locataire</strong><br/><br/>{{tenant_name}}</td>
  </tr>
</table>""",
        "footer_text": "État des lieux dressé contradictoirement entre les parties (loi n° 89-462 du 6 juillet 1989).",
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
    """Met à jour le contenu des templates PAR DÉFAUT vers le modèle canonique
    courant, pour propager une refonte de mise en page aux comptes existants.
    Idempotent (n'écrit que si le contenu diffère). Ne touche QUE les templates
    is_default ; les templates personnalisés (non-défaut) ne sont jamais modifiés.
    Couvre les 6 types par défaut (avis, quittance, relance, résiliation, bail,
    état des lieux) pour propager les refontes de contenu professionnel."""
    updated = 0
    for ttype, d in DEFAULT_TEMPLATES.items():
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
