"""Service d'envoi d'emails Alice via SMTP (aiosmtplib).

Réplique le pattern du service email de LeComptoirImmo : si SMTP_HOST est vide,
l'envoi est simulé (no-op) et la fonction retourne False sans erreur.
"""
import logging
import re
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

_MONTHS = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
    attachment_mime: str = "application/pdf",
) -> bool:
    """Envoie un email via SMTP. Retourne True si envoyé, False si désactivé/erreur."""
    from app.config import get_settings
    cfg = get_settings()
    if not cfg.smtp_enabled:
        logger.info("SMTP désactivé — email simulé vers %s: %s", to, subject)
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
            maintype, _, subtype = attachment_mime.partition("/")
            msg.add_attachment(
                attachment_bytes,
                maintype=maintype,
                subtype=subtype or "octet-stream",
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
    return re.sub(r"<[^>]+>", "", html).strip()


def _base_template(title: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
  .wrapper {{ max-width: 600px; margin: 30px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); }}
  .header {{ background: #4f46e5; color: #fff; padding: 24px 32px; }}
  .header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  .body {{ padding: 28px 32px; }}
  .footer {{ background: #f9fafb; border-top: 1px solid #e5e7eb; padding: 16px 32px; font-size: 12px; color: #6b7280; text-align: center; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header"><h1>Le Comptoir Immo — {title}</h1></div>
  <div class="body">{content}</div>
  <div class="footer">Le Comptoir Immo · Ce message est automatique, merci de ne pas y répondre.</div>
</div>
</body>
</html>
"""


async def send_invoice_email(
    to: str,
    client_name: str,
    period_year: int,
    period_month: int,
    amount: float,
    plan_name: Optional[str],
    status: str,
    pdf_bytes: Optional[bytes] = None,
) -> bool:
    """Envoie la facture mensuelle au gestionnaire (PDF en pièce jointe)."""
    period_label = f"{_MONTHS[period_month]} {period_year}"
    statut = "réglée" if status == "paid" else "en attente de règlement"
    content = f"""
<p>Bonjour {client_name},</p>
<p>Veuillez trouver ci-dessous votre facture pour la période <strong>{period_label}</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Formule</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{plan_name or "Abonnement"}</td></tr>
  <tr><td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280">Montant</td>
      <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{amount:.2f} €</td></tr>
  <tr><td style="padding:8px;color:#6b7280">Statut</td>
      <td style="padding:8px;font-weight:600">{statut}</td></tr>
</table>
{"<p>Le détail de votre facture est joint à cet email en PDF.</p>" if pdf_bytes else ""}
<p>Cordialement,<br>L'équipe Le Comptoir Immo</p>
"""
    filename = f"facture-{period_year}-{period_month:02d}.pdf"
    return await send_email(
        to=to,
        subject=f"Votre facture — {period_label}",
        html_body=_base_template(f"Facture {period_label}", content),
        attachment_bytes=pdf_bytes,
        attachment_filename=filename if pdf_bytes else None,
    )
