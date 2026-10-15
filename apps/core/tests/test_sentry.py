"""Erreurs vers Sentry (ticket #17) : aucune donnée personnelle ni jeton dans les rapports."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.urls import reverse

from apps.core import sentry

ROOT = Path(__file__).resolve().parents[3]


def test_les_jetons_des_liens_sont_effaces():
    confirm = reverse("account_confirm_email", args=["MQ:1tAbCd:secret-de-confirmation"])
    reset = reverse("account_reset_password_from_key", kwargs={"uidb36": "4", "key": "cle-secrete"})
    event = {
        "request": {
            "url": f"https://sugu.ml{confirm}",
            "query_string": "code=4/0AeanS0b&state=xyz&page=2",
            "headers": {"Referer": f"https://sugu.ml{reset}", "Accept": "text/html"},
        },
        "breadcrumbs": {"values": [{"message": f"GET {reset}", "data": {"url": confirm}}]},
    }

    scrubbed = sentry.scrub_event(event, {})

    text = repr(scrubbed)
    for secret in ("secret-de-confirmation", "cle-secrete", "4/0AeanS0b", "xyz"):
        assert secret not in text
    assert scrubbed["request"]["url"] == "https://sugu.ml/comptes/email/confirmation/[Filtered]/"
    assert "page=2" in scrubbed["request"]["query_string"]
    assert scrubbed["request"]["headers"]["Accept"] == "text/html"


def test_les_adresses_sans_jeton_restent_lisibles():
    for name in (
        "account_email_verification_sent",
        "account_reset_password",
        "account_reset_password_done",
        "account_reset_password_from_key_done",
    ):
        url = reverse(name)
        assert sentry.scrub(url) == url


def test_aucune_donnee_personnelle_envoyee():
    options = sentry.options("https://cle@o0.ingest.sentry.io/0", "production")

    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["include_local_variables"] is False
    assert options["traces_sample_rate"] == 0
    assert options["before_send"] is sentry.scrub_event


def test_active_en_production_avec_un_dsn():
    """Les réglages de production démarrent Sentry quand SENTRY_DSN est défini (rien n'est
    envoyé : aucune erreur n'est levée)."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "SECRET_KEY": secrets.token_urlsafe(50),
        "ALLOWED_HOSTS": "sugu.ml",
        "DATABASE_URL": "postgres://sugu:secret@db:5432/sugu",
        "EMAIL_URL": "smtp://localhost",
        "ADMIN_URL": secrets.token_urlsafe(16) + "/",
        "SENTRY_DSN": "https://cle@o0.ingest.sentry.io/0",
    }
    code = (
        "import django, sentry_sdk; django.setup(); o = sentry_sdk.get_client().options; "
        "print(o['dsn'], o['send_default_pii'], o['environment'])"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60
    )

    assert result.stdout.split() == ["https://cle@o0.ingest.sentry.io/0", "False", "production"], (
        result.stderr
    )
