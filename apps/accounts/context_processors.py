from django.conf import settings
from django.http import HttpRequest


def auth_options(request: HttpRequest) -> dict:
    """`google_login` : bouton « Continuer avec Google », seulement si les identifiants OAuth
    sont configurés (ticket #3, ADR 0002)."""
    return {"google_login": settings.GOOGLE_LOGIN_ENABLED}
