"""Construction normalisée des noms de fichiers PDF téléchargés.

Miroir backend de `frontend/src/utils/filename.ts` : tout document porte un
suffixe `nom_prenom_locataire_nom_bien_mmaaaa` (séparés par `_`).
"""

from __future__ import annotations

import re
import unicodedata


def _slug(value: str | None) -> str:
    """Translittère, retire les accents, remplace tout non-alphanumérique par '_'."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    return text.strip("_")


def upper_filename(name: str) -> str:
    """Met la nomenclature du fichier en MAJUSCULES, en gardant l'extension en
    minuscules (`quittance_dupont_072026.pdf` → `QUITTANCE_DUPONT_072026.pdf`)."""
    if not name:
        return name
    dot = name.rfind(".")
    if dot <= 0:  # pas d'extension exploitable
        return name.upper()
    return name[:dot].upper() + name[dot:].lower()


def simple_doc_filename(prefix: str, *parts: object, ext: str = "pdf") -> str:
    """Nom de fichier sans suffixe locataire, en MAJUSCULES : `PREFIX-PART1-...ext`.

    Factorise les noms construits « à la main » (régularisation de charges,
    révision de loyer, taxe, rapport, export…) pour éviter les littéraux dispersés.
    Les parties vides (None / "") sont ignorées.
    """
    segments = [str(prefix)] + [str(p) for p in parts if p not in (None, "")]
    return upper_filename("-".join(segments) + "." + ext.lstrip("."))


def doc_filename(
    prefix: str,
    *,
    tenant: str | None = None,
    property_name: str | None = None,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """Retourne `PREFIX_TENANT_PROPERTY_mmaaaa.pdf` (nomenclature en MAJUSCULES).

    - mois+année présents → suffixe daté `mmaaaa` (mois sur 2 chiffres) ;
    - année seule → suffixe `aaaa` ;
    - sinon pas de suffixe daté.
    """
    segments = [prefix, _slug(tenant), _slug(property_name)]
    if month and year:
        segments.append(f"{int(month):02d}{int(year)}")
    elif year:
        segments.append(str(int(year)))
    return upper_filename("_".join(s for s in segments if s) + ".pdf")
