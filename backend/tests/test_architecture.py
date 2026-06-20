"""
Tests de conformité d'architecture (garde-fous anti-régression).

Ces tests codifient les invariants de conception du produit pour qu'une
régression soit détectée automatiquement. Ils sont VOLONTAIREMENT statiques
(analyse du code source + import de l'app) et NE nécessitent PAS de base de
données — ils sont donc rapides et déterministes.

Couverture :
  1. Sécurité — fail-fast sur secrets de dev en production (config.Settings).
  2. Sécurité — comparaison constant-time de la clé interne (internal_admin).
  3. Sécurité — middlewares de sécurité câblés (en-têtes + rate limiter).
  4. Routage — aucun APIRouter orphelin (tout router v1 est monté quelque part).
  5. Layering — app.models / app.services n'importent PAS app.api (pas de
     dépendance montante).
"""
import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
V1 = APP / "api" / "v1"


# Champs requis (sans valeur par défaut) pour instancier Settings hors .env.
def _base_settings_kwargs() -> dict:
    return {
        "SECRET_KEY": "x" * 48,
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
        "POSTGRES_PASSWORD": "p",
        # Secrets que le validateur surveille : valeurs sûres par défaut ici.
        "ALICE_INTERNAL_KEY": "a-real-rotated-internal-key-not-the-default",
        "FIRST_ADMIN_PASSWORD": "A-Real-Strong-Admin-Pass-9!",
    }


# ── 1. Sécurité : fail-fast sur secrets de dev en production ────────────────────
def test_production_rejects_insecure_alice_key():
    from app.config import Settings, _INSECURE_DEFAULTS

    kwargs = _base_settings_kwargs()
    kwargs["APP_ENV"] = "production"
    kwargs["ALICE_INTERNAL_KEY"] = _INSECURE_DEFAULTS["ALICE_INTERNAL_KEY"]
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs)


def test_production_rejects_insecure_admin_password():
    from app.config import Settings, _INSECURE_DEFAULTS

    kwargs = _base_settings_kwargs()
    kwargs["APP_ENV"] = "production"
    kwargs["FIRST_ADMIN_PASSWORD"] = _INSECURE_DEFAULTS["FIRST_ADMIN_PASSWORD"]
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs)


def test_production_accepts_rotated_secrets():
    from app.config import Settings

    kwargs = _base_settings_kwargs()
    kwargs["APP_ENV"] = "production"
    cfg = Settings(_env_file=None, **kwargs)  # ne doit PAS lever
    assert cfg.is_production is True


def test_non_production_allows_dev_defaults():
    """Hors production, les valeurs de dev sont tolérées (DX, tests, CI)."""
    from app.config import Settings, _INSECURE_DEFAULTS

    kwargs = _base_settings_kwargs()
    kwargs["APP_ENV"] = "development"
    kwargs["ALICE_INTERNAL_KEY"] = _INSECURE_DEFAULTS["ALICE_INTERNAL_KEY"]
    kwargs["FIRST_ADMIN_PASSWORD"] = _INSECURE_DEFAULTS["FIRST_ADMIN_PASSWORD"]
    cfg = Settings(_env_file=None, **kwargs)  # ne doit PAS lever
    assert cfg.is_production is False


# ── 2. Sécurité : comparaison constant-time de la clé interne ───────────────────
def test_internal_key_uses_constant_time_comparison():
    src = (V1 / "internal_admin.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in src, (
        "La vérification de X-Internal-Key doit utiliser hmac.compare_digest "
        "(anti timing-attack)."
    )


def test_internal_key_has_no_plaintext_comparison():
    """Aucune comparaison directe `== ...INTERNAL_KEY` / `!= ...INTERNAL_KEY`
    (vulnérable au timing) ne doit subsister dans le contrat interne."""
    src = (V1 / "internal_admin.py").read_text(encoding="utf-8")
    # Détecte == / != suivi (à courte distance) d'un identifiant *INTERNAL_KEY.
    bad = re.search(r"(==|!=)\s*[A-Za-z_][\w.]*INTERNAL_KEY", src)
    assert bad is None, (
        f"Comparaison en clair de la clé interne détectée : {bad.group(0)!r}. "
        "Utiliser hmac.compare_digest à la place."
    )


# ── 3. Sécurité : middlewares de sécurité câblés sur l'app ──────────────────────
def test_security_headers_middleware_registered():
    from app.core.security_headers import SecurityHeadersMiddleware
    from app.main import app

    classes = {m.cls for m in app.user_middleware}
    assert SecurityHeadersMiddleware in classes, (
        "SecurityHeadersMiddleware doit être enregistré sur l'app."
    )


def test_rate_limiter_registered():
    from slowapi import Limiter
    from slowapi.middleware import SlowAPIMiddleware
    from app.main import app

    # Limiter exposé sur app.state (requis par slowapi).
    assert isinstance(getattr(app.state, "limiter", None), Limiter), (
        "app.state.limiter doit être un slowapi.Limiter."
    )
    # Middleware slowapi monté.
    classes = {m.cls for m in app.user_middleware}
    assert SlowAPIMiddleware in classes, "SlowAPIMiddleware doit être monté."


# ── 4. Routage : aucun APIRouter v1 orphelin ────────────────────────────────────
# Routers volontairement montés AILLEURS qu'à travers l'agrégateur api_router :
#   - internal_admin : monté À LA RACINE dans app/main.py (hors /api, privé Alice).
# Les sous-routers (ex. entretiens.prestataires_router) sont inclus dans le
# router principal de leur module, donc reliés transitivement à l'agrégateur.
_ROUTING_ALLOWLIST = {"internal_admin"}


def _module_router_names(tree: ast.AST) -> list[str]:
    """Noms de variables module-level assignées à un APIRouter(...)."""
    names: list[str] = []
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if (
            isinstance(val, ast.Call)
            and isinstance(val.func, ast.Name)
            and val.func.id == "APIRouter"
        ):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
    return names


def _collect_routes_recursive(router) -> set[str]:
    """Tous les chemins (path) exposés par un router, sous-routers inclus."""
    from fastapi.routing import APIRoute

    # NB : r.path inclut déjà le prefix du router (FastAPI matérialise le chemin
    # complet sur chaque APIRoute, prefix compris).
    paths: set[str] = set()
    for r in getattr(router, "routes", []):
        if isinstance(r, APIRoute):
            paths.add(r.path)
    return paths


def test_every_v1_router_is_mounted():
    from fastapi.routing import APIRoute

    from app.api.v1.router import api_router

    # Tous les chemins réellement montés via l'agrégateur (sous-routers inclus).
    mounted_paths = {r.path for r in api_router.routes if isinstance(r, APIRoute)}

    orphans: list[str] = []
    for py in sorted(V1.glob("*.py")):
        name = py.stem
        if name in {"router", "__init__"} or name.startswith("_"):
            continue
        if name in _ROUTING_ALLOWLIST:
            continue

        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        router_names = _module_router_names(tree)
        if not router_names:
            continue  # module sans APIRouter (helpers)

        import importlib

        mod = importlib.import_module(f"app.api.v1.{name}")
        # Le module est « monté » si au moins un de ses chemins apparaît dans
        # l'arbre de routes assemblé par l'agrégateur.
        module_paths: set[str] = set()
        for rn in router_names:
            router_obj = getattr(mod, rn, None)
            if router_obj is not None:
                module_paths |= _collect_routes_recursive(router_obj)

        # L'agrégateur préfixe les chemins (/api/v1 + préfixe de sous-router),
        # alors que router.routes du module porte le chemin « nu ». On vérifie
        # donc qu'au moins un chemin du module est SUFFIXE d'un chemin monté.
        def _is_mounted(p: str) -> bool:
            if not p:  # garde : un chemin vide rendrait endswith trivial
                return False
            return any(mp == p or mp.endswith(p) for mp in mounted_paths)

        if module_paths and not any(_is_mounted(p) for p in module_paths):
            orphans.append(name)

    assert not orphans, (
        "Routers v1 définis mais jamais montés dans api_router : "
        f"{orphans}. Inclure le router dans app/api/v1/router.py, ou "
        "l'ajouter à _ROUTING_ALLOWLIST avec un commentaire si le montage est "
        "volontairement ailleurs."
    )


# ── 5. Layering : app.models / app.services n'importent PAS app.api ──────────────
# Exceptions LÉGITIMES connues (dette technique bornée, import différé pour
# casser les cycles ; à résorber lors d'un futur déplacement de _isolation vers
# la couche services). Toute NOUVELLE violation hors de cette liste fait
# échouer le test.
#   - _isolation : helpers de périmètre multi-agences hébergés sous api/v1 mais
#     réutilisés par des services (scoping). Imports surtout différés (locaux).
#   - payments.build_quittance_pdf : générateur PDF appelé par automation_engine.
_LAYERING_ALLOWLIST = {
    ("services/signalement_service.py", "app.api.v1._isolation"),
    ("services/agent_action_service.py", "app.api.v1._isolation"),
    ("services/agent_team_service.py", "app.api.v1._isolation"),
    ("services/automation_engine.py", "app.api.v1.payments"),
}


def _iter_imports(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name


def test_lower_layers_do_not_import_api():
    violations: list[str] = []
    for layer in ("models", "services"):
        root = APP / layer
        for py in sorted(root.rglob("*.py")):
            rel = py.relative_to(APP).as_posix()
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for mod in _iter_imports(tree):
                if mod == "app.api" or mod.startswith("app.api."):
                    if (rel, mod) in _LAYERING_ALLOWLIST:
                        continue
                    violations.append(f"{rel} -> {mod}")

    assert not violations, (
        "Dépendance montante interdite (couche basse importe app.api) :\n  "
        + "\n  ".join(violations)
        + "\nDéplacer le code partagé vers app.services/app.core, ou "
        "ajouter une exception justifiée à _LAYERING_ALLOWLIST."
    )
