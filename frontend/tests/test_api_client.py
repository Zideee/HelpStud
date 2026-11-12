"""Tests 9 et 10 (front) : api_client.py, testé avec un faux serveur (sans lancer le back)."""

from datetime import date

import httpx
import pytest

import api_client


def brancher_faux_serveur(monkeypatch: pytest.MonkeyPatch, repondre) -> list[httpx.Request]:
    """Remplace le vrai serveur par la fonction `repondre` ; renvoie la liste des requêtes reçues."""
    recues: list[httpx.Request] = []

    def traiter(requete: httpx.Request) -> httpx.Response:
        recues.append(requete)
        return repondre(requete)

    monkeypatch.setattr(api_client, "creer_client", lambda: httpx.Client(
        base_url="http://faux-serveur", transport=httpx.MockTransport(traiter)))
    return recues
    # Pourquoi MockTransport : httpx envoie les requêtes à notre fonction au lieu du réseau ;
    # on teste le client seul, en une fraction de seconde, sans uvicorn ni base de données.


def test_client_appelle_les_routes_du_contrat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 9 : chaque fonction appelle la bonne méthode et la bonne route du contrat (CA5.4)."""
    recues = brancher_faux_serveur(monkeypatch, lambda requete: httpx.Response(
        204 if requete.method == "DELETE" else 200, json=None if requete.method == "DELETE" else {}))

    api_client.lister_cours()
    api_client.importer_cours("cours.pdf", b"%PDF-factice", "high")
    api_client.modifier_cours(3, priorite="low")
    api_client.lister_echeances()
    api_client.creer_echeance(3, "Examen", "exam", date(2026, 12, 18), 60)
    api_client.supprimer_echeance(5)
    api_client.lire_disponibilites()
    api_client.enregistrer_disponibilites(60, {"monday": ["18:00-20:00"]})
    api_client.generer_planning("2026-W47")
    api_client.lire_planning("2026-W47")
    api_client.marquer_session(7, True)
    api_client.telecharger_ics()

    assert [(r.method, r.url.path) for r in recues] == [
        ("GET", "/courses"), ("POST", "/courses"), ("PATCH", "/courses/3"),
        ("GET", "/deadlines"), ("POST", "/deadlines"), ("DELETE", "/deadlines/5"),
        ("GET", "/availability"), ("PUT", "/availability"),
        ("POST", "/plan/generate"), ("GET", "/plan"), ("PATCH", "/sessions/7"), ("GET", "/plan.ics"),
    ]
    # Les corps envoyés respectent le contrat (noms de champs en anglais, date ISO).
    assert b'name="priority"' in recues[1].content and b"high" in recues[1].content
    assert b"category" not in recues[1].content  # la catégorie n'est plus envoyée (CA2.7)
    assert recues[4].read() == (b'{"course_id":3,"title":"Examen","type":"exam",'
                                b'"date":"2026-12-18","weight":60}')
    assert recues[9].url.params["week"] == "2026-W47"
    # Pourquoi tout vérifier dans un seul test : c'est la « table de correspondance »
    # fonction → route ; si quelqu'un casse une route côté front, ce test le voit.


def test_client_erreurs_lisibles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 10 : 422, 404 ou back éteint → ErreurApi avec un message lisible, jamais une trace Python."""
    # 1. Erreur de validation FastAPI (422) : on garde le message, pas la structure technique.
    brancher_faux_serveur(monkeypatch, lambda r: httpx.Response(
        422, json={"detail": [{"msg": "Value error, La date de l'échéance est déjà passée"}]}))
    with pytest.raises(api_client.ErreurApi, match="déjà passée") as erreur:
        api_client.creer_echeance(1, "X", "exam", date(2020, 1, 1), 10)
    assert erreur.value.code == 422

    # 2. Erreur simple (404) : le detail est repris tel quel.
    brancher_faux_serveur(monkeypatch, lambda r: httpx.Response(404, json={"detail": "Cours inconnu"}))
    with pytest.raises(api_client.ErreurApi, match="Cours inconnu"):
        api_client.modifier_cours(999, priorite="low")
    assert api_client.lire_disponibilites() is None  # 404 ici = « rien de saisi », pas une erreur

    # 3. Back éteint : un message qui dit quoi faire.
    def back_eteint(requete: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connexion refusée", request=requete)
    brancher_faux_serveur(monkeypatch, back_eteint)
    with pytest.raises(api_client.ErreurApi, match="API injoignable"):
        api_client.lister_cours()
    # Pourquoi : la page Streamlit affichera erreur.message dans st.error ; l'étudiant doit
    # comprendre quoi faire, pas lire une « Traceback ».
