"""Vérifications de mise en production (`manage.py check --deploy`, ticket #15)."""

from django.conf import settings
from django.core.checks import Tags, Warning, register

GUESSABLE_ADMIN_URLS = {"admin", "administration", "django-admin", "backoffice", "gestion"}
ADMIN_URL_MIN_LENGTH = 16


@register(Tags.security, deploy=True)
def check_admin_url(app_configs, **kwargs):
    """L'admin ne doit pas être à une adresse devinable (docs/security.md)."""
    url = settings.ADMIN_URL
    if url.strip("/").lower() in GUESSABLE_ADMIN_URLS or len(url) < ADMIN_URL_MIN_LENGTH:
        return [
            Warning(
                "L'admin est à une adresse devinable.",
                hint="ADMIN_URL=<16 caractères aléatoires au moins>/ dans l'environnement, ex. "
                "`python -c \"import secrets; print(secrets.token_urlsafe(16) + '/')\"`.",
                id="sugu.W001",
            )
        ]
    if not url.endswith("/") or url.startswith("/"):
        return [
            Warning("ADMIN_URL doit finir par « / » et ne pas commencer par « / ».", id="sugu.W002")
        ]
    return []
