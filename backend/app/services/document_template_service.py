"""Seed des templates de documents par défaut pour un gestionnaire.

Utilisé à la création d'un compte gestionnaire (UserService.create) et par
l'endpoint POST /templates/initialize-defaults.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_template import DocumentTemplate, TemplateType
from app.services.avis_blocks_render_service import default_avis_blocks, default_blocks, DEFAULT_THEME

# Rôles qui génèrent des documents → reçoivent les templates par défaut.
TEMPLATE_OWNER_ROLES = {"admin", "gestionnaire", "gestionnaire_proprio"}

# Anciens noms canoniques de templates par défaut à migrer vers le nom courant.
_OLD_DEFAULT_NAMES = {"Avis d'échéance standard", "Quittance de loyer standard"}


DEFAULT_TEMPLATES = {
    TemplateType.AVIS_ECHEANCE: {
        "name": "Avis d'échéance",
        "content_html": """<h2>Avis d'échéance</h2>
<p style="text-align:center;color:#6b7280;margin-top:0;">Loyer · {{month}}</p>
<p>{{civility_greeting}},</p>
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
        # Éditeur par blocs (mise en page moderne, rendu prioritaire si présent).
        "blocks": default_avis_blocks(),
        "theme": DEFAULT_THEME,
    },
    TemplateType.QUITTANCE: {
        "name": "Quittance de loyer",
        "content_html": """<h2>Quittance de loyer</h2>
<p style="text-align:center;color:#6b7280;margin-top:0;">{{month}}</p>
<p>{{civility_greeting}},</p>
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
        "blocks": default_blocks("quittance"),
        "theme": DEFAULT_THEME,
    },
    TemplateType.REGULARISATION_CHARGES: {
        "name": "Régularisation de charges locatives",
        "content_html": "<p>Régularisation de charges locatives : {{period_range}}.</p>",
        "footer_text": "Document établi conformément à l'article 23 de la loi n° 89-462 du 6 juillet 1989.",
        "blocks": default_blocks("regularisation_charges"),
        "theme": DEFAULT_THEME,
    },
    TemplateType.REVISION_LOYER: {
        "name": "Révision loyer",
        "content_html": "<p>Révision de loyer (IRL).</p>",
        "footer_text": "Révision effectuée conformément à l'article 17-1 de la loi n° 89-462 du 6 juillet 1989.",
        "blocks": default_blocks("revision_loyer"),
        "theme": DEFAULT_THEME,
    },
    TemplateType.TAXES_FONCIERES: {
        "name": "Décompte Taxes Foncières",
        "content_html": "<p>Décompte taxes foncières (TEOM) : {{period_range}}.</p>",
        "footer_text": "Récupération conforme à l'article 23 de la loi n° 89-462 du 6 juillet 1989.",
        "blocks": default_blocks("taxes_foncieres"),
        "theme": DEFAULT_THEME,
    },
    TemplateType.LETTRE_RELANCE: {
        "name": "Lettre de relance",
        "content_html": """<h2>Lettre de relance</h2>
<p>{{civility_greeting}},</p>
<p>Sauf erreur ou omission de notre part, le loyer de la période <strong>{{period_range}}</strong>, dont l'échéance était fixée au <strong>{{due_date}}</strong>, demeure impayé à ce jour.</p>
<p>Le solde restant dû s'élève à <strong>{{amount_due}}</strong>. Nous vous remercions de bien vouloir le régulariser sous huitaine.</p>
<p style="color:#6b7280;">Si votre règlement a croisé ce courrier, nous vous prions de ne pas en tenir compte.</p>""",
        "footer_text": "Relance amiable établie conformément à l'article 7 de la loi n° 89-462 du 6 juillet 1989.",
        "blocks": default_blocks("lettre_relance"),
        "theme": DEFAULT_THEME,
    },
    TemplateType.PLAN_APUREMENT: {
        "name": "Plan d'apurement",
        "content_html": """<h2>Plan d'apurement</h2>
<p>{{civility_greeting}},</p>
<p>Suite au loyer impayé de la période <strong>{{period_range}}</strong> (échéance du <strong>{{due_date}}</strong>), nous convenons ensemble d'un plan d'apurement pour régler le solde restant dû de <strong>{{amount_due}}</strong> selon l'échéancier convenu.</p>
<p style="color:#6b7280;">À défaut de paiement d'une seule échéance, la totalité du solde restant dû redeviendra immédiatement exigible.</p>""",
        "footer_text": "Plan d'apurement amiable. Le présent plan ne vaut pas renonciation au recouvrement du solde.",
        "blocks": default_blocks("plan_apurement"),
        "theme": DEFAULT_THEME,
    },
}

# Types de documents retirés de la papeterie (désactivés au démarrage).
_RETIRED_TYPES = [
    TemplateType.LETTRE_RESILIATION.value,
    TemplateType.CONTRAT_BAIL.value, TemplateType.ETAT_DES_LIEUX.value,
]


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
    courant, pour propager les refontes de contenu aux comptes existants.
    Couvre les 6 types par défaut. Idempotent (n'écrit que si le contenu diffère).
    Ne touche QUE les templates is_default ; les templates personnalisés ne sont
    jamais modifiés."""
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
            # Renomme les anciens noms canoniques vers le nom courant (sans toucher
            # aux modèles renommés par l'utilisateur).
            if t.name in _OLD_DEFAULT_NAMES and t.name != d["name"]:
                t.name = d["name"]
                updated += 1
            # Modèle par blocs (avis) : on garde les templates PAR DÉFAUT alignés sur
            # le modèle canonique courant — comme pour content_html ci-dessus — afin
            # que les évolutions (icônes, nouvelles lignes…) atteignent les comptes
            # existants. (Une personnalisation se fait sur un modèle dupliqué.)
            if d.get("blocks") and getattr(t, "blocks", None) != d["blocks"]:
                # Réassignation (objet neuf) pour que SQLAlchemy détecte le changement JSONB.
                t.blocks = [dict(b) for b in d["blocks"]]
                t.theme = dict(d["theme"]) if d.get("theme") else None
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
