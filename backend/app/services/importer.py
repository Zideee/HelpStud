"""Import de cours : transforme un fichier Markdown ou PDF en chapitres avec une charge en heures."""

import io
import math
import re
from collections.abc import Callable
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

MOTS_CLES_CHAPITRE_PDF = (
    "chapitre", "partie", "module", "leçon", "lecon", "séance", "seance",
    "thème", "theme", "unité", "unite",
)
LONGUEUR_MAX_TITRE_PDF = 80
MOTIF_TITRE_MOT_CLE = re.compile(
    r"^\s*(?i:" + "|".join(MOTS_CLES_CHAPITRE_PDF) + r")\s+(\d+|[IVXLC]+)\b"
)
MOTIF_TITRE_NUMEROTE = re.compile(r"^\s*(\d{1,2}|[IVXLC]+)\.\s+\S")
# Pourquoi une liste de mots-clés : on ne sait pas comment les profs écrivent leurs PDF ;
# on ajoute un mot ici sans toucher au reste du code (décision équipe, C-03).
# Pourquoi exiger un numéro après le mot-clé : « Partie de ce code… » est une phrase, pas un titre.
# Pourquoi « \.\s » dans le motif numéroté : « 1.5 Intro » est une sous-partie, pas un chapitre.
# Pourquoi 80 caractères au plus : au-delà, c'est une phrase qui commence par un numéro.

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


def lire_titre_pdf_mot_cle(ligne: str) -> str | None:
    """Renvoie la ligne si c'est un titre « Chapitre 2 … », « Partie II … », sinon None."""
    if len(ligne.strip()) <= LONGUEUR_MAX_TITRE_PDF and MOTIF_TITRE_MOT_CLE.match(ligne):
        return ligne.strip()
    return None
    # Pourquoi garder toute la ligne comme titre : « Chapitre 1 Les bases » est plus parlant
    # dans le planning que « Les bases » seul, et on ne risque pas de couper un titre mal formé.


def lire_titre_pdf_numerote(ligne: str) -> str | None:
    """Renvoie la ligne si c'est un titre « 1. Titre » ou « II. Titre », sinon None."""
    if len(ligne.strip()) <= LONGUEUR_MAX_TITRE_PDF and MOTIF_TITRE_NUMEROTE.match(ligne):
        return ligne.strip()
    return None
    # Pourquoi une fonction séparée du mot-clé : elle ne sert que si le PDF n'a aucun
    # mot-clé, sinon les listes numérotées du cours deviendraient de faux chapitres.


def decouper_par_titres(lignes: list[str], lire_titre: Callable[[str], str | None],
                        titre_par_defaut: str) -> list[ChapitreImporte]:
    """Découpe des lignes en chapitres : chaque ligne reconnue par `lire_titre` en ouvre un."""
    chapitres: list[ChapitreImporte] = []
    titre_courant: str | None = None
    lignes_courantes: list[str] = []
    for ligne in lignes:
        titre = lire_titre(ligne)
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
    # Pourquoi `lire_titre` en paramètre : la même boucle sert au Markdown (# / ##) et au
    # PDF (mots-clés ou numéros) ; seule la façon de reconnaître un titre change.


def extraire_chapitres_markdown(texte: str, titre_par_defaut: str) -> list[ChapitreImporte]:
    """Découpe un texte Markdown en chapitres : un chapitre par titre # ou ##."""
    return decouper_par_titres(texte.splitlines(), lire_titre_markdown, titre_par_defaut)


def lire_pages_pdf(contenu: bytes) -> list[str]:
    """Texte de chaque page du PDF (chaîne vide pour une page sans texte)."""
    try:
        pages = PdfReader(io.BytesIO(contenu)).pages
        return [page.extract_text() or "" for page in pages]
    except PyPdfError as erreur:
        raise FichierVide(f"PDF illisible : {erreur}") from erreur
    # Pourquoi attraper PyPdfError : un faux PDF ne doit pas faire planter l'API (erreur 500).


def extraire_chapitres_pdf(contenu: bytes, titre_par_defaut: str) -> list[ChapitreImporte]:
    """Chapitres d'un PDF : par mots-clés, sinon par numéros « 1. », sinon une page = un chapitre."""
    textes = lire_pages_pdf(contenu)
    if compter_lignes("\n".join(textes)) == 0:
        raise FichierVide("Le PDF ne contient aucun texte (scan ou pages blanches ?)")
    toutes_les_lignes = [ligne for texte in textes for ligne in texte.splitlines()]
    for lire_titre in (lire_titre_pdf_mot_cle, lire_titre_pdf_numerote):
        if any(lire_titre(ligne) for ligne in toutes_les_lignes):
            return decouper_par_titres(toutes_les_lignes, lire_titre, titre_par_defaut)
    return [
        creer_chapitre(f"Page {numero}", texte.splitlines())
        for numero, texte in enumerate(textes, start=1)
        if compter_lignes(texte) > 0
    ]
    # Pourquoi toutes les pages bout à bout : un chapitre peut commencer au milieu d'une
    # page et continuer sur la suivante. Pourquoi cet ordre (mots-clés, puis numéros) :
    # « Chapitre 2 » est un titre sûr ; « 1. » peut être une simple liste du cours.
    # Pourquoi le repli par page : un PDF sans titre reconnu doit quand même s'importer
    # (plan B de SPEC §10).


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
