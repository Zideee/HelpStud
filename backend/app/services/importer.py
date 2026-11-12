"""Import de cours : transforme un fichier Markdown ou PDF en chapitres avec une charge en heures."""

import math

MOTS_PAR_HEURE = 200
PAS_ARRONDI_HEURES = 0.5
CHARGE_MINIMALE_HEURES = 1.0
# Pourquoi des constantes nommées : ce sont les règles métier de SPEC §5.1 ;
# si l'équipe les change, on les modifie à un seul endroit, visible en haut du fichier.


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
