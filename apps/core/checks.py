"""Vérifications de mise en production (`manage.py check --deploy`, tickets #15 et #17)."""

from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.template.loader import get_template

from . import backups

GUESSABLE_ADMIN_URLS = {"admin", "administration", "django-admin", "backoffice", "gestion"}
ADMIN_URL_MIN_LENGTH = 16
TO_COMPLETE = "[À COMPLÉTER"
LEGAL_TEMPLATES = [
    "legal/_publisher.html",
    "legal/legal_notice.html",
    "legal/privacy.html",
    "legal/about.html",
]


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


@register(Tags.security, deploy=True)
def check_legal_pages(app_configs, **kwargs):
    """Pages légales encore à compléter par l'éditeur du site (ticket #17, templates/legal/)."""
    unfinished = [
        name for name in LEGAL_TEMPLATES if TO_COMPLETE in get_template(name).template.source
    ]
    if not unfinished:
        return []
    return [
        Warning(
            "Pages légales à compléter : " + ", ".join(unfinished) + ".",
            hint=f"Remplacer chaque « {TO_COMPLETE} … » par l'information demandée "
            "(docs/runbook.md, « Pages légales »).",
            id="sugu.W003",
        )
    ]


@register(Tags.security, deploy=True)
def check_backups(app_configs, **kwargs):
    """Sans bucket de sauvegarde, la base n'existe que sur le serveur (ticket #17)."""
    if backups.is_configured():
        return []
    return [Warning(backups.NOT_CONFIGURED, id="sugu.W004")]
