"""Mise en production (ticket #15) : `check --deploy` sans avertissement, admin à une adresse
secrète, politique de sécurité du contenu (CSP)."""

import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse

from apps.core.checks import check_admin_url

ROOT = Path(__file__).resolve().parents[3]


def _check_deploy(**overrides):
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "SECRET_KEY": secrets.token_urlsafe(50),
        "ALLOWED_HOSTS": "sugu.ml,www.sugu.ml",
        "DATABASE_URL": "postgres://sugu:secret@db:5432/sugu",
        "EMAIL_URL": "smtp+tls://login:cle@smtp-relay.brevo.com:587",
        "ADMIN_URL": secrets.token_urlsafe(16) + "/",
        "PYTHONUTF8": "1",  # messages accentués lisibles sous Windows aussi
        **overrides,
    }
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_check_deploy_sans_avertissement():
    result = _check_deploy()

    assert result.returncode == 0, result.stdout + result.stderr


def test_check_deploy_refuse_ladmin_a_ladresse_par_defaut():
    result = _check_deploy(ADMIN_URL="admin/")

    assert result.returncode != 0
    assert "sugu.W001" in result.stdout + result.stderr


@pytest.mark.parametrize(
    ("url", "warning"),
    [
        ("admin/", "sugu.W001"),
        ("gestion/", "sugu.W001"),
        ("court123/", "sugu.W001"),
        ("/x7Kq2mPz9LwR4vTn/", "sugu.W002"),
        ("x7Kq2mPz9LwR4vTnB", "sugu.W002"),
        ("x7Kq2mPz9LwR4vTn/", None),
    ],
)
def test_adresse_de_ladmin(settings, url, warning):
    settings.ADMIN_URL = url

    ids = [message.id for message in check_admin_url(None)]

    assert ids == ([warning] if warning else [])


# --- CSP -------------------------------------------------------------------------------------


def _nonce(response):
    header = response["Content-Security-Policy"]
    match = re.search(r"'nonce-([^']+)'", header)
    assert match, header
    return header, match.group(1)


@pytest.mark.django_db
def test_csp_stricte_sur_les_pages(client):
    response = client.get(reverse("core:home"))

    header, nonce = _nonce(response)
    assert "default-src 'self'" in header
    assert "style-src 'self';" in header  # aucun style en ligne autorisé
    assert "'unsafe-inline'" not in header and "'unsafe-eval'" not in header
    assert "frame-ancestors 'none'" in header
    assert "form-action 'self' https://accounts.google.com" in header
    html = response.content.decode()
    assert f'<script nonce="{nonce}">' in html  # script du thème
    assert '"allowEval": false' in html  # htmx sans eval ni styles injectés


@pytest.mark.django_db
def test_csp_page_hors_ligne(client):
    response = client.get(reverse("core:offline"))

    _, nonce = _nonce(response)
    assert f'<script nonce="{nonce}">' in response.content.decode()


@pytest.mark.django_db
def test_aucun_script_en_ligne_sans_nonce(client):
    html = client.get(reverse("core:home")).content.decode()

    inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", html)
    assert inline and all("nonce=" in attrs for attrs in inline)


# --- Fichiers de la pile de production -----------------------------------------------------


def test_les_secrets_nentrent_pas_dans_limage():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()

    assert {".env", ".env.*", ".venv", "media"} <= set(ignored)


def test_caddy_coupe_ce_qui_ne_vient_pas_de_cloudflare():
    """« abort » doit être dans un bloc « route » : sinon Caddy le range après « handle » et la
    coupure ne s'applique jamais (constaté à la répétition locale du ticket #15)."""
    caddyfile = (ROOT / "Caddyfile").read_text(encoding="utf-8")
    route = caddyfile[caddyfile.index("route {") :]

    assert "@direct not remote_ip {$EDGE_RANGES}" in caddyfile
    assert route.index("abort @direct") < route.index("handle")
    assert "header_up CF-Connecting-IP {client_ip}" in caddyfile


def test_limage_utilise_les_reglages_de_production():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "DJANGO_SETTINGS_MODULE=config.settings.prod" in dockerfile
    assert "--checksum=sha256:" in dockerfile
    assert "USER app" in dockerfile
