"""Moteur d'automatisation : SEUL émetteur automatique des e-mails/SMS locataires.

Principe (exigence produit) : AUCUN envoi automatique en dur. Tout est piloté par
les `AutomationRule` configurées par le gestionnaire. Types gérés :

- ``avis_echeance``  : envoie l'avis d'échéance (PDF) du mois, ``trigger_days``
  jours avant la date d'échéance.
- ``quittance``      : envoie la quittance (PDF) quand un mois devient soldé
  (déclenché par l'événement de paiement, voir ``send_quittance_for_payment``).
- ``rappel_impaye`` / ``relance_1`` / ``relance_2`` : relance d'impayé,
  ``trigger_days`` jours APRÈS la date d'échéance, tant que le solde est dû.
- ``communication_groupee`` : manuel uniquement (non planifié).

Dédup : ``CommunicationLog.dedup_key`` (une cible + une règle = un seul envoi).
Canal : email / sms / email_sms. Le gestionnaire est mis en copie selon le
réglage ``cc_manager_emails`` (cf. cc_service).
"""

import logging
import re
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Types « relance d'impayé » (déclenchés N jours après l'échéance).
_REMINDER_TYPES = {"rappel_impaye", "relance_1", "relance_2"}
_REMINDER_LABELS = {
    "rappel_impaye": "Rappel de loyer",
    "relance_1": "Relance",
    "relance_2": "Mise en demeure",
}


def _rule_cc(rule) -> str | None:
    """Adresse(s) en copie de la règle (CC), nettoyées ; None si vide."""
    raw = (getattr(rule, "cc_emails", None) or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return ", ".join(parts) or None


# Signature (service) imposée selon le type : contentieux pour les relances/rappels,
# gestion locative pour tous les autres envois.
_CONTENTIEUX_TYPES = {"rappel_impaye", "relance_1", "relance_2"}


def _signature_for(rule_type: str) -> str:
    return "Service contentieux" if rule_type in _CONTENTIEUX_TYPES else "Service Gestion Locative"


async def _cc_with_manager(db, rule) -> str | None:
    """CC de la règle + e-mail du gestionnaire (toujours en copie), dédupliqué."""
    from app.models.user import User

    parts: list[str] = []
    base = _rule_cc(rule)
    if base:
        parts.extend(p.strip() for p in base.split(","))
    mid = getattr(rule, "created_by", None)
    if mid:
        u = await db.get(User, mid)
        email = getattr(u, "email", None)
        if email:
            parts.append(email.strip())
    seen, out = set(), []
    for p in parts:
        k = p.lower()
        if p and k not in seen:
            seen.add(k)
            out.append(p)
    return ", ".join(out) or None


async def _msg_templates(db, rule, tenant_lang: str | None = None):
    """(subject_tmpl, body_tmpl, sms_tmpl) à utiliser : contenu du modèle de courrier
    SÉLECTIONNÉ (onglet Communication) dans la langue du locataire si disponible
    (repli fr), sinon les champs de la règle. Onglet Communication = contenu ;
    onglet Automatisation = pilotage."""
    subj = getattr(rule, "subject", None)
    body = getattr(rule, "body_template", None)
    sms = getattr(rule, "body_template", None)
    try:
        from app.models.message_template import MessageTemplate

        tpl = (
            await db.execute(
                select(MessageTemplate)
                .where(
                    MessageTemplate.gestionnaire_id == rule.created_by,
                    MessageTemplate.rule_type == rule.rule_type,
                    MessageTemplate.is_active.is_(True),
                    MessageTemplate.is_selected.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        content = getattr(tpl, "content", None) if tpl else None
        if content:
            lang = tenant_lang or "fr"
            # Langue du locataire, sinon repli français ; jamais une langue
            # arbitraire (sinon → contenu de la règle = français par défaut).
            block = content.get(lang) or content.get("fr")
            if isinstance(block, dict):
                subj = (block.get("subject") or "").strip() or subj
                body = (block.get("body") or "").strip() or body
                sms = (block.get("sms") or "").strip() or sms
    except Exception as exc:  # noqa: BLE001 : le modèle ne doit jamais casser l'envoi
        logger.warning(
            "[automation] modèle de courrier ignoré (%s): %r", getattr(rule, "rule_type", "?"), exc
        )
    return subj, body, sms


def _render(template: str | None, ctx: dict) -> str | None:
    """Remplace les {{variables}} d'un modèle par les valeurs du contexte."""
    if not template:
        return None

    def repl(m):
        return str(ctx.get(m.group(1).strip(), m.group(0)))

    return re.sub(r"\{\{\s*([\w]+)\s*\}\}", repl, template)


async def _already_sent(db: AsyncSession, dedup_key: str) -> bool:
    from app.models.automation import CommunicationLog

    row = (
        await db.execute(
            select(CommunicationLog.id)
            .where(
                CommunicationLog.dedup_key == dedup_key,
                CommunicationLog.status == "sent",
            )
            .limit(1)
        )
    ).first()
    return row is not None


async def _log(
    db,
    *,
    rule,
    tenant_id,
    lease_id,
    channel,
    recipient,
    subject,
    body,
    status,
    dedup_key,
    error=None,
) -> None:
    from app.models.automation import CommunicationLog

    db.add(
        CommunicationLog(
            rule_id=getattr(rule, "id", None),
            tenant_id=tenant_id,
            lease_id=lease_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=(body or "")[:5000] if body else None,
            status=status,
            error_message=(str(error)[:500] if error else None),
            dedup_key=dedup_key,
            sent_at=datetime.now(UTC),
        )
    )
    await db.flush()


async def _manager_lease_ids(db: AsyncSession, manager_id) -> list:
    """Baux dans le périmètre d'un gestionnaire (créateur du bail)."""
    from app.models.lease import Lease

    rows = (
        (await db.execute(select(Lease.id).where(Lease.created_by == manager_id))).scalars().all()
    )
    return list(rows)


# ── Règles par défaut (no-régression : les envois actuels continuent) ─────────

# Jeu de règles standard créé pour chaque gestionnaire. (rule_type, name, channel,
# trigger_days, signature). Délais : avis 7 j avant l'échéance ; rappels/relances après.
# Signature : « Service contentieux » pour les impayés, « Service Gestion Locative » sinon.
_GL = "Service Gestion Locative"
_CTX = "Service contentieux"
_DEFAULT_RULES = [
    ("avis_echeance", "Avis d'échéance", "email", 7, _GL),
    ("quittance", "Quittance", "email", 0, _GL),
    ("rappel_impaye", "Rappel impayé", "email", 3, _CTX),
    ("relance_1", "Relance 1", "email", 8, _CTX),
    ("relance_2", "Relance 2 (mise en demeure)", "email_sms", 15, _CTX),
    # Événementiels (trigger_days non utilisé)
    ("revision_loyer", "Révision du loyer", "email", 0, _GL),
    ("revision_charges", "Révision des charges", "email", 0, _GL),
    ("taxe_om", "Taxe d'ordures ménagères", "email", 0, _GL),
    # Rapport mensuel : trigger_days = jour d'envoi (1er par défaut)
    ("rapport_mensuel", "Rapport mensuel de gestion", "email", 1, _GL),
    # Communications de candidature (événementielles ; e-mail au candidat)
    ("candidature_accuse", "Candidature : accusé de réception", "email", 0, _GL),
    ("candidature_pieces", "Candidature : demande de pièces", "email", 0, _GL),
    ("candidature_visite", "Candidature : invitation à visiter", "email", 0, _GL),
    ("candidature_relance_visite", "Candidature : rappel de visite", "email", 0, _GL),
    ("candidature_acceptation", "Candidature : acceptation", "email", 0, _GL),
    ("candidature_refus", "Candidature : refus", "email", 0, _GL),
]

# Règles créées DÉSACTIVÉES par défaut (le gestionnaire les active à la demande) :
#  - e-mails candidat automatiques (accusé de réception, acceptation, refus) : on
#    n'écrit pas au candidat sans action explicite du gestionnaire ;
#  - relances impayés (rappel, relance 1, mise en demeure) : déclenchées
#    manuellement après vérification, jamais envoyées au locataire sans contrôle.
_DEFAULT_INACTIVE_RULES = {
    "candidature_accuse",
    "candidature_acceptation",
    "candidature_refus",
    "rappel_impaye",
    "relance_1",
    "relance_2",
}


def _default_active(rule_type: str) -> bool:
    return rule_type not in _DEFAULT_INACTIVE_RULES


# Sujet et corps PAR DÉFAUT, ÉDITABLES dans la règle (rien en boîte noire).
# Placeholders disponibles : {{tenant_name}} {{period}} {{amount}} {{due_date}}
# {{balance}} {{property_name}}.
_DEFAULT_SUBJECTS = {
    "avis_echeance": "Avis d'échéance : {{period}}",
    "quittance": "Quittance de loyer : {{period}}",
    "rappel_impaye": "Rappel : loyer {{period}} impayé",
    "relance_1": "Relance : loyer {{period}} impayé",
    "relance_2": "Mise en demeure : loyer {{period}}",
    "revision_loyer": "Révision de votre loyer à compter du {{effective_date}}",
    "revision_charges": "Révision de vos provisions pour charges à compter du {{effective_date}}",
    "taxe_om": "Taxe d'enlèvement des ordures ménagères {{year}}",
    "rapport_mensuel": "Votre rapport de gestion : {{period}}",
    "candidature_accuse": "Votre demande de logement a bien été prise en compte",
    "candidature_pieces": "Votre dossier de location : pièces à fournir",
    "candidature_visite": "Confirmation de visite : bien {{property_ref}}",
    "candidature_relance_visite": "Rappel : votre visite approche (bien {{property_ref}})",
    "candidature_acceptation": "Votre dossier de location est accepté",
    "candidature_refus": "Réponse à votre candidature",
}
_DEFAULT_BODIES = {
    "avis_echeance": (
        "Bonjour {{tenant_name}},\n\n"
        "Vous trouverez ci-dessous votre avis d'échéance pour la période {{period}}.\n"
        "Montant dû : {{amount}} — échéance le {{due_date}}.\n"
        "Le détail de votre avis est joint à cet e-mail en PDF."
    ),
    "quittance": (
        "Bonjour {{tenant_name}},\n\n"
        "Nous accusons réception de votre règlement de {{amount}} pour la période {{period}}.\n"
        "Votre quittance de loyer est jointe à cet e-mail en PDF."
    ),
    "rappel_impaye": (
        "Bonjour {{tenant_name}},\n\n"
        "Sauf erreur de notre part, le loyer de la période {{period}} reste impayé "
        "(solde dû : {{balance}}).\n"
        "Merci de régulariser dans les meilleurs délais."
    ),
    "relance_1": (
        "Bonjour {{tenant_name}},\n\n"
        "Malgré notre précédent message, le loyer de la période {{period}} demeure impayé "
        "(solde dû : {{balance}}).\n"
        "Nous vous remercions de bien vouloir régulariser sans délai."
    ),
    "relance_2": (
        "Bonjour {{tenant_name}},\n\n"
        "À défaut de règlement du loyer de la période {{period}} (solde dû : {{balance}}), "
        "la présente vaut mise en demeure de régulariser sous huitaine.\n"
        "À défaut, nous serons contraints d'engager les démarches de recouvrement."
    ),
    "revision_loyer": (
        "Bonjour {{tenant_name}},\n\n"
        "Nous vous informons que votre loyer hors charges est révisé : {{old_amount}} → {{new_amount}}, "
        "à compter du {{effective_date}}.\n"
        "Le détail figure dans votre espace locataire et sur votre prochain avis d'échéance."
    ),
    "revision_charges": (
        "Bonjour {{tenant_name}},\n\n"
        "Nous vous informons que vos provisions mensuelles pour charges sont révisées : "
        "{{old_amount}} → {{new_amount}}, à compter du {{effective_date}}.\n"
        "Cette régularisation sera prise en compte sur vos prochains avis d'échéance."
    ),
    "taxe_om": (
        "Bonjour {{tenant_name}},\n\n"
        "Conformément au bail, la taxe d'enlèvement des ordures ménagères {{year}} d'un montant de "
        "{{amount}} vous est refacturée.\n"
        "Le décompte détaillé est joint à cet e-mail."
    ),
    "rapport_mensuel": (
        "Bonjour,\n\n"
        "Voici la synthèse de votre gestion locative pour {{period}} :\n\n"
        "{{stats}}\n"
        "Bonne journée."
    ),
    # Candidature (placeholders : {{candidate_name}} {{property_ref}} {{when}} {{doc_list}}).
    "candidature_accuse": (
        "Bonjour {{candidate_name}},\n\n"
        "Nous vous confirmons que votre demande de logement a bien été prise en compte. "
        "Notre équipe étudie votre dossier et reviendra vers vous rapidement."
    ),
    "candidature_pieces": (
        "Bonjour {{candidate_name}},\n\n"
        "Pour étudier votre dossier de location, merci de nous transmettre les pièces "
        "listées ci-dessous via le lien sécurisé."
    ),
    "candidature_visite": (
        "Bonjour {{candidate_name}},\n\n"
        "Votre dossier a retenu notre attention pour le logement ci-dessous. Nous vous "
        "proposons de réserver un créneau de visite. D'autres candidats sont également "
        "conviés : les créneaux sont attribués dans l'ordre des réservations."
    ),
    "candidature_relance_visite": (
        "Bonjour {{candidate_name}},\n\n"
        "Petit rappel : votre visite est prévue le {{when}}. En cas d'empêchement, "
        "répondez à cet e-mail ou recontactez votre gestionnaire."
    ),
    "candidature_acceptation": (
        "Bonjour {{candidate_name}},\n\n"
        "Nous avons le plaisir de vous informer que votre dossier est accepté pour le "
        "logement ci-dessous. Félicitations !"
    ),
    "candidature_refus": (
        "Bonjour {{candidate_name}},\n\n"
        "Nous vous remercions de l'intérêt porté à ce logement. Après étude attentive des "
        "candidatures reçues, nous sommes au regret de vous informer que votre dossier n'a "
        "pas été retenu cette fois-ci. Nous conservons vos coordonnées et vous souhaitons "
        "une pleine réussite dans vos démarches."
    ),
}


def _body_to_html(text: str | None) -> str:
    """Convertit un corps (texte simple éditable) en HTML pour l'e-mail."""
    if not text:
        return ""
    return "<div>" + text.replace("\n", "<br>") + "</div>"


def render_rule_body(template: str | None, ctx: dict) -> str | None:
    """Rend le corps d'une règle (placeholders + sauts de ligne → HTML)."""
    if not template or not template.strip():
        return None
    return _body_to_html(_render(template, ctx))


def render_subject(template: str | None, ctx: dict) -> str | None:
    """Rend le sujet d'une règle (placeholders)."""
    if not template or not template.strip():
        return None
    return _render(template, ctx)


async def ensure_default_rules(db: AsyncSession, gestionnaire_id) -> int:
    """Crée les règles d'automatisation par défaut manquantes pour un gestionnaire
    (idempotent : ne recrée jamais un type déjà présent). Renvoie le nb créé."""
    from app.models.automation import AutomationRule
    from app.models.user import User

    if not gestionnaire_id:
        return 0
    existing = set(
        (
            await db.execute(
                select(AutomationRule.rule_type).where(AutomationRule.created_by == gestionnaire_id)
            )
        )
        .scalars()
        .all()
    )
    # Le gestionnaire est mis en copie par défaut (son propre e-mail).
    mgr = await db.get(User, gestionnaire_id)
    cc_default = (getattr(mgr, "email", None) or "").strip() or None
    created = 0
    for rule_type, name, channel, days, signature in _DEFAULT_RULES:
        if rule_type in existing:
            continue
        db.add(
            AutomationRule(
                name=name,
                rule_type=rule_type,
                channel=channel,
                trigger_days=days,
                is_active=_default_active(rule_type),
                created_by=gestionnaire_id,
                cc_emails=cc_default,
                signature=signature,
                subject=_DEFAULT_SUBJECTS.get(rule_type),
                body_template=_DEFAULT_BODIES.get(rule_type),
            )
        )
        created += 1
    if created:
        await db.flush()
    return created


async def backfill_default_content(db: AsyncSession) -> int:
    """Au démarrage : remplit le SUJET et le CORPS par défaut (éditables) des règles
    existantes qui n'en ont pas, par type. Rend le contenu visible et modifiable
    dans l'éditeur (plus de corps « en boîte noire »). Ne touche pas un contenu
    déjà personnalisé."""
    from app.models.automation import AutomationRule

    rules = (await db.execute(select(AutomationRule))).scalars().all()
    n = 0
    for r in rules:
        changed = False
        if not (r.body_template or "").strip() and _DEFAULT_BODIES.get(r.rule_type):
            r.body_template = _DEFAULT_BODIES[r.rule_type]
            changed = True
        if not (r.subject or "").strip() and _DEFAULT_SUBJECTS.get(r.rule_type):
            r.subject = _DEFAULT_SUBJECTS[r.rule_type]
            changed = True
        if changed:
            n += 1
    if n:
        await db.flush()
    return n


async def backfill_default_rules(db: AsyncSession) -> int:
    """Au démarrage : seede les règles par défaut pour les gestionnaires qui n'ont
    AUCUNE règle (comptes créés avant la fonctionnalité). Ne touche pas ceux qui en
    ont déjà (respecte les suppressions/personnalisations)."""
    from app.core.permissions import Role
    from app.models.automation import AutomationRule
    from app.models.user import User

    mgr_roles = [Role.ADMIN.value, Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value]
    managers = (await db.execute(select(User.id).where(User.role.in_(mgr_roles)))).scalars().all()
    if not managers:
        return 0
    with_rules = set(
        (
            await db.execute(
                select(AutomationRule.created_by).where(AutomationRule.created_by.in_(managers))
            )
        )
        .scalars()
        .all()
    )
    total = 0
    for mid in managers:
        if mid in with_rules:
            continue
        total += await ensure_default_rules(db, mid)
    return total


async def backfill_rule_types(db: AsyncSession, types: list) -> int:
    """Au démarrage : ajoute les TYPES de règles donnés aux gestionnaires qui ne les
    ont pas encore (sans recréer d'autres règles supprimées). Sert à introduire de
    NOUVEAUX types (révisions, taxe OM, rapport mensuel) sur les comptes existants."""
    from app.core.permissions import Role
    from app.models.automation import AutomationRule
    from app.models.user import User

    mgr_roles = [Role.ADMIN.value, Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value]
    managers = (await db.execute(select(User.id).where(User.role.in_(mgr_roles)))).scalars().all()
    if not managers:
        return 0
    existing = {
        (row[0], row[1])
        for row in (
            await db.execute(
                select(AutomationRule.created_by, AutomationRule.rule_type).where(
                    AutomationRule.created_by.in_(managers),
                    AutomationRule.rule_type.in_(types),
                )
            )
        ).all()
    }
    by_type = {rt: (name, channel, days, sig) for (rt, name, channel, days, sig) in _DEFAULT_RULES}
    total = 0
    for mid in managers:
        for rt in types:
            if (mid, rt) in existing or rt not in by_type:
                continue
            name, channel, days, sig = by_type[rt]
            db.add(
                AutomationRule(
                    name=name,
                    rule_type=rt,
                    channel=channel,
                    trigger_days=days,
                    is_active=_default_active(rt),
                    created_by=mid,
                    signature=sig,
                    subject=_DEFAULT_SUBJECTS.get(rt),
                    body_template=_DEFAULT_BODIES.get(rt),
                )
            )
            total += 1
    if total:
        await db.flush()
    return total


# ── Avis d'échéance ───────────────────────────────────────────────────────────


async def _send_avis(db, rule, avis, today: date) -> bool:
    from app.models.avis_echeance import AvisEcheanceStatus
    from app.models.tenant import Tenant

    dedup = f"avis:{avis.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, avis.tenant_id)
    if tenant is None:
        return False

    period = avis.period_range_label or avis.period_label
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": period,
        "amount": f"{float(avis.amount_total or 0):.2f} €",
        "due_date": avis.due_date.strftime("%d/%m/%Y") if avis.due_date else "",
    }
    _subj_t, _body_t, _sms_t = await _msg_templates(db, rule, getattr(tenant, "language", "fr"))
    subject = _render(_subj_t, ctx) or f"Avis d'échéance : {period}"
    sms_text = _render(_sms_t, ctx) or (
        f"Le Comptoir Immo : votre avis d'échéance {period} "
        f"({ctx['amount']}) est disponible. Échéance le {ctx['due_date']}."
    )
    # Canal piloté par les interrupteurs Automatisation (send_email / send_sms).
    _do_email = bool(getattr(rule, "send_email", True))
    _do_sms = bool(getattr(rule, "send_sms", False))
    channel = (
        "email_sms"
        if (_do_email and _do_sms)
        else "email"
        if _do_email
        else "sms"
        if _do_sms
        else "none"
    )
    cc = await _cc_with_manager(db, rule)

    any_sent = False
    last_err = None
    # E-mail (PDF joint)
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.services import mail_signature
            from app.services.email_service import send_avis_echeance
            from app.services.pdf_service import AvisEcheancePDFService

            sig_html, logo, logo_sub = await mail_signature.build_for_manager(
                db, rule.created_by, _signature_for(rule.rule_type)
            )
            pdf = await AvisEcheancePDFService.generate(db, avis)
            ok = await send_avis_echeance(
                to=tenant.email,
                tenant_name=tenant.full_name or tenant.email,
                period_label=period,
                amount_total=float(avis.amount_total or 0),
                due_date=ctx["due_date"],
                pdf_bytes=pdf,
                cc=cc,
                subject=subject,
                signature_html=sig_html,
                inline_logo=logo,
                inline_logo_subtype=logo_sub,
                body_html=render_rule_body(rule.body_template, ctx),
            )
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] avis email échec avis=%s: %r", avis.id, exc)
    # SMS
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms

            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] avis sms échec avis=%s: %r", avis.id, exc)

    if any_sent:
        if avis.status != AvisEcheanceStatus.ACQUITTE:
            avis.status = AvisEcheanceStatus.ENVOYE
            if not avis.sent_at:
                # Colonne avis.sent_at = TIMESTAMP sans fuseau → datetime naïf.
                avis.sent_at = datetime.utcnow()
        await _log(
            db,
            rule=rule,
            tenant_id=avis.tenant_id,
            lease_id=avis.lease_id,
            channel=channel,
            recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
            subject=subject,
            body=sms_text,
            status="sent",
            dedup_key=dedup,
        )
    elif last_err is not None:
        await _log(
            db,
            rule=rule,
            tenant_id=avis.tenant_id,
            lease_id=avis.lease_id,
            channel=channel,
            recipient=getattr(tenant, "email", None),
            subject=subject,
            body=sms_text,
            status="error",
            dedup_key=dedup,
            error=last_err,
        )
    return any_sent


async def _run_avis_rule(db, rule, today: date) -> int:
    from app.models.avis_echeance import AvisEcheance, AvisEcheanceStatus

    lease_ids = await _manager_lease_ids(db, rule.created_by)
    if not lease_ids:
        return 0
    horizon = today - timedelta(days=60)
    avis_list = (
        (
            await db.execute(
                select(AvisEcheance).where(
                    AvisEcheance.lease_id.in_(lease_ids),
                    AvisEcheance.kind == "loyer",
                    AvisEcheance.status != AvisEcheanceStatus.ACQUITTE,
                    AvisEcheance.due_date >= horizon,
                )
            )
        )
        .scalars()
        .all()
    )
    sent = 0
    for avis in avis_list:
        # Envoyer dès que l'on est à trigger_days (ou moins) de l'échéance.
        if avis.due_date and (avis.due_date - timedelta(days=int(rule.trigger_days or 0))) <= today:
            if await _send_avis(db, rule, avis, today):
                sent += 1
    return sent


# ── Rappels / relances d'impayé ───────────────────────────────────────────────


async def _send_reminder(db, rule, payment, today: date) -> bool:
    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    dedup = f"{rule.rule_type}:{payment.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, payment.tenant_id)
    if tenant is None:
        return False
    lease = await db.get(Lease, payment.lease_id)
    prop = await db.get(Property, lease.property_id) if lease else None

    label = _REMINDER_LABELS.get(rule.rule_type, "Relance")
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": payment.period_label,
        "amount": f"{float(payment.amount_due or 0):.2f} €",
        "balance": f"{float(payment.balance):.2f} €",
        "due_date": payment.due_date.strftime("%d/%m/%Y") if payment.due_date else "",
        "property_name": (prop.name if prop else ""),
    }
    _subj_t, _body_t, _sms_t = await _msg_templates(db, rule, getattr(tenant, "language", "fr"))
    subject = _render(_subj_t, ctx) or f"{label} : loyer {ctx['period']}"
    default_body = (
        f"<p>Bonjour {ctx['tenant_name']},</p>"
        f"<p>Sauf erreur de notre part, le loyer de la période "
        f"<strong>{ctx['period']}</strong> reste impayé (solde dû : "
        f"<strong>{ctx['balance']}</strong>).</p>"
        f"<p>Merci de régulariser dans les meilleurs délais.</p>"
    )
    body_html = render_rule_body(_body_t, ctx) or default_body
    sms_text = (_render(_sms_t, ctx) if _sms_t else None) or (
        f"Le Comptoir Immo : {label.lower()}, loyer {ctx['period']} impaye "
        f"(solde {ctx['balance']}). Merci de regulariser."
    )
    # Canal piloté par les interrupteurs Automatisation (send_email / send_sms).
    _do_email = bool(getattr(rule, "send_email", True))
    _do_sms = bool(getattr(rule, "send_sms", False))
    channel = (
        "email_sms"
        if (_do_email and _do_sms)
        else "email"
        if _do_email
        else "sms"
        if _do_sms
        else "none"
    )
    cc = await _cc_with_manager(db, rule)
    from app.services import mail_signature

    sig_html, logo, logo_sub = await mail_signature.build_for_manager(
        db, rule.created_by, _signature_for(rule.rule_type)
    )

    any_sent = False
    last_err = None
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.services.email_service import send_email

            # Lettre de relance jointe : génération à la volée (modèle du gestionnaire
            # sinon repli .j2), comme l'envoi manuel. Fail-soft : si la génération
            # échoue, l'e-mail part quand même sans pièce jointe.
            pdf_bytes = pdf_name = None
            try:
                from app.services.payment_service import PaymentService
                from app.services.pdf_service import build_relance_pdf, relance_filename

                _full = await PaymentService.get_by_id(db, payment.id, load_relations=True)
                pdf_bytes = await build_relance_pdf(db, _full)
                pdf_name = relance_filename(_full)
            except Exception as pexc:  # noqa: BLE001
                logger.warning(
                    "[automation] PDF relance indisponible payment=%s: %r", payment.id, pexc
                )
            ok = await send_email(
                to=tenant.email,
                subject=subject,
                html_body=body_html + sig_html,
                attachment_bytes=pdf_bytes,
                attachment_filename=pdf_name,
                cc=cc,
                inline_logo=logo,
                inline_logo_subtype=logo_sub,
            )
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] relance email échec payment=%s: %r", payment.id, exc)
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms

            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("[automation] relance sms échec payment=%s: %r", payment.id, exc)

    if any_sent:
        await _log(
            db,
            rule=rule,
            tenant_id=payment.tenant_id,
            lease_id=payment.lease_id,
            channel=channel,
            recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
            subject=subject,
            body=sms_text,
            status="sent",
            dedup_key=dedup,
        )
    elif last_err is not None:
        await _log(
            db,
            rule=rule,
            tenant_id=payment.tenant_id,
            lease_id=payment.lease_id,
            channel=channel,
            recipient=getattr(tenant, "email", None),
            subject=subject,
            body=sms_text,
            status="error",
            dedup_key=dedup,
            error=last_err,
        )
    return any_sent


async def _run_reminder_rule(db, rule, today: date) -> int:
    from app.models.payment import Payment, PaymentStatus

    lease_ids = await _manager_lease_ids(db, rule.created_by)
    if not lease_ids:
        return 0
    horizon = today - timedelta(days=120)
    pays = (
        (
            await db.execute(
                select(Payment).where(
                    Payment.lease_id.in_(lease_ids),
                    Payment.status.in_(
                        [PaymentStatus.PENDING, PaymentStatus.PARTIAL, PaymentStatus.LATE]
                    ),
                    Payment.due_date >= horizon,
                )
            )
        )
        .scalars()
        .all()
    )
    sent = 0
    delay = int(rule.trigger_days or 0)
    for p in pays:
        if float(p.balance) <= 0.005:
            continue
        if p.due_date and (p.due_date + timedelta(days=delay)) <= today:
            if await _send_reminder(db, rule, p, today):
                sent += 1
    return sent


# ── Quittance (événementiel : déclenché par le paiement) ──────────────────────


async def send_quittance_for_payment(db: AsyncSession, payment) -> bool:
    """Envoie la quittance d'un mois soldé, SI une règle « quittance » active existe
    pour le gestionnaire du bail. Toujours marque la quittance générée (consultable).
    Renvoie True si un envoi a eu lieu."""
    from app.models.automation import AutomationRule
    from app.models.lease import Lease
    from app.models.tenant import Tenant

    if not getattr(payment, "quittance_generated_at", None):
        payment.quittance_generated_at = datetime.now(UTC)
    if getattr(payment, "quittance_sent_at", None):
        return False

    lease = await db.get(Lease, payment.lease_id)
    manager_id = getattr(lease, "created_by", None) if lease else None
    if not manager_id:
        return False
    rule = (
        await db.execute(
            select(AutomationRule)
            .where(
                AutomationRule.created_by == manager_id,
                AutomationRule.rule_type == "quittance",
                AutomationRule.is_active.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if rule is None or not bool(getattr(rule, "auto_generate", True)):
        return False  # pas de règle active / type non automatisé → pas d'envoi auto

    dedup = f"quittance:{payment.id}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    tenant = await db.get(Tenant, payment.tenant_id)
    if tenant is None:
        return False

    amount = float(payment.amount_paid or 0) + float(getattr(payment, "amount_on_plan", 0) or 0)
    ctx = {
        "tenant_name": tenant.full_name or "",
        "period": payment.period_label,
        "amount": f"{amount:.2f} €",
    }
    _subj_t, _body_t, _sms_t = await _msg_templates(db, rule, getattr(tenant, "language", "fr"))
    subject = _render(_subj_t, ctx) or f"Quittance de loyer : {ctx['period']}"
    sms_text = _render(_sms_t, ctx) or (
        f"Le Comptoir Immo : votre quittance {ctx['period']} ({ctx['amount']}) est disponible."
    )
    # Canal piloté par les interrupteurs Automatisation (send_email / send_sms).
    _do_email = bool(getattr(rule, "send_email", True))
    _do_sms = bool(getattr(rule, "send_sms", False))
    channel = (
        "email_sms"
        if (_do_email and _do_sms)
        else "email"
        if _do_email
        else "sms"
        if _do_sms
        else "none"
    )
    cc = await _cc_with_manager(db, rule)
    from app.services import mail_signature

    sig_html, logo, logo_sub = await mail_signature.build_for_manager(
        db, manager_id, _signature_for(rule.rule_type)
    )

    any_sent = False
    if channel in ("email", "email_sms") and getattr(tenant, "email", None):
        try:
            from app.api.v1.payments import build_quittance_pdf
            from app.services.email_service import send_quittance as _send_q

            pdf, _fn = await build_quittance_pdf(db, payment)
            ok = await _send_q(
                to=tenant.email,
                tenant_name=tenant.full_name or "",
                period_label=ctx["period"],
                amount=amount,
                pdf_bytes=pdf,
                cc=cc,
                subject=subject,
                signature_html=sig_html,
                inline_logo=logo,
                inline_logo_subtype=logo_sub,
                body_html=render_rule_body(rule.body_template, ctx),
            )
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            logger.warning("[automation] quittance email échec payment=%s: %r", payment.id, exc)
    if channel in ("sms", "email_sms") and getattr(tenant, "phone", None):
        try:
            from app.services.sms_service import send_sms

            ok = await send_sms(tenant.phone, sms_text)
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            logger.warning("[automation] quittance sms échec payment=%s: %r", payment.id, exc)

    if any_sent:
        payment.quittance_sent_at = datetime.now(UTC)
        await _log(
            db,
            rule=rule,
            tenant_id=payment.tenant_id,
            lease_id=payment.lease_id,
            channel=channel,
            recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
            subject=subject,
            body=sms_text,
            status="sent",
            dedup_key=dedup,
        )
    return any_sent


# ── Événementiels : révision loyer/charges, taxe ordures ménagères ───────────


async def _active_rule(db, manager_id, rule_type):
    from app.models.automation import AutomationRule

    if not manager_id:
        return None
    return (
        await db.execute(
            select(AutomationRule)
            .where(
                AutomationRule.created_by == manager_id,
                AutomationRule.rule_type == rule_type,
                AutomationRule.is_active.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def _send_event_to_tenant(
    db, lease, *, rule_type, ctx_extra, dedup_suffix, pdf_bytes=None, pdf_name=None
) -> bool:
    """Envoi e-mail au locataire pour un événement (révision, TEOM), si la règle
    correspondante du gestionnaire est active. Sans boîte noire (rule = source)."""
    from app.models.tenant import Tenant

    manager_id = getattr(lease, "created_by", None)
    rule = await _active_rule(db, manager_id, rule_type)
    if rule is None or not bool(getattr(rule, "auto_generate", True)):
        return False  # type non automatisé → géré au clic
    tenant = await db.get(Tenant, getattr(lease, "tenant_id", None))
    if tenant is None:
        return False
    # Canaux pilotés par les interrupteurs Automatisation de la règle.
    do_email = bool(getattr(rule, "send_email", True)) and bool(getattr(tenant, "email", None))
    do_sms = bool(getattr(rule, "send_sms", False)) and bool(getattr(tenant, "phone", None))
    if not (do_email or do_sms):
        return False
    dedup = f"{rule_type}:{lease.id}:{dedup_suffix}:{rule.id}"
    if await _already_sent(db, dedup):
        return False
    # Nom du bien via une requête explicite : `lease.parent_property` est une
    # relation lazy → son accès déclencherait un lazy-load interdit en async.
    prop = None
    if getattr(lease, "property_id", None):
        from app.models.property import Property

        prop = await db.get(Property, lease.property_id)
    ctx = {
        "tenant_name": tenant.full_name or "",
        "property_name": getattr(prop, "name", "") or "",
        **ctx_extra,
    }
    _subj_t, _body_t, _sms_t = await _msg_templates(db, rule, getattr(tenant, "language", "fr"))
    subject = render_subject(_subj_t, ctx) or (_DEFAULT_SUBJECTS.get(rule_type) or "")
    body_html = render_rule_body(_body_t, ctx) or _body_to_html(
        _render(_DEFAULT_BODIES.get(rule_type), ctx)
    )
    any_sent = False
    if do_email:
        from app.services import mail_signature
        from app.services.email_service import send_email

        sig_html, logo, logo_sub = await mail_signature.build_for_manager(
            db, manager_id, _signature_for(rule.rule_type)
        )
        ok = await send_email(
            to=tenant.email,
            subject=subject,
            html_body=body_html + (sig_html or ""),
            cc=await _cc_with_manager(db, rule),
            inline_logo=logo,
            inline_logo_subtype=logo_sub,
            attachment_bytes=pdf_bytes,
            attachment_filename=pdf_name,
        )
        any_sent = any_sent or ok
    if do_sms:
        try:
            from app.services.sms_service import send_sms

            ok = await send_sms(tenant.phone, (render_subject(_sms_t, ctx) or subject))
            any_sent = any_sent or ok
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[automation] SMS événement %s échec lease=%s: %r", rule_type, lease.id, exc
            )
    if any_sent:
        await _log(
            db,
            rule=rule,
            tenant_id=tenant.id,
            lease_id=lease.id,
            channel=("email_sms" if (do_email and do_sms) else "email" if do_email else "sms"),
            recipient=getattr(tenant, "email", None) or getattr(tenant, "phone", None),
            subject=subject,
            body=body_html,
            status="sent",
            dedup_key=dedup,
        )
    return any_sent


async def send_revision_email(
    db, lease, *, kind, old_amount, new_amount, effective_date, pdf_bytes=None, pdf_name=None
) -> bool:
    """Notifie le locataire d'une révision de loyer ('rent') ou de charges ('charges').
    PDF optionnel joint (avis IRL pour le loyer, décompte de régularisation pour les charges)."""
    eff = (
        effective_date.strftime("%d/%m/%Y")
        if hasattr(effective_date, "strftime")
        else str(effective_date)
    )
    return await _send_event_to_tenant(
        db,
        lease,
        rule_type=("revision_loyer" if kind == "rent" else "revision_charges"),
        ctx_extra={
            "old_amount": f"{float(old_amount):.2f} €",
            "new_amount": f"{float(new_amount):.2f} €",
            "effective_date": eff,
        },
        dedup_suffix=eff,
        pdf_bytes=pdf_bytes,
        pdf_name=pdf_name,
    )


async def send_teom_email(db, lease, *, year, amount, pdf_bytes=None) -> bool:
    """Notifie le locataire de la taxe d'ordures ménagères à payer (règle 'taxe_om')."""
    from app.utils.filename import simple_doc_filename

    return await _send_event_to_tenant(
        db,
        lease,
        rule_type="taxe_om",
        ctx_extra={"year": str(year), "amount": f"{float(amount):.2f} €"},
        dedup_suffix=str(year),
        pdf_bytes=pdf_bytes,
        pdf_name=(simple_doc_filename("taxe-ordures", year) if pdf_bytes else None),
    )


# ── Rapport mensuel de gestion (planifié, jour = trigger_days) ────────────────

_MONTHS_FR = [
    "",
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


async def _manager_stats_vars(db, manager_id, year: int, month: int) -> dict:
    """Statistiques du mois (chaînes formatées) : source unique pour le corps de
    l'e-mail ET le PDF « Rapport de gestion » de l'atelier de documents."""
    v = {
        "period": f"{_MONTHS_FR[month]} {year}",
        "stat_due": "—",
        "stat_paid": "—",
        "stat_taux": "—",
        "stat_unpaid": "—",
        "stat_biens": "—",
        "stat_actifs": "—",
        "stat_occ": "—",
        "stat_entrees": "—",
        "stat_sorties": "—",
        "stat_demarches": "—",
        "stat_signalements": "—",
    }
    lease_ids = await _manager_lease_ids(db, manager_id)
    try:
        from app.models.payment import Payment

        pays = []
        if lease_ids:
            pays = (
                (
                    await db.execute(
                        select(Payment).where(
                            Payment.lease_id.in_(lease_ids),
                            Payment.period_year == year,
                            Payment.period_month == month,
                        )
                    )
                )
                .scalars()
                .all()
            )
        due = sum(float(p.amount_due or 0) for p in pays)
        paid = sum(float(p.amount_paid or 0) for p in pays)
        unpaid = sum(
            float(getattr(p, "balance", 0) or 0)
            for p in pays
            if p.status in ("pending", "partial", "late")
        )
        taux = (paid / due * 100) if due > 0 else 0
        v.update(
            stat_due=f"{due:.2f} €",
            stat_paid=f"{paid:.2f} €",
            stat_taux=f"{taux:.0f} %",
            stat_unpaid=f"{unpaid:.2f} €",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[rapport] stats encaissements échec: %r", exc)
    try:
        from app.models.lease import Lease

        leases = (
            (await db.execute(select(Lease).where(Lease.created_by == manager_id))).scalars().all()
        )
        actifs = [l for l in leases if l.is_active]
        biens = len({l.property_id for l in leases})
        entrees = sum(
            1
            for l in leases
            if l.start_date and l.start_date.year == year and l.start_date.month == month
        )
        sorties = sum(
            1
            for l in leases
            if getattr(l, "end_date", None)
            and l.end_date.year == year
            and l.end_date.month == month
        )
        occ = (len(actifs) / biens * 100) if biens else 0
        v.update(
            stat_biens=str(biens),
            stat_actifs=str(len(actifs)),
            stat_occ=f"{occ:.0f} %",
            stat_entrees=str(entrees),
            stat_sorties=str(sorties),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[rapport] stats parc échec: %r", exc)
    try:
        from app.models.signalement import Signalement
        from app.models.ticket import Ticket

        t_open = s_open = 0
        if lease_ids:
            t_open = len(
                (
                    await db.execute(
                        select(Ticket.id).where(
                            Ticket.lease_id.in_(lease_ids),
                            Ticket.status.in_(("open", "in_progress", "pending_closure")),
                        )
                    )
                )
                .scalars()
                .all()
            )
            s_open = len(
                (
                    await db.execute(
                        select(Signalement.id).where(
                            Signalement.lease_id.in_(lease_ids),
                            Signalement.status.in_(("nouveau", "en_cours")),
                        )
                    )
                )
                .scalars()
                .all()
            )
        v.update(stat_demarches=str(t_open), stat_signalements=str(s_open))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[rapport] stats demandes échec: %r", exc)
    return v


async def _compute_manager_stats(db, manager_id, year: int, month: int) -> str:
    """Synthèse textuelle du mois (corps de l'e-mail), dérivée des mêmes stats."""
    v = await _manager_stats_vars(db, manager_id, year, month)
    return "\n".join(
        [
            f"• Loyers encaissés : {v['stat_paid']} sur {v['stat_due']} appelés (recouvrement {v['stat_taux']})",
            f"• Impayés du mois : {v['stat_unpaid']}",
            f"• Parc : {v['stat_biens']} bien(s), {v['stat_actifs']} bail/baux actif(s) (occupation {v['stat_occ']})",
            f"• Mouvements : {v['stat_entrees']} entrée(s), {v['stat_sorties']} sortie(s)",
            f"• Demandes en cours : {v['stat_demarches']} démarche(s), {v['stat_signalements']} signalement(s)",
        ]
    )


async def _run_rapport_mensuel(db, rule, today: date) -> int:
    """Envoie le rapport mensuel si `today.day == rule.trigger_days` (1 fois/mois),
    sur le mois écoulé, au gestionnaire (et en copie aux adresses CC de la règle)."""
    from datetime import timedelta

    from app.models.user import User

    if int(rule.trigger_days or 1) != today.day:
        return 0
    if not bool(getattr(rule, "send_email", True)):
        return 0  # rapport = e-mail au gestionnaire ; pas d'e-mail → rien à faire
    last_prev = today.replace(day=1) - timedelta(days=1)
    year, month = last_prev.year, last_prev.month
    manager_id = rule.created_by
    dedup = f"rapport_mensuel:{manager_id}:{year}-{month:02d}"
    if await _already_sent(db, dedup):
        return 0
    # Destinataire principal = le gestionnaire ; le champ CC sert de copies.
    mgr = await db.get(User, manager_id)
    recipient = getattr(mgr, "email", None)
    if not recipient:
        return 0
    period = f"{_MONTHS_FR[month]} {year}"
    ctx = {"period": period, "stats": await _compute_manager_stats(db, manager_id, year, month)}
    subject = render_subject(rule.subject, ctx) or f"Votre rapport de gestion : {period}"
    body_html = render_rule_body(rule.body_template, ctx) or _body_to_html(
        _render(_DEFAULT_BODIES["rapport_mensuel"], ctx)
    )
    from app.services import mail_signature
    from app.services.email_service import send_email

    sig_html, logo, logo_sub = await mail_signature.build_for_manager(
        db, manager_id, _signature_for(rule.rule_type)
    )
    # Rapport joint en PDF via le modèle « Rapport de gestion » de l'atelier de documents
    # (éditable dans les ateliers de modèles). Fail-soft.
    pdf_bytes = pdf_name = None
    try:
        from app.services.document_blocks_pdf_service import RapportGestionPDFService
        from app.utils.filename import simple_doc_filename

        pdf_bytes = await RapportGestionPDFService.generate(db, manager_id, year, month)
        pdf_name = simple_doc_filename("rapport-gestion", year, f"{month:02d}")
    except Exception as pexc:  # noqa: BLE001
        logger.warning("[automation] PDF rapport mensuel indisponible mgr=%s: %r", manager_id, pexc)
    # CC = adresses de la règle MAIS jamais le destinataire principal (le rapport
    # part déjà « To » au gestionnaire → éviter un doublon To == Cc).
    cc_rapport = (
        ", ".join(
            p
            for p in [s.strip() for s in (_rule_cc(rule) or "").split(",")]
            if p and p.lower() != (recipient or "").lower()
        )
        or None
    )
    ok = await send_email(
        to=recipient,
        subject=subject,
        html_body=body_html + (sig_html or ""),
        cc=cc_rapport,
        inline_logo=logo,
        inline_logo_subtype=logo_sub,
        attachment_bytes=pdf_bytes,
        attachment_filename=pdf_name,
    )
    if ok:
        await _log(
            db,
            rule=rule,
            tenant_id=None,
            lease_id=None,
            channel="email",
            recipient=recipient,
            subject=subject,
            body=body_html,
            status="sent",
            dedup_key=dedup,
        )
        return 1
    return 0


# ── Boucle principale (planifiée quotidiennement) ─────────────────────────────


async def run_all(
    db: AsyncSession, today: date | None = None, manager_id=None, only_rule_id=None, now=None
) -> dict:
    """Exécute les règles actives (hors quittance = événementiel, et hors
    communication groupée = manuelle). Filtres : ``manager_id`` (un gestionnaire),
    ``only_rule_id`` (une seule règle, pour « Exécuter maintenant »), ``now``
    (planificateur : ne traite que les règles dont l'heure hh:mm est atteinte ce
    jour et qui n'ont pas déjà tourné aujourd'hui). Renvoie {rule_type: count}."""
    from datetime import datetime

    from app.models.automation import AutomationRule

    today = today or date.today()
    q = select(AutomationRule).where(AutomationRule.is_active.is_(True))
    if manager_id is not None:
        q = q.where(AutomationRule.created_by == manager_id)
    if only_rule_id is not None:
        q = q.where(AutomationRule.id == only_rule_id)
    rules = (await db.execute(q)).scalars().all()
    stamp = now or datetime.now(UTC)
    summary: dict = {}
    for rule in rules:
        if not rule.created_by:
            continue
        # Interrupteur maître « Générer » : si off, ce type n'est pas automatisé
        # (génération manuelle au clic dans les écrans dédiés).
        if not bool(getattr(rule, "auto_generate", True)):
            continue
        # Planificateur : l'heure hh:mm doit être atteinte aujourd'hui ET la règle
        # ne doit pas avoir déjà tourné ce jour (rattrapage robuste, 1×/jour).
        if now is not None:
            sched = int(rule.run_hour or 0) * 60 + int(getattr(rule, "run_minute", 0) or 0)
            if (now.hour * 60 + now.minute) < sched:
                continue
            lr = rule.last_run_at
            if lr is not None:
                lr_local = lr.astimezone(now.tzinfo) if (now.tzinfo and lr.tzinfo) else lr
                if lr_local.date() == now.date():
                    continue
        try:
            if rule.rule_type == "avis_echeance":
                n = await _run_avis_rule(db, rule, today)
            elif rule.rule_type in _REMINDER_TYPES:
                n = await _run_reminder_rule(db, rule, today)
            elif rule.rule_type == "rapport_mensuel":
                n = await _run_rapport_mensuel(db, rule, today)
            else:
                continue  # quittance / révisions / taxe_om = événementiels ; communication_groupee = manuel
            rule.last_run_at = stamp
            if n:
                summary[rule.rule_type] = summary.get(rule.rule_type, 0) + n
        except Exception as exc:  # noqa: BLE001 : une règle ne bloque pas les autres
            logger.error("[automation] règle %s (%s) échec: %r", rule.id, rule.rule_type, exc)
    return summary
