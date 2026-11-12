"""Point d'entrée de l'API HelpStud : crée l'application FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import chemin_base, initialiser_base


@asynccontextmanager
async def cycle_de_vie(application: FastAPI) -> AsyncIterator[None]:
    """Au démarrage du serveur : crée les tables si besoin."""
    initialiser_base(chemin_base())
    yield
    # Pourquoi au démarrage et pas à l'import du module : le chemin de la base est lu au
    # moment où le serveur démarre, donc les tests peuvent le changer juste avant.


app = FastAPI(title="HelpStud API", version="0.1.0", lifespan=cycle_de_vie)
# Pourquoi une variable `app` au niveau du module : c'est ce que uvicorn cherche
# quand on lance `uvicorn app.main:app` (module app.main, objet app).


@app.get("/health")
def verifier_sante() -> dict[str, str]:
    """Indique que l'API répond."""
    return {"status": "ok"}
    # Pourquoi : une route triviale permet de vérifier que le serveur tourne
    # (front, tests, démo) avant même que la logique métier existe.
