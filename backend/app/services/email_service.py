"""Service d'envoi d'emails transactionnels via SMTP (aiosmtplib)."""
import logging
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
    attachment_mime: str = "application/pdf",
    cc: Optional[str] = None,
    inline_logo: Optional[bytes] = None,
    inline_logo_subtype: str = "png",
) -> bool:
    """Envoie un email via SMTP. Retourne True si envoyé, False si désactivé ou erreur.

    ``cc`` : adresse(s) en copie (ex. le gestionnaire en copie d'un e-mail locataire).
    Ignoré si égal au destinataire principal.
    ``inline_logo`` : image (logo gestionnaire) embarquée en pièce inline et
    référençable dans le HTML via ``cid:managerlogo`` (signature des e-mails).
    """
    from app.config import get_settings
    cfg = get_settings()
    if not cfg.smtp_enabled:
        logger.debug("SMTP désactivé : email simulé vers %s: %s", to, subject)
        return False

    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = f"{cfg.SMTP_FROM_NAME} <{cfg.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        if cc and cc.strip() and cc.strip().lower() != (to or "").strip().lower():
            msg["Cc"] = cc.strip()
        msg["Subject"] = subject
        msg.set_content(text_body or _html_to_text(html_body))
        msg.add_alternative(html_body, subtype="html")

        # Logo gestionnaire en image inline (CID) attachée à la partie HTML.
        if inline_logo:
            try:
                html_part = msg.get_payload()[-1]
                html_part.add_related(
                    inline_logo, maintype="image",
                    subtype=(inline_logo_subtype or "png"), cid="managerlogo",
                )
            except Exception as _exc:  # noqa: BLE001 : le logo ne doit jamais bloquer l'envoi
                logger.warning("Logo inline non joint: %s", _exc)

        if attachment_bytes and attachment_filename:
            msg.add_attachment(
                attachment_bytes,
                maintype=attachment_mime.split("/")[0],
                subtype=attachment_mime.split("/")[1],
                filename=attachment_filename,
            )

        await aiosmtplib.send(
            msg,
            hostname=cfg.SMTP_HOST,
            port=cfg.SMTP_PORT,
            username=cfg.SMTP_USER or None,
            password=cfg.SMTP_PASSWORD or None,
            start_tls=cfg.SMTP_TLS,
        )
        logger.info("Email envoyé → %s: %s", to, subject)
        return True

    except Exception as exc:
        logger.error("Échec envoi email → %s: %s | %s", to, subject, exc)
        return False


def _html_to_text(html: str) -> str:
    """Conversion HTML → texte brut minimaliste (supprime balises)."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


def build_signature_html(service_name: Optional[str], has_logo: bool = False) -> str:
    """Bloc signature des e-mails : « Cordialement », logo gestionnaire (image
    inline via cid:managerlogo), nom du service, puis la mention d'envoi
    automatique. Utilisé par les envois pilotés par les règles d'automatisation."""
    rows = ['<p style="margin:0 0 6px">Cordialement,</p>']
    if has_logo:
        rows.append('<img src="cid:managerlogo" alt="" style="max-height:54px;margin:6px 0">')
    if service_name and service_name.strip():
        rows.append(f'<p style="margin:2px 0;font-weight:600;color:#111827">{service_name.strip()}</p>')
    rows.append('<p style="margin:12px 0 0;color:#9ca3af;font-size:12px">'
                'Cette communication a été envoyée automatiquement par le système Le Comptoir.</p>')
    return ('<div style="margin-top:20px;border-top:1px solid #e5e7eb;padding-top:12px">'
            + "".join(rows) + '</div>')


# ── Templates email ───────────────────────────────────────────────────────────

def _base_template(title: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
  .wrapper {{ max-width: 600px; margin: 30px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); }}
  .header {{ background: #1e40af; color: #fff; padding: 24px 32px; }}
  .header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  .body {{ padding: 28px 32px; }}
  .footer {{ background: #f9fafb; border-top: 1px solid #e5e7eb; padding: 16px 32px; font-size: 12px; color: #6b7280; text-align: center; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header"><h1>Le Comptoir Immo : {title}</h1></div>
  <div class="body">{content}</div>
  <div class="footer">Le Comptoir Immo · Gestion locative · Ce message est automatique, merci de ne pas y répondre.</div>
</div>
</body>
</html>
"""


async def send_avis_echeance(
    to: str,
    tenant_name: str,
    period_label: str,
    amount_total: float,
    due_date: str,
    pdf_bytes: Optional[bytes] = None,
    cc: Optional[str] = None,
    subject: Optional[str] = None,
    signature_html: Optional[str] = None,
    inline_logo: Optional[bytes] = None,
    inline_logo_subtype: str = "png",
    body_html: Optional[str] = None,
) -> bool:
    # Corps : celui de la règle (body_html, éditable) sinon corps par défaut.
    inner = body_html if body_html else f"""
<p>Bonjour {tenant_name},</p>
<p>Vous trouverez ci-dessous votre avis d'échéance pour la période <strong>{period_label}</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Montant dû</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{amount_total:.2f} €</td></tr>
  <tr><td style="padding:8px;color:#6b7280">Date d'échéance</td>
      <td style="padding:8px;font-weight:600">{due_date}</td></tr>
</table>
{"<p>Le détail de votre avis est joint à cet email en PDF.</p>" if pdf_bytes else ""}"""
    content = f"""{inner}
{signature_html or "<p>Cordialement,<br>Votre gestionnaire</p>"}
"""
    return await send_email(
        to=to,
        subject=subject or f"Avis d'échéance : {period_label}",
        html_body=_base_template(f"Avis d'échéance {period_label}", content),
        attachment_bytes=pdf_bytes,
        attachment_filename=f"avis-echeance-{period_label.lower().replace(' ', '-')}.pdf" if pdf_bytes else None,
        cc=cc, inline_logo=inline_logo, inline_logo_subtype=inline_logo_subtype,
    )


async def send_quittance(
    to: str,
    tenant_name: str,
    period_label: str,
    amount: float,
    pdf_bytes: Optional[bytes] = None,
    cc: Optional[str] = None,
    subject: Optional[str] = None,
    signature_html: Optional[str] = None,
    inline_logo: Optional[bytes] = None,
    inline_logo_subtype: str = "png",
    body_html: Optional[str] = None,
) -> bool:
    inner = body_html if body_html else f"""
<p>Bonjour {tenant_name},</p>
<p>Votre paiement de <strong>{amount:.2f} €</strong> pour la période <strong>{period_label}</strong> a bien été enregistré.</p>
{"<p>Votre quittance de loyer est jointe à cet email en PDF.</p>" if pdf_bytes else ""}"""
    content = f"""{inner}
{signature_html or "<p>Cordialement,<br>Votre gestionnaire</p>"}
"""
    return await send_email(
        to=to,
        subject=subject or f"Quittance de loyer : {period_label}",
        html_body=_base_template(f"Quittance {period_label}", content),
        attachment_bytes=pdf_bytes,
        attachment_filename=f"quittance-{period_label.lower().replace(' ', '-')}.pdf" if pdf_bytes else None,
        cc=cc, inline_logo=inline_logo, inline_logo_subtype=inline_logo_subtype,
    )


def build_credentials_email(
    *,
    login: str,
    password: str,
    full_name: Optional[str] = None,
    login_url: str = "https://immo.lecomptoir.services/login",
    product_label: str = "Le Comptoir Immo",
    plan_label: Optional[str] = None,
    reset: bool = False,
) -> tuple[str, str]:
    """Modèle d'e-mail professionnel des identifiants de connexion.

    Retourne (objet, corps_html). Réutilisable pour l'envoi initial des accès
    comme pour une réinitialisation (``reset=True``). L'objet est volontairement
    sobre (sans tiret, sans majuscules criardes ni ponctuation suspecte) pour
    limiter le classement en courrier indésirable.
    """
    greeting = f"Bonjour {full_name.strip()}," if (full_name or "").strip() else "Bonjour,"
    if reset:
        subject = f"Réinitialisation de votre mot de passe {product_label}"
        title = "Réinitialisation de votre mot de passe"
        intro = (
            f"Vous avez demandé la réinitialisation de votre mot de passe pour votre "
            f"espace <strong>{product_label}</strong>. Voici un mot de passe temporaire "
            f"pour vous reconnecter :"
        )
    else:
        subject = f"Vos accès à votre espace {product_label}"
        title = "Vos accès à votre espace"
        intro = (
            f"Votre espace <strong>{product_label}</strong> est prêt. "
            f"Voici vos identifiants de connexion :"
        )

    rows = []
    if plan_label and plan_label.strip():
        rows.append(("Formule", plan_label.strip()))
    rows.append(("Identifiant", login))
    rows.append(("Mot de passe temporaire", password))
    rows_html = "".join(
        f'<tr><td style="padding:11px 16px;border-bottom:1px solid #eef2f7;color:#64748b;'
        f'font-size:13px">{k}</td>'
        f'<td style="padding:11px 16px;border-bottom:1px solid #eef2f7;font-weight:600;'
        f'color:#0f172a;font-size:14px">{v}</td></tr>'
        for k, v in rows
    )

    content = f"""
<p style="margin:0 0 14px;font-size:15px;color:#0f172a">{greeting}</p>
<p style="margin:0 0 18px;font-size:14px;color:#334155;line-height:1.6">{intro}</p>
<table role="presentation" style="width:100%;border-collapse:collapse;border:1px solid #eef2f7;border-radius:8px;overflow:hidden;margin:0 0 24px">
{rows_html}
</table>
<div style="text-align:center;margin:0 0 24px">
  <a href="{login_url}" style="display:inline-block;background:#1e40af;color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:13px 30px;border-radius:8px">Accéder à mon espace</a>
</div>
<p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:1.6">Lien de connexion : <a href="{login_url}" style="color:#1e40af;text-decoration:none">{login_url}</a></p>
<p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:1.6">Pour votre sécurité, un nouveau mot de passe vous sera demandé lors de votre première connexion.</p>
<p style="margin:0;font-size:13px;color:#94a3b8;line-height:1.6">Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail.</p>
"""
    return subject, _base_template(title, content)


async def send_credentials(
    to: str,
    login: str,
    password: str,
    full_name: Optional[str] = None,
    login_url: str = "https://immo.lecomptoir.services/login",
    product_label: str = "Le Comptoir Immo",
    plan_label: Optional[str] = None,
    reset: bool = False,
) -> bool:
    """Envoie les identifiants de connexion (identifiant + mot de passe TEMPORAIRE).
    Le mot de passe devra être changé à la 1re connexion."""
    subject, html = build_credentials_email(
        login=login, password=password, full_name=full_name, login_url=login_url,
        product_label=product_label, plan_label=plan_label, reset=reset,
    )
    return await send_email(to=to, subject=subject, html_body=html)


async def send_revision_loyer(
    to: str,
    tenant_name: str,
    effective_date: str,
    old_rent: float,
    new_rent: Optional[float] = None,
    irl_quarter: Optional[int] = None,
    irl_year: Optional[int] = None,
) -> bool:
    """Prévient le locataire d'une révision de loyer à venir (1 mois à l'avance)."""
    if new_rent is not None:
        detail = f"""
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Loyer actuel</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{old_rent:.2f} €</td></tr>
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Nouveau loyer</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{new_rent:.2f} €</td></tr>
  <tr><td style="padding:8px;color:#6b7280">À compter du</td>
      <td style="padding:8px;font-weight:600">{effective_date}</td></tr>
</table>
<p style="color:#6b7280;font-size:13px">Révision calculée selon l'indice de référence des loyers
{f"(IRL T{irl_quarter} {irl_year})" if irl_quarter and irl_year else "(IRL)"}.</p>
"""
    else:
        detail = f"""
<p>À compter du <strong>{effective_date}</strong>, votre loyer sera révisé selon l'indice
de référence des loyers (IRL). Le nouveau montant vous sera précisé dès la publication
de l'indice applicable.</p>
"""
    content = f"""
<p>Bonjour {tenant_name},</p>
<p>Conformément à votre bail, votre loyer fera l'objet de sa révision annuelle.</p>
{detail}
<p>Cordialement,<br>Votre gestionnaire</p>
"""
    return await send_email(
        to=to,
        subject="Révision de loyer à venir",
        html_body=_base_template("Révision de loyer à venir", content),
    )


async def send_charge_regularization(
    to: str,
    tenant_name: str,
    period: str,
    provisions_total: float,
    real_total: float,
    balance: float,
    new_monthly_provision: float,
) -> bool:
    """Notifie le locataire d'une régularisation annuelle des charges."""
    if balance > 0:
        solde = (f'<tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">'
                 f'Trop-perçu remboursé</td><td style="padding:8px;border-bottom:1px solid #e5e7eb;'
                 f'font-weight:600;color:#047857">{balance:.2f} €</td></tr>')
        note = "<p>Ce trop-perçu sera déduit automatiquement de vos prochains loyers.</p>"
    elif balance < 0:
        solde = (f'<tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">'
                 f'Complément à régler</td><td style="padding:8px;border-bottom:1px solid #e5e7eb;'
                 f'font-weight:600;color:#b91c1c">{abs(balance):.2f} €</td></tr>')
        note = "<p>Un complément de charges reste à régler. Votre gestionnaire vous précisera les modalités.</p>"
    else:
        solde = ""
        note = "<p>Les provisions versées correspondent exactement aux charges réelles.</p>"
    content = f"""
<p>Bonjour {tenant_name},</p>
<p>Voici la régularisation de vos charges pour la période <strong>{period}</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Provisions versées</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{provisions_total:.2f} €</td></tr>
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Charges réelles</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{real_total:.2f} €</td></tr>
  {solde}
  <tr><td style="padding:8px;color:#6b7280">Nouvelle provision mensuelle</td>
      <td style="padding:8px;font-weight:600">{new_monthly_provision:.2f} €</td></tr>
</table>
{note}
<p>Cordialement,<br>Votre gestionnaire</p>
"""
    return await send_email(
        to=to,
        subject="Régularisation de vos charges",
        html_body=_base_template("Régularisation des charges", content),
    )


async def send_subscription_lead_notification(
    to: str,
    full_name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    message: Optional[str] = None,
) -> bool:
    """Notifie l'équipe d'une nouvelle demande de souscription (page d'accueil)."""
    def _row(label: str, value: Optional[str]) -> str:
        if not value:
            return ""
        return (
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;color:#6b7280">{label}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;font-weight:600">{value}</td></tr>'
        )

    content = f"""
<p>Une nouvelle demande de souscription vient d'être déposée depuis la page d'accueil.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  {_row("Nom", full_name)}
  {_row("Email", email)}
  {_row("Téléphone", phone)}
  {_row("Société", company)}
</table>
{f'<p style="color:#6b7280;margin:0 0 4px">Besoin exprimé :</p><p style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px">{message}</p>' if message else ''}
<p style="margin-top:16px">À traiter dans Alice → <strong>Demandes</strong>.</p>
"""
    return await send_email(
        to=to,
        subject=f"Nouvelle demande de souscription : {full_name}",
        html_body=_base_template("Nouvelle demande de souscription", content),
    )


async def send_group_message(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    signature_html: Optional[str] = None,
    inline_logo: Optional[bytes] = None,
    inline_logo_subtype: str = "png",
) -> bool:
    content = f"""
<p>{body.replace(chr(10), '<br>')}</p>
{signature_html or ""}
"""
    return await send_email(
        to=to,
        subject=subject,
        html_body=_base_template(subject, content),
        text_body=body,
        cc=cc, inline_logo=inline_logo, inline_logo_subtype=inline_logo_subtype,
    )
