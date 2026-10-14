"""Limitation de débit des actions du site (docs/security.md, « Débit et robots »).

S'appuie sur la limitation d'allauth (compteurs dans le cache, réglage ACCOUNT_RATE_LIMITS) ;
allauth annonce que cette API publique pourrait disparaître : seul ce fichier serait à changer.
"""

from allauth.core import ratelimit
from django.http import HttpRequest, HttpResponse


def consume(request: HttpRequest, action: str, *, dry_run: bool = False) -> bool:
    """Décompte une tentative de `action` pour l'utilisateur connecté (sinon l'IP).
    Renvoie False si la limite est atteinte. `dry_run` vérifie sans décompter."""
    user = request.user if request.user.is_authenticated else None
    return ratelimit.consume(request, action=action, user=user, dry_run=dry_run)


def too_many_requests(request: HttpRequest) -> HttpResponse:
    """Réponse 429 avec la page du site (templates/429.html)."""
    return ratelimit.respond_429(request)
