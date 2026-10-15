from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
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


DEFAULT_DESCRIPTION = (
    "Petites annonces entre particuliers au Mali : téléphones, véhicules, maison, mode… "
    "Achetez et vendez près de chez vous sur Sugu."
)


def seo(request: HttpRequest) -> dict:
    """Référencement (2026-10-15) : adresse canonique (sans paramètres, sauf la page au-delà de
    la première), image de partage et description par défaut, balise de vérification Google
    (GOOGLE_SITE_VERIFICATION, Search Console)."""
    path = request.path
    page = request.GET.get("page", "")
    if page.isdigit() and int(page) > 1:
        path = f"{path}?page={int(page)}"
    return {
        "canonical_url": request.build_absolute_uri(path),
        "default_description": DEFAULT_DESCRIPTION,
        "default_og_image": request.build_absolute_uri(static("img/icons/icon-512.png")),
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
    }
