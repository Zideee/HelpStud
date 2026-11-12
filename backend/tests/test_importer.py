"""Test 1 (métier) : import d'un cours PDF — chapitres et charge par lignes (CA1.1 à CA1.4, CA1.6)."""

import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.importer import (
    ChapitreImporte,
    FormatNonSupporte,
    calculer_charge,
    importer_cours,
)


def creer_pdf(pages: list[list[str]]) -> bytes:
    """Fabrique en mémoire un PDF : une page par liste de lignes (liste vide = page blanche)."""
    redacteur = PdfWriter()
    police = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                               NameObject("/Subtype"): NameObject("/Type1"),
                               NameObject("/BaseFont"): NameObject("/Helvetica")})
    for lignes in pages:
        page = redacteur.add_blank_page(width=612, height=792)
        if lignes:
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): police})})
            texte = " T* ".join(f"({ligne}) Tj" for ligne in lignes)
            contenu = DecodedStreamObject()
            contenu.set_data(f"BT /F1 10 Tf 14 TL 72 760 Td {texte} ET".encode("latin-1"))
            page.replace_contents(contenu)
    tampon = io.BytesIO()
    redacteur.write(tampon)
    return tampon.getvalue()
    # Pourquoi fabriquer le PDF dans le test : on décide exactement combien de lignes a
    # chaque page, donc on connaît la charge attendue. « T* » = « passer à la ligne ».


def test_import_pdf_chapitres_et_charge() -> None:
    """PDF → un chapitre par page non vide ; 40 lignes/h, arrondi au 0,5 h sup., min 1 h ;
    Markdown toujours accepté par le service ; .docx refusé."""
    # 1. Un PDF de 3 pages : 90 lignes, une page blanche, 10 lignes.
    pdf = creer_pdf([[f"ligne {i}" for i in range(90)], [], [f"ligne {i}" for i in range(10)]])
    nom, chapitres = importer_cours("Statistiques.pdf", pdf)
    assert nom == "Statistiques"
    assert chapitres == [
        ChapitreImporte(titre="Page 1", nombre_lignes=90, heures=2.5),  # 2,25 h → 2,5 h
        ChapitreImporte(titre="Page 3", nombre_lignes=10, heures=1.0),  # 0,25 h → minimum 1 h
    ]
    # 2. Les bords de la règle (SPEC §5.1) : 40 lignes = 1 h pile, 41 = 1,5 h, 120 = 3 h.
    assert [calculer_charge(n) for n in (40, 41, 120)] == [1.0, 1.5, 3.0]
    # 3. Le Markdown reste accepté par le service (spec officielle, données de démo) :
    #    titres # et ## ; le titre et les lignes vides ne comptent pas.
    _, chapitres_md = importer_cours("SQL.md", "Intro\n# A\nun\n\ndeux\n## B\ntrois\n".encode("utf-8"))
    assert [(c.titre, c.nombre_lignes) for c in chapitres_md] == [("A", 2), ("B", 1)]
    # 4. Un format non supporté est refusé (l'API renverra 415).
    with pytest.raises(FormatNonSupporte):
        importer_cours("notes.docx", b"x")
    # Pourquoi un test centré sur le PDF : c'est le seul format proposé à l'écran (décision
    # de l'équipe) ; le Markdown n'est plus vérifié que par un assert de compatibilité.
