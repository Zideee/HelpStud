"""Tests de l'importeur de cours (services/importer.py)."""

import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.importer import (
    ChapitreImporte,
    FichierVide,
    FormatNonSupporte,
    calculer_charge,
    compter_mots,
    extraire_chapitres_markdown,
    extraire_chapitres_pdf,
    importer_cours,
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


def creer_pdf(textes_des_pages: list[str]) -> bytes:
    """Fabrique en mémoire un PDF d'une page par texte (texte vide = page blanche)."""
    redacteur = PdfWriter()
    police = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for texte in textes_des_pages:
        page = redacteur.add_blank_page(width=612, height=792)
        if texte:
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): police})}
            )
            contenu = DecodedStreamObject()
            contenu.set_data(f"BT /F1 12 Tf 72 720 Td ({texte}) Tj ET".encode("latin-1"))
            page.replace_contents(contenu)
    tampon = io.BytesIO()
    redacteur.write(tampon)
    return tampon.getvalue()
    # Pourquoi fabriquer le PDF dans le test plutôt que commiter un fichier : on voit
    # exactement le texte de chaque page, et on en crée autant de variantes qu'on veut.


def test_pdf_un_chapitre_par_page() -> None:
    """P0-03 : un chapitre « Page N » par page non vide ; les pages blanches sont sautées."""
    contenu = creer_pdf(["un deux trois", "", "quatre cinq"])
    assert extraire_chapitres_pdf(contenu, "Cours") == [
        ChapitreImporte(titre="Page 1", nombre_mots=3, heures=1.0),
        ChapitreImporte(titre="Page 3", nombre_mots=2, heures=1.0),
    ]
    # Pourquoi « Page 3 » et pas « Page 2 » : le numéro reste celui du PDF, pour que
    # l'étudiant retrouve la page dans son document.


def test_pdf_sans_texte_leve_fichier_vide() -> None:
    """Un PDF sans aucun mot (pages blanches, scan) est refusé."""
    with pytest.raises(FichierVide):
        extraire_chapitres_pdf(creer_pdf(["", ""]), "Cours")


def test_pdf_illisible_leve_fichier_vide() -> None:
    """Un fichier .pdf qui n'est pas un vrai PDF est refusé, sans faire planter l'API."""
    with pytest.raises(FichierVide):
        extraire_chapitres_pdf(b"ceci n'est pas un pdf", "Cours")


def test_importer_cours_markdown() -> None:
    """Le nom du cours est le nom du fichier sans extension ; l'extension est insensible à la casse."""
    nom, chapitres = importer_cours("SQL.MD", "# Bases\nun deux".encode("utf-8"))
    assert nom == "SQL"
    assert chapitres == [ChapitreImporte(titre="Bases", nombre_mots=2, heures=1.0)]


def test_importer_cours_pdf() -> None:
    """Un .pdf passe par l'extraction PDF."""
    nom, chapitres = importer_cours("stats.pdf", creer_pdf(["un deux"]))
    assert nom == "stats"
    assert [chapitre.titre for chapitre in chapitres] == ["Page 1"]


def test_importer_cours_format_non_supporte() -> None:
    """Un fichier ni .md ni .pdf est refusé (l'API renverra 415)."""
    with pytest.raises(FormatNonSupporte):
        importer_cours("notes.docx", b"x")


@pytest.mark.parametrize("contenu", [b"", b"   \n\n  "])
def test_importer_cours_markdown_vide(contenu: bytes) -> None:
    """Un Markdown vide ou sans aucun mot est refusé (l'API renverra 422)."""
    with pytest.raises(FichierVide):
        importer_cours("vide.md", contenu)
