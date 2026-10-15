"""Bannière « Installer l'application » (ticket #14, ajout du 2026-10-15)."""

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_banniere_cachee_par_defaut_sur_laccueil(client):
    html = client.get(reverse("core:home")).content.decode()

    # Cachée tant que le script ne sait pas que l'installation est possible : jamais affichée
    # sans JavaScript, ni dans l'application installée.
    assert "data-install-banner" in html
    assert 'class="sg-alert sg-alert--info hidden"' in html
    assert "js/install.js" in html
    assert "Touchez le bouton Partager" in html  # marche à suivre iPhone, elle aussi cachée


def test_pas_de_banniere_ailleurs(client):
    html = client.get(reverse("listings:search")).content.decode()

    assert "data-install-banner" not in html
    assert "js/install.js" not in html


def test_script_dinstallation():
    path = finders.find("js/install.js")
    script = open(path, encoding="utf-8").read()

    assert "beforeinstallprompt" in script
    assert "(display-mode: standalone)" in script  # rien dans l'application installée
    assert "LATER_DAYS = 30" in script
    assert "event.preventDefault()" in script  # notre bannière plutôt que la mini-barre
