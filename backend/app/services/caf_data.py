"""Données disponibles pour remplir les PDF officiels CAF (mapping champ→donnée).

Construit, pour un bail, le dictionnaire des valeurs (bailleur, locataire,
logement, montants, dates) que le gestionnaire associe aux champs du CERFA
téléversé. Réutilise la même logique que les modèles générés (letters.py)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.owner import Owner

MONTHS_FR = [
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

# Clés de données proposées dans l'éditeur de mapping (clé → libellé lisible).
DATA_KEYS: list[tuple[str, str]] = [
    ("bailleur_name", "Bailleur : nom / raison sociale"),
    ("bailleur_addr1", "Bailleur : adresse (ligne 1)"),
    ("bailleur_addr2", "Bailleur : adresse (ligne 2, CP Ville)"),
    ("bailleur_phone", "Bailleur : téléphone"),
    ("bailleur_email", "Bailleur : e-mail"),
    ("bailleur_siret", "Bailleur : SIRET"),
    ("tenant_name", "Locataire : nom complet"),
    ("tenant2_name", "Co-locataire : nom complet"),
    ("start_date", "Date d'entrée dans les lieux"),
    ("logement_street", "Logement : rue"),
    ("logement_cpville", "Logement : CP et ville"),
    ("ville", "Logement : ville"),
    ("area_sqm", "Surface (m²)"),
    ("rent_no_charges", "Loyer hors charges (€)"),
    ("charges", "Charges (€)"),
    ("total_tcc", "Loyer charges comprises (€)"),
    ("month_entry", "Mois d'entrée (texte)"),
    ("july_year", "Année de juillet"),
    ("nb_coloc", "Nombre de colocataires"),
    ("today", "Date du jour"),
    ("mandataire_company", "Mandataire : société"),
    ("mandataire_national_id", "Mandataire : SIRET"),
]
DATA_KEY_SET = {k for k, _ in DATA_KEYS}


def _split_address(addr):
    """Coupe une adresse texte en (rue, 'CP Ville') devant le 1er code postal (5 chiffres)."""
    import re

    s = (addr or "").strip()
    if not s:
        return "", ""
    m = re.search(r"\b\d{5}\b", s)
    if not m:
        return s, ""
    return s[: m.start()].strip(" ,"), s[m.start() :].strip(" ,")


async def build_values(db: AsyncSession, current_user, lease) -> dict:
    """Valeurs (texte) disponibles pour le remplissage du CERFA, à partir du bail."""
    tenant = lease.tenant
    prop = lease.parent_property
    today = date.today()
    owner = None
    if prop and getattr(prop, "owner_id", None):
        owner = (
            await db.execute(select(Owner).where(Owner.id == prop.owner_id))
        ).scalar_one_or_none()
    co_tenants = list(lease.co_tenants or [])
    tenant2 = co_tenants[0] if co_tenants else None
    nb_coloc = 1 + len(co_tenants)
    addr1, addr2 = _split_address(owner.full_address if owner else None)
    logement_street = (prop.address if prop else "") or ""
    logement_cpville = " ".join(
        p for p in [(prop.zip_code if prop else ""), (prop.city if prop else "")] if p
    ).strip()
    sd = lease.start_date
    return {
        "bailleur_name": (
            getattr(current_user, "owner_full_name", None)
            or (owner.full_name if owner else None)
            or (prop.owner_name if prop else None)
            or getattr(current_user, "full_name", "")
        ),
        "bailleur_addr1": addr1,
        "bailleur_addr2": addr2,
        "bailleur_phone": (owner.phone if owner else None)
        or (prop.owner_phone if prop else None)
        or getattr(current_user, "phone", "")
        or "",
        "bailleur_email": (owner.email if owner else None)
        or (prop.owner_email if prop else None)
        or getattr(current_user, "email", "")
        or "",
        "bailleur_siret": (owner.national_id if owner else None) or "",
        "tenant_name": tenant.full_name if tenant else "",
        "tenant2_name": tenant2.full_name if tenant2 else "",
        "start_date": sd.strftime("%d/%m/%Y") if sd else "",
        "logement_street": logement_street,
        "logement_cpville": logement_cpville,
        "ville": prop.city if prop and prop.city else "",
        "area_sqm": f"{float(prop.area_sqm):.0f}"
        if prop and getattr(prop, "area_sqm", None)
        else "",
        "rent_no_charges": f"{float(lease.rent_amount):.2f}"
        if lease.rent_amount is not None
        else "",
        "charges": f"{float(lease.charges_amount):.2f}" if lease.charges_amount is not None else "",
        "total_tcc": f"{lease.total_monthly:.2f}"
        if getattr(lease, "total_monthly", None) is not None
        else "",
        "month_entry": f"{MONTHS_FR[sd.month]} {sd.year}" if sd else "",
        "july_year": str(today.year),
        "nb_coloc": str(nb_coloc),
        "today": today.strftime("%d/%m/%Y"),
        "mandataire_company": getattr(current_user, "owner_company", "") or "",
        "mandataire_national_id": getattr(current_user, "owner_national_id", "") or "",
    }
