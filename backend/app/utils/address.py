"""Normalisation d'adresse — découpe « comme si l'utilisateur l'avait saisie
via l'autocomplétion » : rue dans `address`, code postal dans `zip_code`,
ville dans `city`.

Utilisé sur les chemins d'écriture (comptes, fiches propriétaires) pour qu'une
adresse combinée (« 7 rue d'Alembert 92600 Asnières-Sur-Seine ») ne soit jamais
stockée d'un seul tenant, sans que l'utilisateur ait à re-saisir quoi que ce soit.
"""

import re

# Code postal français / DOM : 5 chiffres consécutifs.
_POSTAL_RE = re.compile(r"\d{5}")
# Caractères de bord à retirer (espaces, virgules, retours ligne, tabulations).
_STRIP = " ,\r\n\t"


def split_combined_address(address):
    """Découpe « rue CP ville » → (rue, cp, ville).

    Renvoie (rue, cp, ville) si `address` contient un code postal à 5 chiffres
    précédé d'une rue ET suivi d'une ville ; sinon (None, None, None).
    """
    if not address:
        return None, None, None
    m = _POSTAL_RE.search(address)
    if not m:
        return None, None, None
    street = address[: m.start()].strip(_STRIP)
    town = address[m.end() :].strip(_STRIP)
    if not street or not town:
        return None, None, None
    return street, m.group(0), town


def normalize_address_fields(address, zip_code, city):
    """Normalise le triplet (address, zip_code, city).

    - Si rien n'est structuré (zip_code/city vides) et que `address` est combinée,
      on la découpe et on remplit les trois champs.
    - Si le code postal est déjà renseigné ET présent dans `address` (doublon),
      on tronque `address` pour ne garder que la rue.
    Idempotent : une adresse déjà propre est renvoyée telle quelle. Conservateur :
    on ne tronque jamais sur la seule base du nom de ville (éviter « Rue de Paris »).
    """
    if not address:
        return address, zip_code, city

    has_zip = bool(zip_code and str(zip_code).strip())
    has_city = bool(city and str(city).strip())

    # Cas 1 — aucun champ structuré : on découpe l'adresse combinée.
    if not has_zip and not has_city:
        street, cp, town = split_combined_address(address)
        if street is not None:
            return street, cp, town
        return address, zip_code, city

    # Cas 2 — le CP est déjà connu et dupliqué dans l'adresse : on tronque la rue.
    if has_zip:
        z = str(zip_code).strip()
        idx = address.find(z)
        if idx > 0:
            street = address[:idx].strip(_STRIP)
            if street:
                return street, zip_code, city

    return address, zip_code, city
