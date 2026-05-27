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
) -> bool:
    """Envoie un email via SMTP. Retourne True si envoyé, False si désactivé ou erreur."""
    from app.config import get_settings
    cfg = get_settings()
    if not cfg.smtp_enabled:
        logger.debug("SMTP désactivé — email simulé vers %s: %s", to, subject)
        return False

    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = f"{cfg.SMTP_FROM_NAME} <{cfg.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text_body or _html_to_text(html_body))
        msg.add_alternative(html_body, subtype="html")

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
  <div class="header"><h1>Le Comptoir Immo — {title}</h1></div>
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
) -> bool:
    content = f"""
<p>Bonjour {tenant_name},</p>
<p>Vous trouverez ci-dessous votre avis d'échéance pour la période <strong>{period_label}</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Montant dû</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{amount_total:.2f} €</td></tr>
  <tr><td style="padding:8px;color:#6b7280">Date d'échéance</td>
      <td style="padding:8px;font-weight:600">{due_date}</td></tr>
</table>
{"<p>Le détail de votre avis est joint à cet email en PDF.</p>" if pdf_bytes else ""}
<p>Cordialement,<br>Votre gestionnaire</p>
"""
    return await send_email(
        to=to,
        subject=f"Avis d'échéance — {period_label}",
        html_body=_base_template(f"Avis d'échéance {period_label}", content),
        attachment_bytes=pdf_bytes,
        attachment_filename=f"avis-echeance-{period_label.lower().replace(' ', '-')}.pdf" if pdf_bytes else None,
    )


async def send_quittance(
    to: str,
    tenant_name: str,
    period_label: str,
    amount: float,
    pdf_bytes: Optional[bytes] = None,
) -> bool:
    content = f"""
<p>Bonjour {tenant_name},</p>
<p>Votre paiement de <strong>{amount:.2f} €</strong> pour la période <strong>{period_label}</strong> a bien été enregistré.</p>
{"<p>Votre quittance de loyer est jointe à cet email en PDF.</p>" if pdf_bytes else ""}
<p>Cordialement,<br>Votre gestionnaire</p>
"""
    return await send_email(
        to=to,
        subject=f"Quittance de loyer — {period_label}",
        html_body=_base_template(f"Quittance {period_label}", content),
        attachment_bytes=pdf_bytes,
        attachment_filename=f"quittance-{period_label.lower().replace(' ', '-')}.pdf" if pdf_bytes else None,
    )


async def send_group_message(
    to: str,
    subject: str,
    body: str,
) -> bool:
    content = f"""
<p>{body.replace(chr(10), '<br>')}</p>
"""
    return await send_email(
        to=to,
        subject=subject,
        html_body=_base_template(subject, content),
        text_body=body,
    )
