# -*- coding: utf-8 -*-
"""Journalisation fichier de LeComptoir Immo (supervisée par Portail360).

Écrit deux journaux rotatifs (taille bornée → ne sature pas le disque) dans
`LOG_DIR` (monté sur l'hôte, lisible par Portail360 en SSH) :
  - immo.log         : tout (INFO+), exploitation courante ;
  - immo-error.log   : avertissements et erreurs (WARNING+), pour repérer les bugs.

La sortie console (docker logs) est conservée. Idempotent : n'ajoute pas deux
fois les mêmes handlers (workers uvicorn multiples)."""
from __future__ import annotations
import logging
import os
from logging.handlers import RotatingFileHandler

_FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging() -> None:
    log_dir = os.getenv("LOG_DIR", "/app/logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:  # noqa: BLE001 : pas de dossier inscriptible → on garde stdout
        return

    fmt = logging.Formatter(_FMT)
    root = logging.getLogger()
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)

    present = {getattr(h, "_lci_tag", None) for h in root.handlers}

    if "all" not in present:
        fh = RotatingFileHandler(
            os.path.join(log_dir, "immo.log"),
            maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
        )
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        fh._lci_tag = "all"  # type: ignore[attr-defined]
        root.addHandler(fh)

    if "err" not in present:
        eh = RotatingFileHandler(
            os.path.join(log_dir, "immo-error.log"),
            maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8",
        )
        eh.setLevel(logging.WARNING)
        eh.setFormatter(fmt)
        eh._lci_tag = "err"  # type: ignore[attr-defined]
        root.addHandler(eh)

    # Les erreurs serveur (exceptions non gérées, tracebacks) passent par
    # « uvicorn.error » → on les fait remonter vers la racine (donc vers nos
    # fichiers) sans casser la sortie console d'uvicorn.
    for name in ("uvicorn.error", "fastapi"):
        logging.getLogger(name).propagate = True
