from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse

# Destinations de premier niveau (design/components/BottomNav). Tant que la page n'existe pas
# (ticket indiqué), le lien pointe vers son adresse prévue et tombe sur la page 404.
NAV_ITEMS = [
    ("home", "Accueil", "core:home", "/"),
    ("search", "Recherche", "listings:search", "/recherche/"),  # ticket #9
    ("post", "Déposer", "listings:create", "/deposer/"),  # ticket #7
    ("favorites", "Favoris", "favorites:list", "/favoris/"),  # ticket #11
    ("messages", "Messages", "messaging:inbox", "/messages/"),  # ticket #12
]


def _href(url_name: str, fallback: str) -> str:
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return fallback


def navigation(request: HttpRequest) -> dict:
    """Liens de la barre de navigation (page courante marquée `current`) et URL de recherche."""
    items = []
    for key, label, url_name, fallback in NAV_ITEMS:
        href = _href(url_name, fallback)
        current = request.path == href if href == "/" else request.path.startswith(href)
        items.append({"key": key, "label": label, "href": href, "current": current})
    search_url = next(item["href"] for item in items if item["key"] == "search")
    return {"nav_items": items, "search_url": search_url}
