"""Développement local : DEBUG, base PostgreSQL de compose.yml, emails dans la console."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]
INTERNAL_IPS = ["127.0.0.1"]

DATABASES = {"default": env.db("DATABASE_URL", default="postgres://sugu:sugu@localhost:5432/sugu")}

MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

# Pas de manifeste statique en dev : les fichiers se servent tels quels.
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
