"""Import de cours : transforme un fichier Markdown ou PDF en chapitres avec une charge en heures."""

import io
import math
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

LIGNES_PAR_HEURE = 40
PAS_ARRONDI_HEURES = 0.5
CHARGE_MINIMALE_HEURES = 1.0
# Pourquoi des constantes nommées : ce sont les règles métier de SPEC §5.1 ;
# si l'équipe les change, on les modifie à un seul endroit, visible en haut du fichier.
# (La règle est passée de « 200 mots / h » à « 40 lignes / h » après le Sprint 1 : seule
# cette constante et le comptage ont changé, grâce à ce découpage.)

PREFIXES_TITRE_MARKDOWN = ("# ", "## ")
# Pourquoi seulement # et ## : ce sont les niveaux de chapitre décidés (Q3 de SPEC.md) ;
# un ### est une sous-partie, donc du contenu du chapitre en cours.

EXTENSIONS_ACCEPTEES = (".md", ".pdf")


class FichierVide(ValueError):
    """Le fichier ne contient aucun texte exploitable."""
    # Pourquoi une exception à nous : l'API la traduira en 422 sans avoir à connaître
    # les détails de pypdf ou de l'encodage du fichier.


class FormatNonSupporte(ValueError):
    """L'extension du fichier n'est ni .md ni .pdf."""
    # Pourquoi distincte de FichierVide : l'API doit renvoyer un autre code (415).


@dataclass(frozen=True)
class ChapitreImporte:
    """Un chapitre tel qu'il sort de l'import, avant d'être enregistré en base."""

    titre: str
    nombre_lignes: int
    heures: float
    # Pourquoi frozen=True : un chapitre importé ne doit plus changer ; et deux chapitres
    # identiques sont égaux (==), ce qui rend les tests très simples à écrire.


def compter_lignes(texte: str) -> int:
    """Nombre de lignes non vides (une ligne faite seulement d'espaces ne compte pas)."""
    return sum(1 for ligne in texte.splitlines() if ligne.strip())
    # Pourquoi ignorer les lignes vides : elles séparent les paragraphes mais ne
    # contiennent rien à apprendre ; les compter gonflerait la charge.


def calculer_charge(nombre_lignes: int) -> float:
    """Heures d'étude d'un chapitre : lignes / 40, arrondi au 0,5 h supérieur, minimum 1 h."""
    heures = nombre_lignes / LIGNES_PAR_HEURE
    heures_arrondies = math.ceil(heures / PAS_ARRONDI_HEURES) * PAS_ARRONDI_HEURES
    return max(CHARGE_MINIMALE_HEURES, heures_arrondies)
    # Pourquoi arrondir au supérieur : mieux vaut surestimer le travail que le sous-estimer
    # (décision Q1 de SPEC.md). Pourquoi diviser par 0,5 puis remultiplier : ceil() arrondit
    # à l'entier, donc on compte en « demi-heures » pour arrondir au 0,5 h.


def lire_titre_markdown(ligne: str) -> str | None:
    """Renvoie le titre si la ligne est un titre de chapitre (# ou ##), sinon None."""
    for prefixe in PREFIXES_TITRE_MARKDOWN:
        if ligne.startswith(prefixe):
            return ligne[len(prefixe):].strip()
    return None
    # Pourquoi tester « # » suivi d'un espace : « ### » commence par « # » mais son
    # 2e caractère est « # », pas une espace, donc il n'est pas reconnu comme chapitre.


def creer_chapitre(titre: str, lignes: list[str]) -> ChapitreImporte:
    """Construit un chapitre à partir de son titre et des lignes de son contenu."""
    nombre_lignes = compter_lignes("\n".join(lignes))
    return ChapitreImporte(titre, nombre_lignes, calculer_charge(nombre_lignes))
    # Pourquoi une fonction à part : le même calcul sert pour chaque titre, pour le
    # dernier chapitre et pour un fichier sans titre ; on l'écrit une seule fois.


def extraire_chapitres_markdown(texte: str, titre_par_defaut: str) -> list[ChapitreImporte]:
    """Découpe un texte Markdown en chapitres : un chapitre par titre # ou ##."""
    chapitres: list[ChapitreImporte] = []
    titre_courant: str | None = None
    lignes_courantes: list[str] = []
    for ligne in texte.splitlines():
        titre = lire_titre_markdown(ligne)
        if titre is None:
            lignes_courantes.append(ligne)
            continue
        if titre_courant is not None:
            chapitres.append(creer_chapitre(titre_courant, lignes_courantes))
        titre_courant, lignes_courantes = titre, []
    if titre_courant is None:
        return [creer_chapitre(titre_par_defaut, lignes_courantes)]
    chapitres.append(creer_chapitre(titre_courant, lignes_courantes))
    return chapitres
    # Pourquoi ce parcours ligne par ligne : on accumule le contenu jusqu'au titre suivant,
    # puis on « ferme » le chapitre. Le texte avant le 1er titre est accumulé puis jeté
    # au 1er titre (lignes_courantes = []) ; sans aucun titre, il devient le chapitre unique.


def extraire_chapitres_pdf(contenu: bytes, titre_par_defaut: str) -> list[ChapitreImporte]:
    """Un chapitre par page non vide du PDF, nommé « Page N »."""
    try:
        pages = PdfReader(io.BytesIO(contenu)).pages
        textes = [page.extract_text() or "" for page in pages]
    except PyPdfError as erreur:
        raise FichierVide(f"PDF illisible : {erreur}") from erreur
    chapitres = [
        creer_chapitre(f"Page {numero}", texte.splitlines())
        for numero, texte in enumerate(textes, start=1)
        if compter_lignes(texte) > 0
    ]
    if not chapitres:
        raise FichierVide("Le PDF ne contient aucun texte (scan ou pages blanches ?)")
    return chapitres
    # Pourquoi une page = un chapitre : un PDF n'a pas de « # » ; c'est la version simple
    # du P0, la détection des titres « Chapitre N » vient en P1-01 (titre_par_defaut y servira).
    # Pourquoi attraper PyPdfError : un faux PDF ne doit pas faire planter l'API (erreur 500).


def importer_cours(nom_fichier: str, contenu: bytes) -> tuple[str, list[ChapitreImporte]]:
    """Renvoie (nom du cours, chapitres) selon l'extension du fichier."""
    chemin = Path(nom_fichier)
    extension = chemin.suffix.lower()
    if extension not in EXTENSIONS_ACCEPTEES:
        raise FormatNonSupporte(f"Format {extension or 'inconnu'} non supporté : .md ou .pdf")
    if extension == ".pdf":
        return chemin.stem, extraire_chapitres_pdf(contenu, chemin.stem)
    texte = contenu.decode("utf-8-sig", errors="replace")
    if compter_lignes(texte) == 0:
        raise FichierVide("Le fichier Markdown est vide")
    return chemin.stem, extraire_chapitres_markdown(texte, chemin.stem)
    # Pourquoi tester le format en premier : un .docx vide doit dire « mauvais format »
    # (415), pas « fichier vide ». Pourquoi utf-8-sig : le Bloc-notes de Windows ajoute
    # parfois un caractère invisible (BOM) au début, qui serait collé au premier titre.
