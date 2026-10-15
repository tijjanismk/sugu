import json

from django.conf import settings
from django.core.paginator import Paginator
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.listings.services import PAGE_SIZE, home_categories, latest_listings

from . import pwa


def home(request: HttpRequest) -> HttpResponse:
    """Accueil : catégories et dernières annonces, 20 par page (ticket #8).

    « Voir plus » demande la page suivante en htmx (en-tête HX-Request) : seul le partial
    « listing_page » est renvoyé, ajouté sous la grille. Sans JavaScript, c'est un lien ?page=N.
    """
    page_obj = Paginator(latest_listings(), PAGE_SIZE).get_page(request.GET.get("page"))
    if request.htmx:
        return render(request, "core/home.html#listing_page", {"page_obj": page_obj})
    return render(
        request, "core/home.html", {"categories": home_categories(), "page_obj": page_obj}
    )


def health(request: HttpRequest) -> JsonResponse:
    """Sonde de supervision : répond 200 si l'application et la base sont joignables."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


@require_GET
@cache_control(max_age=86400, public=True)
def manifest(request: HttpRequest) -> JsonResponse:
    """Manifeste de l'application (ticket #14)."""
    return JsonResponse(
        pwa.manifest(),
        content_type="application/manifest+json",
        json_dumps_params={"ensure_ascii": False},
    )


@require_GET
@cache_control(no_cache=True)
def service_worker(request: HttpRequest) -> HttpResponse:
    """Service worker, jamais mis en cache par le navigateur : une nouvelle version est vue au
    chargement suivant. Rendu sans contexte de requête : rien de personnel n'y entre."""
    context = {
        "version": pwa.cache_version(),
        "offline_url": reverse("core:offline"),
        "precache_json": json.dumps(pwa.precache_urls()),
        "static_from_cache": not settings.DEBUG,
    }
    body = render_to_string("core/sw.js", context)
    return HttpResponse(body, content_type="text/javascript; charset=utf-8")


@require_GET
def offline(request: HttpRequest) -> HttpResponse:
    """Page hors-ligne, identique pour tous (voir templates/core/offline.html). Rendue avec la
    requête pour le nonce CSP de son script ; le gabarit n'utilise rien d'autre."""
    return render(request, "core/offline.html")


@require_GET
def favicon(request: HttpRequest) -> HttpResponse:
    """Les navigateurs demandent /favicon.ico d'office : on les renvoie vers l'icône."""
    return redirect(static("img/icons/favicon.ico"), permanent=True)


# Pages privées ou sans intérêt pour un moteur de recherche (référencement, 2026-10-15). L'admin
# n'y figure pas : son adresse est secrète (ticket #15). La recherche libre reste explorable
# (ses liens mènent aux annonces) mais porte « noindex ».
ROBOTS_DISALLOW = [
    "/comptes/",
    "/messages/",
    "/favoris/",
    "/mes-annonces/",
    "/deposer/",
    "/hors-ligne/",
    "/annonce/*/contacter/",
    "/annonce/*/modifier/",
    "/annonce/*/vendue/",
    "/annonce/*/supprimer/",
    "/annonce/*/photos/",
]


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = ["User-agent: *", *(f"Disallow: {path}" for path in ROBOTS_DISALLOW), ""]
    lines.append(f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}")
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
