"""Tests de la normalisation d'adresse (pure, sans DB)."""
from app.utils.address import normalize_address_fields, split_combined_address


def test_combined_with_newline_no_structured():
    # Cas réel : tout dans address, CP/ville vides, séparateur = retour ligne.
    a, z, c = normalize_address_fields("7 rue d'Alembert\n92600 Asnières-Sur-Seine", "", "")
    assert a == "7 rue d'Alembert"
    assert z == "92600"
    assert c == "Asnières-Sur-Seine"


def test_combined_space_separated_no_structured():
    a, z, c = normalize_address_fields("23 résidence les Alizés 97354 Remire-Montjoly", None, None)
    assert a == "23 résidence les Alizés"
    assert z == "97354"
    assert c == "Remire-Montjoly"


def test_clean_address_unchanged():
    # Déjà propre : on ne touche à rien (idempotent).
    a, z, c = normalize_address_fields("1852 Rue du Champ de Canne", "97351", "Matoury")
    assert (a, z, c) == ("1852 Rue du Champ de Canne", "97351", "Matoury")


def test_zip_duplicated_in_address_is_trimmed():
    # CP renseigné ET présent dans l'adresse → on tronque la rue.
    a, z, c = normalize_address_fields("1852 Rue du Champ de Canne, 97351 Matoury", "97351", "Matoury")
    assert a == "1852 Rue du Champ de Canne"
    assert z == "97351"
    assert c == "Matoury"


def test_city_name_in_street_not_truncated():
    # Garde-fou : ville renseignée mais CP absent de l'adresse → on ne tronque pas
    # (sinon « Rue de Paris » serait coupée).
    a, z, c = normalize_address_fields("Rue de Paris", None, "Paris")
    assert a == "Rue de Paris"
    assert c == "Paris"


def test_empty_address():
    assert normalize_address_fields(None, None, None) == (None, None, None)
    assert normalize_address_fields("", "75001", "Paris") == ("", "75001", "Paris")


def test_idempotent():
    once = normalize_address_fields("7 rue d'Alembert 92600 Asnières", "", "")
    twice = normalize_address_fields(*once)
    assert once == twice


def test_split_helper_no_postal():
    assert split_combined_address("12 rue sans code") == (None, None, None)
