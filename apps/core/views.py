from django.core.paginator import Paginator
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.listings.services import PAGE_SIZE, home_categories, latest_listings


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
