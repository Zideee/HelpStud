"""Génère les cours de démo en PDF (sample_data/*.pdf) à partir des cours Markdown (C-04).

Lancement, depuis la racine du dépôt, venv activé :
    python scripts/generer_pdf_demo.py
"""

import textwrap
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

DOSSIER_DEMO = Path(__file__).parents[1] / "sample_data"
COURS_DEMO = ("SQL", "Python", "Statistiques")
LARGEUR_LIGNE = 90            # caractères par ligne (décision C-04)
TAILLE_POLICE = 10
INTERLIGNE = 14               # points entre deux lignes
LARGEUR_PAGE, HAUTEUR_PAGE = 612, 792   # format Letter, en points
MARGE_GAUCHE, MARGE_HAUT = 50, 50
PREFIXES_TITRE = ("# ", "## ")
# Pourquoi des constantes : la mise en page se règle ici, sans chercher dans le code.


def lire_chapitres(texte_markdown: str) -> list[tuple[str, list[str]]]:
    """Découpe le Markdown en (titre, lignes du contenu), un élément par titre # ou ##."""
    chapitres: list[tuple[str, list[str]]] = []
    for ligne in texte_markdown.splitlines():
        prefixe = next((p for p in PREFIXES_TITRE if ligne.startswith(p)), None)
        if prefixe is not None:
            chapitres.append((ligne[len(prefixe):].strip(), []))
        elif chapitres:
            chapitres[-1][1].append(ligne)
    return chapitres
    # Pourquoi ne pas réutiliser importer.py : ce script est un outil de l'équipe, pas
    # le produit ; il reste indépendant du back (il n'a besoin que de pypdf).


def couper_lignes(lignes: list[str]) -> list[str]:
    """Coupe chaque ligne en morceaux de LARGEUR_LIGNE caractères au plus (sans couper les mots)."""
    resultat: list[str] = []
    for ligne in lignes:
        resultat.extend(textwrap.wrap(ligne, LARGEUR_LIGNE) or [""])
    return resultat
    # Pourquoi « or [""] » : textwrap renvoie [] pour une ligne vide ; on la garde pour
    # conserver les séparations entre paragraphes (elles ne comptent pas dans la charge).


def echapper_pdf(texte: str) -> str:
    """Échappe les caractères spéciaux d'une chaîne PDF : \\ ( )."""
    return texte.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Pourquoi : dans un PDF, le texte s'écrit entre parenthèses ; une « ( » du cours
    # fermerait la chaîne trop tôt et casserait le fichier.


def ajouter_page(redacteur: PdfWriter, lignes: list[str]) -> None:
    """Ajoute une page qui affiche les lignes, de haut en bas, en Helvetica."""
    police = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    page = redacteur.add_blank_page(width=LARGEUR_PAGE, height=HAUTEUR_PAGE)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): police})})
    texte = " T* ".join(f"({echapper_pdf(ligne)}) Tj" for ligne in lignes)
    contenu = DecodedStreamObject()
    contenu.set_data((f"BT /F1 {TAILLE_POLICE} Tf {INTERLIGNE} TL "
                      f"{MARGE_GAUCHE} {HAUTEUR_PAGE - MARGE_HAUT} Td {texte} ET").encode("cp1252"))
    page.replace_contents(contenu)
    # Pourquoi WinAnsiEncoding + cp1252 : c'est l'encodage standard des PDF pour les
    # accents français (é, à, ç) et le tiret « — ». « T* » = passer à la ligne suivante.


def generer_pdf(chemin_markdown: Path, chemin_pdf: Path) -> int:
    """Écrit le PDF d'un cours : une page par chapitre, 1re ligne « Chapitre N — Titre »."""
    chapitres = lire_chapitres(chemin_markdown.read_text(encoding="utf-8"))
    redacteur = PdfWriter()
    for numero, (titre, lignes) in enumerate(chapitres, start=1):
        ajouter_page(redacteur, [f"Chapitre {numero} — {titre}"] + couper_lignes(lignes))
    with chemin_pdf.open("wb") as fichier:
        redacteur.write(fichier)
    return len(chapitres)
    # Pourquoi « Chapitre N — Titre » en 1re ligne : c'est ce que l'import (C-03) reconnaît,
    # donc l'écran affichera les vrais titres. Limite connue : un chapitre de plus de
    # ~50 lignes déborderait de sa page ; les cours de démo en font moins de 25.


def main() -> None:
    """Génère les 3 PDF de démo à côté des fichiers Markdown."""
    for nom in COURS_DEMO:
        nombre = generer_pdf(DOSSIER_DEMO / f"{nom}.md", DOSSIER_DEMO / f"{nom}.pdf")
        print(f"{nom}.pdf : {nombre} chapitres")


if __name__ == "__main__":
    main()
