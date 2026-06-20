"""Actualisation des loyers — Étape 2 : mention de révision IRL à venir.

Prévient le locataire 1 mois à l'avance : la mention est ajoutée sur l'avis
d'échéance du mois précédant la date de révision, sur la quittance correspondante,
et déclenche une notification + un e-mail (no-op tant que SMTP est désactivé).

Logique précise pour le rythme mensuel : on affiche la mention si la révision
prend effet le mois SUIVANT immédiatement la période de l'avis/quittance.
"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease
from app.services.irl_service import IrlService

_MONTHS_FR = [
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


def next_revision_date(lease: Lease) -> date:
    """Prochaine date anniversaire de révision (dernière révision ou début de bail)."""
    base = lease.last_revision_date or lease.start_date
    try:
        return base.replace(year=base.year + 1)
    except ValueError:  # 29 février
        return base + timedelta(days=365)


def _month_after(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


async def upcoming_revision_notice(
    db: AsyncSession, lease: Lease, period_year: int, period_month: int
) -> dict | None:
    """Renvoie les infos de la mention si une révision IRL prend effet le mois
    suivant cette période (sinon None)."""
    if not lease or not getattr(lease, "irl_quarter", None) or lease.irl_base_index is None:
        return None
    nrd = next_revision_date(lease)
    if (nrd.year, nrd.month) != _month_after(period_year, period_month):
        return None
    base = float(lease.irl_base_index)
    if base <= 0:
        return None
    old_rent = float(lease.rent_amount)
    latest = await IrlService.get_latest_for_quarter(db, lease.irl_quarter)
    new_rent = round(old_rent * float(latest.value) / base, 2) if latest else None
    return {
        "effective_date": f"{nrd.day} {_MONTHS_FR[nrd.month - 1]} {nrd.year}",
        "old_rent": old_rent,
        "new_rent": new_rent,
        "irl_quarter": lease.irl_quarter,
        "irl_year": latest.year if latest else None,
        "irl_value": float(latest.value) if latest else None,
    }


def notice_text(notice: dict) -> str:
    """Texte brut de la mention (notifications, e-mail)."""
    eff = notice["effective_date"]
    if notice.get("new_rent") is not None:
        return (
            f"Conformément à votre bail, votre loyer sera révisé selon l'indice de "
            f"référence des loyers (IRL). À compter du {eff}, le loyer mensuel passera "
            f"de {notice['old_rent']:.2f} € à {notice['new_rent']:.2f} € "
            f"(IRL T{notice['irl_quarter']} {notice['irl_year']})."
        )
    return (
        f"Conformément à votre bail, votre loyer sera révisé selon l'indice de "
        f"référence des loyers (IRL) à compter du {eff}. Le nouveau montant vous "
        f"sera précisé dès la publication de l'indice applicable."
    )


def notice_html(notice: dict) -> str:
    """Bloc HTML de la mention, à insérer dans les PDF (avis/quittance)."""
    eff = notice["effective_date"]
    if notice.get("new_rent") is not None:
        body = (
            f"Conformément à votre bail, votre loyer fera l'objet d'une révision "
            f"annuelle selon l'indice de référence des loyers (IRL). À compter du "
            f"<strong>{eff}</strong>, le loyer mensuel passera de "
            f"<strong>{notice['old_rent']:.2f} €</strong> à "
            f"<strong>{notice['new_rent']:.2f} €</strong> "
            f"(IRL T{notice['irl_quarter']} {notice['irl_year']})."
        )
    else:
        body = (
            f"Conformément à votre bail, votre loyer fera l'objet d'une révision "
            f"annuelle selon l'indice de référence des loyers (IRL) à compter du "
            f"<strong>{eff}</strong>. Le nouveau montant vous sera précisé dès la "
            f"publication de l'indice applicable."
        )
    return (
        '<div style="margin-top:16px;padding:10px 12px;border:1px solid #d1d5db;'
        'border-left:4px solid #2563eb;background:#f8fafc;font-size:11px;color:#374151;">'
        '<strong style="color:#1e3a8a;">Information : révision de loyer à venir</strong><br/>'
        f"{body}</div>"
    )


def inject_notice(html: str, notice: dict) -> str:
    """Insère le bloc de mention juste avant </body> (ou en fin de document)."""
    block = notice_html(notice)
    if "</body>" in html:
        return html.replace("</body>", block + "</body>", 1)
    return html + block
