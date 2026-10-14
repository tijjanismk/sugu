"""Application installable (ticket #14) : manifeste, icônes, service worker, page hors-ligne."""

import json

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.core import pwa

pytestmark = pytest.mark.django_db


def _manifest(client):
    response = client.get(reverse("core:manifest"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"
    return json.loads(response.content)


def test_manifeste_installable(client):
    """Critères d'installation de Chrome : nom, adresse de départ, affichage autonome, icônes
    192 et 512 px en PNG."""
    data = _manifest(client)

    assert data["name"] and data["short_name"] == "Sugu"
    assert data["start_url"] == "/"
    assert data["display"] == "standalone"
    assert data["lang"] == "fr"
    sizes = {icon["sizes"] for icon in data["icons"] if icon["purpose"] == "any"}
    assert {"192x192", "512x512"} <= sizes
    assert any(icon["purpose"] == "maskable" for icon in data["icons"])


@pytest.mark.parametrize(
    ("name", "size"),
    [
        ("icon-192.png", 192),
        ("icon-512.png", 512),
        ("maskable-512.png", 512),
        ("apple-touch-icon.png", 180),
    ],
)
def test_icones_aux_bonnes_dimensions(name, size):
    path = finders.find(f"img/icons/{name}")

    assert path, name
    with Image.open(path) as image:
        assert image.size == (size, size)
        assert image.format == "PNG"


def test_icones_du_manifeste_existent(client):
    for icon in _manifest(client)["icons"]:
        name = icon["src"].removeprefix("/static/")
        assert finders.find(name), icon["src"]


def test_raccourcis_vers_depot_et_messages(client):
    urls = {shortcut["url"] for shortcut in _manifest(client)["shortcuts"]}

    assert urls == {reverse("listings:create"), reverse("messaging:inbox")}


def test_service_worker_a_la_racine_jamais_en_cache(client):
    response = client.get(reverse("core:service_worker"))

    assert reverse("core:service_worker") == "/sw.js"  # portée : tout le site
    assert response["Content-Type"].startswith("text/javascript")
    assert "no-cache" in response["Cache-Control"]
    body = response.content.decode()
    assert f'const OFFLINE_URL = "{reverse("core:offline")}";' in body
    for url in pwa.precache_urls():
        assert f'"{url}"' in body
    assert f'const VERSION = "{pwa.cache_version()}";' in body


def test_le_service_worker_ne_met_jamais_les_pages_en_cache(client):
    body = client.get(reverse("core:service_worker")).content.decode()

    # Pages : réseau, sinon la page hors-ligne ; seules les URL précachées sont lues du cache.
    assert 'request.mode === "navigate"' in body
    assert "fetch(request).catch(() => caches.match(OFFLINE_URL))" in body
    assert "cache.put" not in body
    # Seule la page hors-ligne est obligatoire à l'installation.
    assert "url === OFFLINE_URL ? cache.add(url) : cache.add(url).catch(() => {})" in body
    assert all(
        url.startswith("/static/") or url == reverse("core:offline") for url in pwa.precache_urls()
    )


def test_version_change_quand_un_fichier_change(settings, tmp_path, monkeypatch):
    settings.DEBUG = True
    before = pwa.cache_version()
    css = tmp_path / "app.css"
    css.write_text("body{}")
    real_find = finders.find
    monkeypatch.setattr(
        finders, "find", lambda name: str(css) if name == "css/app.css" else real_find(name)
    )

    assert pwa.cache_version() != before


def test_statiques_du_cache_seulement_hors_developpement(client, settings):
    settings.DEBUG = False
    assert "const STATIC_FROM_CACHE = true;" in client.get("/sw.js").content.decode()
    settings.DEBUG = True
    assert "const STATIC_FROM_CACHE = false;" in client.get("/sw.js").content.decode()


def test_page_hors_ligne_identique_pour_tous(client):
    client.force_login(UserFactory(display_name="Aminata Koné"))

    response = client.get(reverse("core:offline"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "Pas de connexion" in html
    assert "Aminata" not in html
    assert "csrf" not in html.lower()
    assert "Set-Cookie" not in str(response.headers)
    assert 'href=""' in html  # « Réessayer » recharge l'adresse demandée


def test_chaque_page_declare_le_manifeste_et_le_service_worker(client):
    html = client.get(reverse("core:home")).content.decode()

    assert f'<link rel="manifest" href="{reverse("core:manifest")}">' in html
    assert 'name="theme-color"' in html
    assert 'rel="apple-touch-icon"' in html
    assert f'data-sw="{reverse("core:service_worker")}"' in html


def test_favicon_a_la_racine(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 301
    assert response.url.endswith("img/icons/favicon.ico")


@pytest.mark.parametrize("name", ["core:manifest", "core:service_worker", "core:offline"])
def test_en_lecture_seule(client, name):
    assert client.post(reverse(name)).status_code == 405


@pytest.mark.parametrize("name", ["js/pwa.js", "js/htmx.min.js"])
def test_statiques_servis_sans_collectstatic(client, name):
    """Le job e2e (CI) lance le serveur avec les réglages de test, sans collectstatic : sans
    fichiers statiques, le service worker ne s'enregistrerait pas."""
    response = client.get(f"/static/{name}")

    assert response.status_code == 200
