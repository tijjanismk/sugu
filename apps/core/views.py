from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Page d'accueil provisoire ; le ticket #8 y met la grille d'annonces."""
    return render(request, "core/home.html")


def health(request: HttpRequest) -> JsonResponse:
    """Sonde de supervision : répond 200 si l'application et la base sont joignables."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
