"""Gabarit de base (ticket #4) : navigation, partial htmx, pages d'erreur."""

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_l_accueil_renvoie_la_page_complete_sans_htmx(client):
    response = client.get(reverse("core:home"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" in html
    assert 'id="recent-title"' in html
    assert "htmx.min.js" in html


def test_l_accueil_renvoie_seulement_le_partial_avec_htmx(client):
    response = client.get(reverse("core:home"), headers={"HX-Request": "true"})

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert "sg-bottomnav" not in html


def test_la_navigation_marque_la_page_courante(client):
    html = client.get(reverse("core:home")).content.decode()

    assert '<nav class="sg-bottomnav" aria-label="Navigation principale">' in html
    accueil = html.split('class="sg-bottomnav__item" href="/"')[1].split(">")[0]
    assert 'aria-current="page"' in accueil
    recherche = html.split('class="sg-bottomnav__item" href="/recherche/"')[1].split(">")[0]
    assert "aria-current" not in recherche


def test_les_pages_de_compte_sont_des_flux_sans_barre_basse(client):
    html = client.get(reverse("account_login")).content.decode()

    assert "sg-bottomnav" not in html
    assert "has-bottomnav" not in html


def test_le_jeton_csrf_est_transmis_aux_requetes_htmx(client):
    html = client.get(reverse("core:home")).content.decode()

    assert 'hx-headers=\'{"X-CSRFToken": "' in html


def test_la_barre_du_haut_propose_la_connexion_ou_la_deconnexion(client):
    assert "Se connecter" in client.get(reverse("core:home")).content.decode()

    client.force_login(UserFactory())
    html = client.get(reverse("core:home")).content.decode()
    assert "Se déconnecter" in html
    assert f'action="{reverse("account_logout")}"' in html


def test_page_404_du_site(client):
    response = client.get("/cette-page-n-existe-pas/")

    assert response.status_code == 404
    html = response.content.decode()
    assert "Cette page n'existe pas" in html
    assert "Retour à l'accueil" in html


def test_la_page_500_se_rend_sans_contexte():
    # handler500 rend le gabarit sans requête ni context processor.
    html = render_to_string("500.html")

    assert "Le site a un souci" in html
    assert "sg-bottomnav" not in html
