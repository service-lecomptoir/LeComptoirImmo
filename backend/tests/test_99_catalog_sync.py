"""Garde anti-dérive : le repli hors-ligne du frontend doit rester aligné sur le
catalogue canonique (source de vérité unique : core/feature_catalog.py).

Le runtime se synchronise déjà en direct (catalogStore fetch /public/features),
mais le repli statique `FEATURE_LABELS` de frontend/src/lib/features.ts peut
dériver en silence. Ce test échoue en CI dès qu'une clé ou un libellé diverge,
ce qui aurait évité l'incident « Ma papeterie » / « agents_ia ».
"""
import re
from pathlib import Path

from app.core.feature_catalog import public_catalog

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "features.ts"
# Libellé en simple OU double quote (certains contiennent une apostrophe).
_LABEL = r"""(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")"""


def _parse_block(source: str, marker: str) -> dict[str, str]:
    block = source.split(marker, 1)[1].split("}", 1)[0]
    return {k: (a or b) for k, a, b in re.findall(r"(\w+):\s*" + _LABEL, block)}


def _front_labels() -> dict[str, str]:
    return _parse_block(_FRONT.read_text(encoding="utf-8"), "FEATURE_LABELS")


def test_frontend_fallback_has_same_keys_as_catalog():
    catalog = {item["key"] for item in public_catalog()}
    front = set(_front_labels())
    assert front == catalog, (
        f"Repli frontend désynchronisé. Manquantes={sorted(catalog - front)} "
        f"En trop={sorted(front - catalog)}"
    )


def test_frontend_fallback_labels_match_catalog():
    front = _front_labels()
    mismatches = {
        item["key"]: (item["label"], front.get(item["key"]))
        for item in public_catalog()
        if front.get(item["key"]) != item["label"]
    }
    assert not mismatches, f"Libellés divergents (catalogue vs repli) : {mismatches}"
