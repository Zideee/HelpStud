"""Point d'entrée de l'API HelpStud : crée l'application FastAPI."""

from fastapi import FastAPI

app = FastAPI(title="HelpStud API", version="0.1.0")
# Pourquoi une variable `app` au niveau du module : c'est ce que uvicorn cherche
# quand on lance `uvicorn app.main:app` (module app.main, objet app).


@app.get("/health")
def verifier_sante() -> dict[str, str]:
    """Indique que l'API répond."""
    return {"status": "ok"}
    # Pourquoi : une route triviale permet de vérifier que le serveur tourne
    # (front, tests, démo) avant même que la logique métier existe.
