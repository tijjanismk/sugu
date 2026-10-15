"""Remontée des erreurs de production vers Sentry (ticket #17), sans donnée personnelle.

Activée seulement si SENTRY_DSN est défini (config/settings/prod.py). Rien côté navigateur :
pas de script tiers, la CSP ne change pas. Ce qui ne part jamais :
- l'utilisateur, son IP, ses cookies (`send_default_pii=False`) ;
- le corps des requêtes : mots de passe, messages, annonces (`max_request_body_size`) ;
- les variables locales des fonctions, qui contiennent les mêmes données ;
- les jetons des liens de confirmation d'email, de mot de passe oublié et de retour de Google,
  effacés des adresses par `scrub_event` (comme le journal d'accès absent, docs/security.md).
"""

import re

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

FILTERED = "[Filtered]"
# Chemins à jeton (apps/accounts/urls.py) et paramètres de retour OAuth.
TOKEN_PATHS = re.compile(
    r"(/comptes/email/confirmation/|/comptes/mot-de-passe/oublie/)(?!envoye/|termine/)[^/?#\s]+"
)
TOKEN_PARAMS = re.compile(r"\b(code|state|key|token)=[^&#\s]*", re.IGNORECASE)


def scrub(text: str) -> str:
    text = TOKEN_PATHS.sub(rf"\g<1>{FILTERED}", text)
    return TOKEN_PARAMS.sub(rf"\g<1>={FILTERED}", text)


def scrub_event(event: dict, hint: dict) -> dict:
    request = event.get("request") or {}
    for field in ("url", "query_string"):
        if isinstance(request.get(field), str):
            request[field] = scrub(request[field])
    headers = request.get("headers") or {}
    for name, value in headers.items():
        if isinstance(value, str):
            headers[name] = scrub(value)
    for crumb in (event.get("breadcrumbs") or {}).get("values", []):
        if isinstance(crumb.get("message"), str):
            crumb["message"] = scrub(crumb["message"])
        for key, value in (crumb.get("data") or {}).items():
            if isinstance(value, str):
                crumb["data"][key] = scrub(value)
    return event


def options(dsn: str, environment: str) -> dict:
    return {
        "dsn": dsn,
        "environment": environment,
        "integrations": [DjangoIntegration(transaction_style="url")],
        "send_default_pii": False,
        "max_request_body_size": "never",
        "include_local_variables": False,
        "traces_sample_rate": 0,  # erreurs seulement : l'offre gratuite suffit
        "before_send": scrub_event,
        "before_send_transaction": scrub_event,
    }


def init(dsn: str, environment: str) -> None:
    sentry_sdk.init(**options(dsn, environment))
