"""Tests (pytest et CI) : rapides, sans réseau, stockage de fichiers temporaire."""

import tempfile

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://sugu:sugu@localhost:5432/sugu_test")
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}

MEDIA_ROOT = tempfile.mkdtemp(prefix="sugu-test-media-")
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
WHITENOISE_AUTOREFRESH = True
