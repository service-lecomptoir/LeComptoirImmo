# -*- coding: utf-8 -*-
"""Modèles de courrier par défaut, multilingues (FR/EN/pt-BR/ht/srn).

Seedés pour chaque gestionnaire (un modèle « Standard » sélectionné par type), et
réutilisés comme repli par l'assistance IA. Contenu volontairement court, avec des
variables {{...}} fournies par le moteur selon le type.
"""
from typing import Dict, Any

# Variables disponibles par type (pour info / assistance IA).
TYPE_PLACEHOLDERS: Dict[str, str] = {
    "avis_echeance": "{{tenant_name}} {{period}} {{amount}} {{due_date}} {{property_name}}",
    "quittance": "{{tenant_name}} {{period}} {{amount}} {{property_name}}",
    "rappel_impaye": "{{tenant_name}} {{period}} {{balance}} {{due_date}} {{property_name}}",
    "relance_1": "{{tenant_name}} {{period}} {{balance}} {{due_date}} {{property_name}}",
    "relance_2": "{{tenant_name}} {{period}} {{balance}} {{due_date}} {{property_name}}",
    "revision_loyer": "{{tenant_name}} {{old_amount}} {{new_amount}} {{effective_date}} {{property_name}}",
    "revision_charges": "{{tenant_name}} {{old_amount}} {{new_amount}} {{effective_date}} {{property_name}}",
    "taxe_om": "{{tenant_name}} {{year}} {{amount}} {{property_name}}",
    "candidature_accuse": "{{candidate_name}} {{property_ref}}",
    "candidature_pieces": "{{candidate_name}} {{property_ref}}",
    "candidature_visite": "{{candidate_name}} {{property_ref}}",
    "candidature_relance_visite": "{{candidate_name}} {{property_ref}} {{when}}",
    "candidature_acceptation": "{{candidate_name}} {{property_ref}} {{property_address}}",
    "candidature_refus": "{{candidate_name}} {{property_ref}}",
}

# content[type][lang] = {subject, body, sms}
DEFAULTS: Dict[str, Dict[str, Dict[str, str]]] = {
    "avis_echeance": {
        "fr": {"subject": "Avis d'échéance : {{period}}",
               "body": "Bonjour {{tenant_name}},\n\nVotre avis d'échéance pour la période {{period}} est disponible : {{amount}}, à régler pour le {{due_date}}.\n\nLe document est joint et déposé dans votre espace locataire.",
               "sms": "Le Comptoir Immo : avis d'échéance {{period}} ({{amount}}), à régler le {{due_date}}."},
        "en": {"subject": "Rent notice: {{period}}",
               "body": "Hello {{tenant_name}},\n\nYour rent notice for {{period}} is available: {{amount}}, due on {{due_date}}.\n\nThe document is attached and filed in your tenant area.",
               "sms": "Le Comptoir Immo: rent notice {{period}} ({{amount}}), due {{due_date}}."},
        "pt-BR": {"subject": "Aviso de vencimento: {{period}}",
                  "body": "Olá {{tenant_name}},\n\nSeu aviso de vencimento referente a {{period}} está disponível: {{amount}}, a pagar até {{due_date}}.\n\nO documento está anexado e arquivado na sua área.",
                  "sms": "Le Comptoir Immo: aviso {{period}} ({{amount}}), vencimento {{due_date}}."},
        "ht": {"subject": "Avi echeyans : {{period}}",
               "body": "Bonjou {{tenant_name}},\n\nAvi echeyans ou pou peryòd {{period}} an disponib : {{amount}}, pou peye anvan {{due_date}}.\n\nDokiman an tache epi li nan espas lokatè ou.",
               "sms": "Le Comptoir Immo : avi {{period}} ({{amount}}), peye anvan {{due_date}}."},
        "srn": {"subject": "Oyti-paiman: {{period}}",
                "body": "Odi {{tenant_name}},\n\nYu oyti gi a peryode {{period}} de klaar: {{amount}}, pai fosi {{due_date}}.\n\nA dokumenti de na ini en de na yu lokate-presi.",
                "sms": "Le Comptoir Immo: oyti {{period}} ({{amount}}), pai fosi {{due_date}}."},
    },
    "quittance": {
        "fr": {"subject": "Quittance de loyer : {{period}}",
               "body": "Bonjour {{tenant_name}},\n\nNous vous remercions de votre règlement. Votre quittance pour {{period}} ({{amount}}) est jointe et disponible dans votre espace.",
               "sms": "Le Comptoir Immo : votre quittance {{period}} ({{amount}}) est disponible."},
        "en": {"subject": "Rent receipt: {{period}}",
               "body": "Hello {{tenant_name}},\n\nThank you for your payment. Your receipt for {{period}} ({{amount}}) is attached and available in your area.",
               "sms": "Le Comptoir Immo: your receipt {{period}} ({{amount}}) is available."},
        "pt-BR": {"subject": "Recibo de aluguel: {{period}}",
                  "body": "Olá {{tenant_name}},\n\nObrigado pelo pagamento. Seu recibo de {{period}} ({{amount}}) está anexado e disponível na sua área.",
                  "sms": "Le Comptoir Immo: recibo {{period}} ({{amount}}) disponível."},
        "ht": {"subject": "Resi lwaye : {{period}}",
               "body": "Bonjou {{tenant_name}},\n\nMèsi pou pèman ou. Resi ou pou {{period}} ({{amount}}) tache epi li disponib nan espas ou.",
               "sms": "Le Comptoir Immo : resi {{period}} ({{amount}}) disponib."},
        "srn": {"subject": "Oyti-resi: {{period}}",
                "body": "Odi {{tenant_name}},\n\nGran tangi gi yu paiman. A resi gi {{period}} ({{amount}}) de na ini en de na yu presi.",
                "sms": "Le Comptoir Immo: resi {{period}} ({{amount}}) de klaar."},
    },
    "rappel_impaye": {
        "fr": {"subject": "Rappel : loyer {{period}} impayé",
               "body": "Bonjour {{tenant_name}},\n\nSauf erreur de notre part, le loyer de {{period}} reste impayé (solde dû : {{balance}}). Merci de régulariser dans les meilleurs délais.",
               "sms": "Le Comptoir Immo : rappel, loyer {{period}} impayé (solde {{balance}}). Merci de régulariser."},
        "en": {"subject": "Reminder: rent {{period}} unpaid",
               "body": "Hello {{tenant_name}},\n\nUnless we are mistaken, the rent for {{period}} is still unpaid (balance due: {{balance}}). Please settle it as soon as possible.",
               "sms": "Le Comptoir Immo: reminder, rent {{period}} unpaid (balance {{balance}})."},
        "pt-BR": {"subject": "Lembrete: aluguel {{period}} em aberto",
                  "body": "Olá {{tenant_name}},\n\nSalvo engano, o aluguel de {{period}} continua em aberto (saldo devido: {{balance}}). Pedimos a regularização o quanto antes.",
                  "sms": "Le Comptoir Immo: lembrete, aluguel {{period}} em aberto (saldo {{balance}})."},
        "ht": {"subject": "Rapèl : lwaye {{period}} pa peye",
               "body": "Bonjou {{tenant_name}},\n\nSi nou pa twonpe nou, lwaye {{period}} an poko peye (rès pou peye : {{balance}}). Tanpri regle sa pi vit posib.",
               "sms": "Le Comptoir Immo : rapèl, lwaye {{period}} pa peye (rès {{balance}})."},
        "srn": {"subject": "Memre: oyti {{period}} no pai",
                "body": "Odi {{tenant_name}},\n\nEfu wi no fowtu, a oyti gi {{period}} no pai ete (a rest fu pai: {{balance}}). Grantangi pai en esi-esi.",
                "sms": "Le Comptoir Immo: memre, oyti {{period}} no pai (rest {{balance}})."},
    },
    "relance_1": {
        "fr": {"subject": "Relance : loyer {{period}} impayé",
               "body": "Bonjour {{tenant_name}},\n\nMalgré notre précédent message, le loyer de {{period}} (échéance du {{due_date}}) demeure impayé : solde dû {{balance}}. Merci de régulariser sous huitaine. La lettre de relance est jointe.",
               "sms": "Le Comptoir Immo : relance, loyer {{period}} impayé (solde {{balance}}). Régularisez sous 8 jours."},
        "en": {"subject": "Follow-up: rent {{period}} unpaid",
               "body": "Hello {{tenant_name}},\n\nDespite our previous message, the rent for {{period}} (due {{due_date}}) is still unpaid: balance {{balance}}. Please settle within eight days. The follow-up letter is attached.",
               "sms": "Le Comptoir Immo: follow-up, rent {{period}} unpaid (balance {{balance}}). Please pay within 8 days."},
        "pt-BR": {"subject": "Cobrança: aluguel {{period}} em aberto",
                  "body": "Olá {{tenant_name}},\n\nApesar da mensagem anterior, o aluguel de {{period}} (vencimento {{due_date}}) continua em aberto: saldo {{balance}}. Regularize em oito dias. A carta de cobrança está anexada.",
                  "sms": "Le Comptoir Immo: cobrança, aluguel {{period}} (saldo {{balance}}). Regularize em 8 dias."},
        "ht": {"subject": "Relans : lwaye {{period}} pa peye",
               "body": "Bonjou {{tenant_name}},\n\nMalgre mesaj nou anvan an, lwaye {{period}} (echeyans {{due_date}}) poko peye : rès {{balance}}. Tanpri regle nan uit jou. Lèt relans lan tache.",
               "sms": "Le Comptoir Immo : relans, lwaye {{period}} pa peye (rès {{balance}}). Regle nan 8 jou."},
        "srn": {"subject": "Memre-brifi: oyti {{period}} no pai",
                "body": "Odi {{tenant_name}},\n\nAla wi fosi brifi, a oyti gi {{period}} (paiman-dei {{due_date}}) no pai ete: rest {{balance}}. Grantangi pai inisei aiti dei. A memre-brifi de na ini.",
                "sms": "Le Comptoir Immo: memre, oyti {{period}} no pai (rest {{balance}}). Pai inisei 8 dei."},
    },
    "relance_2": {
        "fr": {"subject": "Mise en demeure : loyer {{period}} impayé",
               "body": "Bonjour {{tenant_name}},\n\nEn l'absence de règlement, nous vous mettons en demeure de payer le loyer de {{period}} (solde dû {{balance}}) sous huitaine. À défaut, nous engagerons les procédures de recouvrement. La mise en demeure est jointe.",
               "sms": "Le Comptoir Immo : mise en demeure, loyer {{period}} impayé (solde {{balance}}). Procédure sans règlement sous 8 jours."},
        "en": {"subject": "Formal notice: rent {{period}} unpaid",
               "body": "Hello {{tenant_name}},\n\nAs payment is still outstanding, this is a formal notice to pay the rent for {{period}} (balance {{balance}}) within eight days. Failing this, recovery proceedings will begin. The formal notice is attached.",
               "sms": "Le Comptoir Immo: formal notice, rent {{period}} unpaid (balance {{balance}}). Proceedings if unpaid within 8 days."},
        "pt-BR": {"subject": "Notificação formal: aluguel {{period}} em aberto",
                  "body": "Olá {{tenant_name}},\n\nNa falta de pagamento, notificamos formalmente para pagar o aluguel de {{period}} (saldo {{balance}}) em oito dias. Caso contrário, iniciaremos a cobrança judicial. A notificação está anexada.",
                  "sms": "Le Comptoir Immo: notificação, aluguel {{period}} (saldo {{balance}}). Cobrança se não pago em 8 dias."},
        "ht": {"subject": "Mizan demè : lwaye {{period}} pa peye",
               "body": "Bonjou {{tenant_name}},\n\nKòm pèman an pa fèt, nou mete ou an demè pou peye lwaye {{period}} (rès {{balance}}) nan uit jou. Si se pa sa, n ap kòmanse pwosedi rekouvreman. Mizan demè a tache.",
               "sms": "Le Comptoir Immo : mizan demè, lwaye {{period}} (rès {{balance}}). Pwosedi si pa peye nan 8 jou."},
        "srn": {"subject": "Ofisi-warskow: oyti {{period}} no pai",
                "body": "Odi {{tenant_name}},\n\nFu di a paiman no pai ete, wi e gi yu wan ofisi-warskow fu pai a oyti gi {{period}} (rest {{balance}}) inisei aiti dei. Efu no, wi o bigin a kragi-pisi. A warskow de na ini.",
                "sms": "Le Comptoir Immo: warskow, oyti {{period}} (rest {{balance}}). Kragi efu no pai inisei 8 dei."},
    },
    "revision_loyer": {
        "fr": {"subject": "Révision de votre loyer au {{effective_date}}",
               "body": "Bonjour {{tenant_name}},\n\nVotre loyer évolue de {{old_amount}} à {{new_amount}} à compter du {{effective_date}}. L'avis détaillé est joint et déposé dans votre espace.",
               "sms": "Le Comptoir Immo : votre loyer passe à {{new_amount}} au {{effective_date}}."},
        "en": {"subject": "Rent review effective {{effective_date}}",
               "body": "Hello {{tenant_name}},\n\nYour rent changes from {{old_amount}} to {{new_amount}} effective {{effective_date}}. The detailed notice is attached and filed in your area.",
               "sms": "Le Comptoir Immo: your rent becomes {{new_amount}} on {{effective_date}}."},
        "pt-BR": {"subject": "Reajuste do aluguel a partir de {{effective_date}}",
                  "body": "Olá {{tenant_name}},\n\nSeu aluguel passa de {{old_amount}} para {{new_amount}} a partir de {{effective_date}}. O aviso detalhado está anexado.",
                  "sms": "Le Comptoir Immo: aluguel passa a {{new_amount}} em {{effective_date}}."},
        "ht": {"subject": "Revizyon lwaye ou nan {{effective_date}}",
               "body": "Bonjou {{tenant_name}},\n\nLwaye ou pase de {{old_amount}} a {{new_amount}} apati {{effective_date}}. Avi detaye a tache epi li nan espas ou.",
               "sms": "Le Comptoir Immo : lwaye ou vin {{new_amount}} nan {{effective_date}}."},
        "srn": {"subject": "Kenki fu yu oyti fu {{effective_date}}",
                "body": "Odi {{tenant_name}},\n\nYu oyti e kenki fu {{old_amount}} go na {{new_amount}} bigin {{effective_date}}. A fini-brifi de na ini.",
                "sms": "Le Comptoir Immo: yu oyti tron {{new_amount}} na {{effective_date}}."},
    },
    "revision_charges": {
        "fr": {"subject": "Révision de vos charges au {{effective_date}}",
               "body": "Bonjour {{tenant_name}},\n\nVos provisions pour charges évoluent de {{old_amount}} à {{new_amount}} à compter du {{effective_date}}. Le décompte est joint et déposé dans votre espace.",
               "sms": "Le Comptoir Immo : vos charges passent à {{new_amount}} au {{effective_date}}."},
        "en": {"subject": "Charges review effective {{effective_date}}",
               "body": "Hello {{tenant_name}},\n\nYour charges provision changes from {{old_amount}} to {{new_amount}} effective {{effective_date}}. The statement is attached and filed in your area.",
               "sms": "Le Comptoir Immo: your charges become {{new_amount}} on {{effective_date}}."},
        "pt-BR": {"subject": "Reajuste dos encargos a partir de {{effective_date}}",
                  "body": "Olá {{tenant_name}},\n\nA provisão de encargos passa de {{old_amount}} para {{new_amount}} a partir de {{effective_date}}. O demonstrativo está anexado.",
                  "sms": "Le Comptoir Immo: encargos passam a {{new_amount}} em {{effective_date}}."},
        "ht": {"subject": "Revizyon chaj ou nan {{effective_date}}",
               "body": "Bonjou {{tenant_name}},\n\nProvizyon chaj ou pase de {{old_amount}} a {{new_amount}} apati {{effective_date}}. Dekont lan tache epi li nan espas ou.",
               "sms": "Le Comptoir Immo : chaj ou vin {{new_amount}} nan {{effective_date}}."},
        "srn": {"subject": "Kenki fu yu kostu fu {{effective_date}}",
                "body": "Odi {{tenant_name}},\n\nYu kostu-provisi e kenki fu {{old_amount}} go na {{new_amount}} bigin {{effective_date}}. A telu de na ini.",
                "sms": "Le Comptoir Immo: yu kostu tron {{new_amount}} na {{effective_date}}."},
    },
    "taxe_om": {
        "fr": {"subject": "Taxe d'ordures ménagères {{year}}",
               "body": "Bonjour {{tenant_name}},\n\nLa taxe d'enlèvement des ordures ménagères {{year}} qui vous est refacturée s'élève à {{amount}}. Le décompte est joint et déposé dans votre espace.",
               "sms": "Le Comptoir Immo : taxe ordures ménagères {{year}} : {{amount}}."},
        "en": {"subject": "Household waste tax {{year}}",
               "body": "Hello {{tenant_name}},\n\nThe household waste collection tax {{year}} re-billed to you amounts to {{amount}}. The statement is attached and filed in your area.",
               "sms": "Le Comptoir Immo: household waste tax {{year}}: {{amount}}."},
        "pt-BR": {"subject": "Taxa de lixo {{year}}",
                  "body": "Olá {{tenant_name}},\n\nA taxa de coleta de lixo {{year}} repassada a você é de {{amount}}. O demonstrativo está anexado.",
                  "sms": "Le Comptoir Immo: taxa de lixo {{year}}: {{amount}}."},
        "ht": {"subject": "Taks fatra {{year}}",
               "body": "Bonjou {{tenant_name}},\n\nTaks ranmasaj fatra {{year}} yo refaktire ba ou a se {{amount}}. Dekont lan tache epi li nan espas ou.",
               "sms": "Le Comptoir Immo : taks fatra {{year}} : {{amount}}."},
        "srn": {"subject": "Doti-belasti {{year}}",
                "body": "Odi {{tenant_name}},\n\nA doti-tyari belasti {{year}} di wi e bil baka na yu na {{amount}}. A telu de na ini.",
                "sms": "Le Comptoir Immo: doti-belasti {{year}}: {{amount}}."},
    },
}


def _fr_only(subject: str, body: str, sms: str = "") -> Dict[str, Dict[str, str]]:
    """Modèle français seul (les candidats n'ont pas de langue : repli fr)."""
    return {"fr": {"subject": subject, "body": body, "sms": sms}}


# Communications de candidature (français ; adressées au candidat, pas au locataire).
DEFAULTS.update({
    "candidature_accuse": _fr_only(
        "Votre demande de logement a bien été prise en compte",
        "Bonjour {{candidate_name}},\n\nNous vous confirmons que votre demande de logement a bien "
        "été prise en compte. Notre équipe étudie votre dossier et reviendra vers vous rapidement.",
    ),
    "candidature_pieces": _fr_only(
        "Votre dossier de location : pièces à fournir",
        "Bonjour {{candidate_name}},\n\nPour étudier votre dossier de location, merci de nous "
        "transmettre les pièces listées ci-dessous via le lien sécurisé.",
    ),
    "candidature_visite": _fr_only(
        "Confirmation de visite : bien {{property_ref}}",
        "Bonjour {{candidate_name}},\n\nVotre dossier a retenu notre attention pour le logement "
        "ci-dessous. Nous vous proposons de réserver un créneau de visite. D'autres candidats sont "
        "également conviés : les créneaux sont attribués dans l'ordre des réservations.",
    ),
    "candidature_relance_visite": _fr_only(
        "Rappel : votre visite approche (bien {{property_ref}})",
        "Bonjour {{candidate_name}},\n\nPetit rappel : votre visite est prévue le {{when}}. En cas "
        "d'empêchement, répondez à cet e-mail ou recontactez votre gestionnaire.",
    ),
    "candidature_acceptation": _fr_only(
        "Votre dossier de location est accepté",
        "Bonjour {{candidate_name}},\n\nNous avons le plaisir de vous informer que votre dossier "
        "est accepté pour le logement ci-dessous. Félicitations !",
    ),
    "candidature_refus": _fr_only(
        "Réponse à votre candidature",
        "Bonjour {{candidate_name}},\n\nNous vous remercions de l'intérêt porté à ce logement. "
        "Après étude attentive des candidatures reçues, nous sommes au regret de vous informer que "
        "votre dossier n'a pas été retenu cette fois-ci. Nous conservons vos coordonnées et vous "
        "souhaitons une pleine réussite dans vos démarches.",
    ),
})


def default_content(rule_type: str) -> Dict[str, Any]:
    """Contenu multilingue par défaut pour un type (copie)."""
    src = DEFAULTS.get(rule_type, {})
    return {lang: dict(block) for lang, block in src.items()}


async def backfill_default_message_templates(db) -> int:
    """Crée un modèle « Standard » multilingue sélectionné par (gestionnaire, type)
    s'il n'en existe aucun. Idempotent. Retourne le nombre de modèles créés."""
    from sqlalchemy import select
    from app.models.user import User
    from app.models.message_template import MessageTemplate

    created = 0
    managers = (await db.execute(select(User.id).where(User.role.in_(("gestionnaire", "gestionnaire_proprio"))))).scalars().all()
    existing = set(
        (row[0], row[1]) for row in (await db.execute(
            select(MessageTemplate.gestionnaire_id, MessageTemplate.rule_type)
        )).all()
    )
    for mid in managers:
        for rtype in DEFAULTS:
            if (mid, rtype) in existing:
                continue
            db.add(MessageTemplate(
                gestionnaire_id=mid, rule_type=rtype, name="Standard",
                content=default_content(rtype), is_selected=True, is_active=True,
            ))
            created += 1
    if created:
        await db.flush()
    return created
