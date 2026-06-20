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


def doc_filename(
    prefix: str,
    *,
    tenant: str | None = None,
    property_name: str | None = None,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """Retourne `prefix_Tenant_Property_mmaaaa.pdf`.

    - mois+année présents → suffixe daté `mmaaaa` (mois sur 2 chiffres) ;
    - année seule → suffixe `aaaa` ;
    - sinon pas de suffixe daté.
    """
    segments = [prefix, _slug(tenant), _slug(property_name)]
    if month and year:
        segments.append(f"{int(month):02d}{int(year)}")
    elif year:
        segments.append(str(int(year)))
    return "_".join(s for s in segments if s) + ".pdf"
