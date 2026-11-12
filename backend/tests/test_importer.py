"""Tests de l'importeur de cours (services/importer.py)."""

import pytest

from app.services.importer import (
    ChapitreImporte,
    calculer_charge,
    compter_mots,
    extraire_chapitres_markdown,
)


@pytest.mark.parametrize(
    ("nombre_mots", "heures_attendues"),
    [
        (0, 1.0),     # fichier vide : on garde le minimum d'1 h
        (120, 1.0),   # 0,6 h → 1 h : le minimum s'applique
        (200, 1.0),   # 1 h pile : pas d'arrondi
        (201, 1.5),   # 1,005 h → 1,5 h : arrondi au 0,5 h SUPÉRIEUR
        (450, 2.5),   # 2,25 h → 2,5 h
        (600, 3.0),   # 3 h pile
    ],
)
def test_regle_de_charge(nombre_mots: int, heures_attendues: float) -> None:
    """Test 8 : 200 mots/h, arrondi au 0,5 h supérieur, minimum 1 h (SPEC §5.1)."""
    assert calculer_charge(nombre_mots) == heures_attendues
    # Pourquoi un tableau de cas : chaque ligne vise une partie précise de la règle
    # (minimum, valeur pile, arrondi), donc un échec dit tout de suite laquelle est cassée.


def test_compter_mots() -> None:
    """Les mots sont séparés par des espaces, tabulations ou retours à la ligne."""
    assert compter_mots("un deux\ttrois\nquatre  cinq") == 5
    assert compter_mots("") == 0
    # Pourquoi : calculer_charge dépend de ce compte ; s'il est faux, toute la charge l'est.


TEXTE_MARKDOWN = """Intro ignorée
# Chapitre A
un deux trois
## Chapitre B
### Sous-partie
quatre cinq
"""


def test_titres_markdown_deviennent_chapitres() -> None:
    """Test 7 : chaque titre # ou ## devient un chapitre, dans l'ordre (CA1.2)."""
    chapitres = extraire_chapitres_markdown(TEXTE_MARKDOWN, "Cours")
    assert chapitres == [
        ChapitreImporte(titre="Chapitre A", nombre_mots=3, heures=1.0),
        ChapitreImporte(titre="Chapitre B", nombre_mots=4, heures=1.0),
    ]
    # Pourquoi ce texte : il contient les 4 pièges de la règle — du texte avant le
    # 1er titre (ignoré), un # et un ## (chapitres), un ### (simple contenu).


def test_markdown_sans_titre_un_seul_chapitre() -> None:
    """Sans aucun titre, tout le texte forme un seul chapitre nommé comme le cours."""
    chapitres = extraire_chapitres_markdown("un deux trois", "Cours")
    assert chapitres == [ChapitreImporte(titre="Cours", nombre_mots=3, heures=1.0)]
    # Pourquoi : un fichier de notes sans titre doit quand même devenir un cours utilisable.
