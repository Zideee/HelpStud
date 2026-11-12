"""Base SQLite : chemin, création des tables et connexion par requête."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from typing import Annotated

from fastapi import Depends

CHEMIN_PAR_DEFAUT = "helpstud.db"
# Pourquoi un fichier à la racine : simple à trouver, et ignoré par Git (*.db dans .gitignore).

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low'))
);
CREATE TABLE IF NOT EXISTS chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  title TEXT NOT NULL,
  hours REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS deadlines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('exam', 'assignment')),
  date TEXT NOT NULL,
  weight INTEGER NOT NULL CHECK (weight BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS availability (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  session_minutes INTEGER NOT NULL,
  slots_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0
);
"""
# Pourquoi les noms de colonnes du contrat (anglais) : la base et le JSON parlent la même
# langue, donc pas d'erreur de traduction entre les deux. Les CHECK sont un 2e filet de
# sécurité derrière Pydantic. availability a une seule ligne (id = 1) : un seul utilisateur.
# Les dates sont du texte ISO 8601 car SQLite n'a pas de vrai type date.
# Pas de colonne « category » : elle est calculée à partir des échéances (SPEC §5.4),
# donc elle ne peut jamais contredire les dates saisies.


def chemin_base() -> str:
    """Chemin de la base : variable d'environnement HELPSTUD_DB, sinon helpstud.db."""
    return os.environ.get("HELPSTUD_DB", CHEMIN_PAR_DEFAUT)
    # Pourquoi une variable d'environnement : les tests pointent vers une base temporaire
    # sans toucher à la vraie, et sans modifier le code.


def ouvrir_connexion(chemin: str) -> sqlite3.Connection:
    """Ouvre une connexion SQLite configurée (lignes nommées, clés étrangères actives)."""
    connexion = sqlite3.connect(chemin, check_same_thread=False)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    return connexion
    # Pourquoi check_same_thread=False : FastAPI peut ouvrir la connexion dans un thread et
    # exécuter la route dans un autre ; c'est sans risque ici car chaque requête a la sienne.
    # Pourquoi sqlite3.Row : on lit ligne["name"] au lieu de ligne[1], plus lisible.
    # Pourquoi le PRAGMA : SQLite n'applique les clés étrangères que si on le lui demande.


def initialiser_base(chemin: str) -> None:
    """Crée les tables si elles n'existent pas."""
    with closing(ouvrir_connexion(chemin)) as connexion:
        connexion.executescript(SCHEMA)
        connexion.commit()
    # Pourquoi « IF NOT EXISTS » : on peut relancer le serveur sans perdre les données.


def obtenir_connexion() -> Iterator[sqlite3.Connection]:
    """Dépendance FastAPI : ouvre une connexion par requête et la ferme après."""
    connexion = ouvrir_connexion(chemin_base())
    try:
        yield connexion
        connexion.commit()
    except Exception:
        connexion.rollback()
        raise
    finally:
        connexion.close()
    # Pourquoi commit à la fin seulement : si la route échoue au milieu (ex. 404 après une
    # insertion), rollback annule tout ; la base ne reste jamais à moitié modifiée.


Connexion = Annotated[sqlite3.Connection, Depends(obtenir_connexion)]
# Pourquoi cet alias : chaque route écrit simplement `connexion: Connexion` pour recevoir
# sa connexion, au lieu de répéter `Depends(obtenir_connexion)` partout.
