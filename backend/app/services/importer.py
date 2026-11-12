"""Import de cours : transforme un fichier Markdown ou PDF en chapitres avec une charge en heures."""

import math
from dataclasses import dataclass

MOTS_PAR_HEURE = 200
PAS_ARRONDI_HEURES = 0.5
CHARGE_MINIMALE_HEURES = 1.0
# Pourquoi des constantes nommées : ce sont les règles métier de SPEC §5.1 ;
# si l'équipe les change, on les modifie à un seul endroit, visible en haut du fichier.

PREFIXES_TITRE_MARKDOWN = ("# ", "## ")
# Pourquoi seulement # et ## : ce sont les niveaux de chapitre décidés (Q3 de SPEC.md) ;
# un ### est une sous-partie, donc du contenu du chapitre en cours.


@dataclass(frozen=True)
class ChapitreImporte:
    """Un chapitre tel qu'il sort de l'import, avant d'être enregistré en base."""

    titre: str
    nombre_mots: int
    heures: float
    # Pourquoi frozen=True : un chapitre importé ne doit plus changer ; et deux chapitres
    # identiques sont égaux (==), ce qui rend les tests très simples à écrire.


def compter_mots(texte: str) -> int:
    """Nombre de mots d'un texte (séparés par des espaces)."""
    return len(texte.split())
    # Pourquoi split() sans argument : il coupe sur tous les blancs (espaces, tabulations,
    # retours à la ligne) et ignore les blancs répétés, donc pas de « mots vides ».


def calculer_charge(nombre_mots: int) -> float:
    """Heures d'étude d'un chapitre : mots / 200, arrondi au 0,5 h supérieur, minimum 1 h."""
    heures = nombre_mots / MOTS_PAR_HEURE
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
    nombre_mots = compter_mots("\n".join(lignes))
    return ChapitreImporte(titre, nombre_mots, calculer_charge(nombre_mots))
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
