"""Génération de mots de passe temporaires (identifiants envoyés par e-mail)."""

import secrets

# Alphabet lisible (sans caractères ambigus : 0/O, 1/l/I).
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def generate_temp_password(length: int = 10) -> str:
    """Mot de passe temporaire lisible, à usage unique (changement forcé ensuite)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
