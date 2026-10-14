"""Application installable (ticket #14) : manifeste, service worker et page hors-ligne.

Le service worker ne met en cache que des fichiers publics : la charte (CSS, police, htmx,
icônes) et la page hors-ligne. Les pages du site ne sont jamais mises en cache : elles
contiennent des données personnelles (messages, téléphone, jeton CSRF).
"""

import hashlib
import json
from functools import cache

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.urls import reverse

PRECACHED_STATIC = [
    "css/app.css",
    "js/htmx.min.js",
    "js/pwa.js",
    "fonts/figtree-latin-wght-normal.woff2",
    "img/icons/icon-192.png",
]

# design/tokens.css : --indigo et --surface (clair), --surface (sombre).
THEME_COLOR = "#2b3c8e"
THEME_COLOR_DARK = "#11142b"
BACKGROUND_COLOR = "#f6f4ee"


def _icon(name: str, size: int, purpose: str) -> dict:
    src = static(f"img/icons/{name}")
    return {"src": src, "sizes": f"{size}x{size}", "type": "image/png", "purpose": purpose}


def manifest() -> dict:
    return {
        "id": "/",
        "name": "Sugu — petites annonces",
        "short_name": "Sugu",
        "description": "Achetez et vendez entre particuliers, près de chez vous.",
        "lang": "fr",
        "dir": "ltr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": BACKGROUND_COLOR,
        "theme_color": THEME_COLOR,
        "categories": ["shopping"],
        "icons": [
            _icon("icon-192.png", 192, "any"),
            _icon("icon-512.png", 512, "any"),
            _icon("maskable-512.png", 512, "maskable"),
        ],
        # Appui long sur l'icône (Android) : les deux gestes les plus fréquents.
        "shortcuts": [
            {"name": "Déposer une annonce", "url": reverse("listings:create")},
            {"name": "Messages", "url": reverse("messaging:inbox")},
        ],
    }


def precache_urls() -> list[str]:
    return [static(name) for name in PRECACHED_STATIC] + [reverse("core:offline")]


def _version() -> str:
    """Change dès qu'un fichier précaché change : le navigateur voit un nouveau service worker,
    l'installe et vide l'ancien cache. En production, les noms hachés suffiraient ; en
    développement, on lit le contenu."""
    digest = hashlib.sha256(json.dumps(precache_urls()).encode())
    for name in PRECACHED_STATIC:
        path = finders.find(name)
        if path:
            with open(path, "rb") as file:
                digest.update(file.read())
    return digest.hexdigest()[:12]


_cached_version = cache(_version)


def cache_version() -> str:
    return _version() if settings.DEBUG else _cached_version()
