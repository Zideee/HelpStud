"""Test 1 (métier) : import d'un cours Markdown — chapitres et charge (CA1.1, CA1.2, CA1.4, CA1.6)."""

import pytest

from app.services.importer import (
    ChapitreImporte,
    FormatNonSupporte,
    calculer_charge,
    importer_cours,
)


def test_import_markdown_chapitres_et_charge() -> None:
    """Titres # et ## → chapitres ; 200 mots/h, arrondi au 0,5 h supérieur, min 1 h ; .docx refusé."""
    texte = (
        "Intro ignorée\n"
        "# Chapitre A\n" + "mot " * 450 + "\n"
        "## Chapitre B\n"
        "### Sous-partie\n"
        "quatre cinq\n"
    )
    nom, chapitres = importer_cours("SQL.md", texte.encode("utf-8"))

    # Nom du cours = nom du fichier ; texte avant le 1er titre ignoré ; ### = contenu.
    assert nom == "SQL"
    assert chapitres == [
        ChapitreImporte(titre="Chapitre A", nombre_mots=450, heures=2.5),  # 2,25 h → 2,5 h
        ChapitreImporte(titre="Chapitre B", nombre_mots=4, heures=1.0),    # minimum 1 h
    ]
    # Les deux bords de l'arrondi : 200 mots = 1 h pile, 201 mots = 1,5 h.
    assert calculer_charge(200) == 1.0
    assert calculer_charge(201) == 1.5
    # Un format non supporté est refusé (l'API renverra 415).
    with pytest.raises(FormatNonSupporte):
        importer_cours("notes.docx", b"x")
    # Pourquoi un seul test pour tout l'import : c'est un MVP ; chaque assert vise une
    # règle précise de SPEC §5.1 / CA1.x, et le message d'échec de pytest dit laquelle.
