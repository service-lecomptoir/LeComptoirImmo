"""Nomenclature des fichiers générés : tout en MAJUSCULES (extension en minuscules)."""

from app.utils.filename import doc_filename, upper_filename


def test_upper_filename_garde_extension_minuscule():
    assert upper_filename("regularisation-charges-12.pdf") == "REGULARISATION-CHARGES-12.pdf"
    assert upper_filename("quittance_dupont_072026.PDF") == "QUITTANCE_DUPONT_072026.pdf"
    assert upper_filename("signalements.csv") == "SIGNALEMENTS.csv"


def test_upper_filename_sans_extension():
    assert upper_filename("sans_extension") == "SANS_EXTENSION"
    assert upper_filename("") == ""


def test_doc_filename_en_majuscules():
    nom = doc_filename(
        "quittance", tenant="Jean Dupont", property_name="Les Tilleuls", month=7, year=2026
    )
    assert nom == "QUITTANCE_JEAN_DUPONT_LES_TILLEULS_072026.pdf"
    assert nom == nom[:-4].upper() + ".pdf"  # corps en MAJ, extension en min

    bail = doc_filename("bail", tenant="Marie Curie")
    assert bail == "BAIL_MARIE_CURIE.pdf"
