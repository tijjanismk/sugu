"""Production : HTTPS derrière Caddy et Cloudflare, photos sur R2, secrets par l'environnement."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# Caddy termine le TLS et transmet X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# EMAIL_URL=smtp://user:password@host:587 (django-environ) traduit en MAILERS (Django 6.1).
_email = env.email_url("EMAIL_URL", default="consolemail://")
_email_options = {
    "host": _email.get("EMAIL_HOST"),
    "port": _email.get("EMAIL_PORT"),
    "username": _email.get("EMAIL_HOST_USER"),
    "password": _email.get("EMAIL_HOST_PASSWORD"),
    "use_tls": _email.get("EMAIL_USE_TLS", False),
    "use_ssl": _email.get("EMAIL_USE_SSL", False),
}
MAILERS = {
    "default": {
        "BACKEND": _email["EMAIL_BACKEND"],
        "OPTIONS": {k: v for k, v in _email_options.items() if v not in (None, "")}
        if "smtp" in _email["EMAIL_BACKEND"]
        else {},
    }
}

# Photos sur Cloudflare R2 (API S3) dès que les clés sont fournies ; sinon disque local (ticket #7).
if env("AWS_STORAGE_BUCKET_NAME", default=""):
    STORAGES["default"] = {  # noqa: F405
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
            "endpoint_url": env("AWS_S3_ENDPOINT_URL"),
            "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default=None),
            "default_acl": None,
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

# Comptes : liens des emails (confirmation, mot de passe oublié) en HTTPS.
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
# Limitation de débit par IP : derrière Cloudflare puis Caddy, REMOTE_ADDR est celle de Caddy.
# Cloudflare fournit l'IP du visiteur dans CF-Connecting-IP. Ne se fier à cet en-tête que si
# le serveur n'accepte le trafic web que depuis Cloudflare (ticket #15, docs/security.md).
ALLAUTH_TRUSTED_CLIENT_IP_HEADER = "CF-Connecting-IP"
