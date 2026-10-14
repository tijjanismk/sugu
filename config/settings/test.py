"""Tests (pytest et CI) : rapides, sans réseau, stockage de fichiers temporaire."""

import tempfile
from pathlib import Path

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://sugu:sugu@localhost:5432/sugu_test")
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}

# Un seul dossier, réutilisé d'une exécution à l'autre : mkdtemp en créait un nouveau à
# chaque lancement de pytest, jamais supprimé. Les tests qui écrivent des fichiers
# (dépôt d'annonce) utilisent en plus leur propre tmp_path.
MEDIA_ROOT = Path(tempfile.gettempdir()) / "sugu-test-media"
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
WHITENOISE_AUTOREFRESH = True
# Le job e2e lance runserver avec ces réglages, sans collectstatic : WhiteNoise sert alors
# les fichiers depuis leurs sources (htmx, pwa.js qui enregistre le service worker).
WHITENOISE_USE_FINDERS = True

# Cache en mémoire, vidé avant chaque test (conftest.py) pour isoler les limites de débit.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
