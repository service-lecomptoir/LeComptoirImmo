"""Garde-fou CRITIQUE : aucune instruction destructive non gardée au démarrage.

Un déploiement ne doit JAMAIS supprimer de données en production. Ce test échoue
si le SQL de démarrage (`app/main.py`) contient une instruction `DELETE` sans
clause `WHERE`, ou un `TRUNCATE`.

Régression historique (corrigée) : un `DELETE FROM lease_rent_revisions`
inconditionnel s'exécutait à CHAQUE démarrage et effaçait toutes les
réévaluations de loyer programmées à chaque déploiement. Toute purge de migration
doit désormais être gardée (ex. `WHERE EXISTS (SELECT 1 FROM information_schema...`)
pour devenir un no-op une fois la migration passée.
"""

import ast
import re
from pathlib import Path

# Vraies instructions SQL (avec table cible) — pas les simples jetons de détection.
DELETE_RE = re.compile(r"\bDELETE\s+FROM\s+\w+", re.IGNORECASE)
TRUNCATE_RE = re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?\w+", re.IGNORECASE)
WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)


def _sql_literals(path: Path) -> list[str]:
    """Toutes les chaînes littérales du fichier (l'AST concatène déjà les
    littéraux adjacents → on récupère l'instruction SQL complète)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_no_unguarded_destructive_startup_sql():
    main_py = Path(__file__).resolve().parents[1] / "app" / "main.py"
    offending: list[tuple[str, str]] = []
    for raw in _sql_literals(main_py):
        u = " ".join(raw.split())  # normalise espaces / retours ligne
        if TRUNCATE_RE.search(u):
            offending.append(("TRUNCATE interdit au démarrage", u[:140]))
        if DELETE_RE.search(u) and not WHERE_RE.search(u):
            offending.append(("DELETE sans WHERE (non gardé)", u[:140]))

    assert not offending, (
        "Instruction(s) destructive(s) non gardée(s) dans app/main.py — un déploiement "
        "ne doit jamais supprimer de données en prod. Ajoute un garde "
        "(WHERE EXISTS information_schema..., ou une condition) :\n"
        + "\n".join(f"  - [{kind}] {sql}" for kind, sql in offending)
    )
