"""Réglages communs à tous les environnements. Les valeurs sensibles viennent de l'environnement."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# En local, un fichier .env à la racine suffit ; en production, Docker fournit les variables.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_htmx",
    "allauth",
    "allauth.account",
    "apps.core",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modèle utilisateur personnalisé dès la première migration (ADR 0001, ticket #3 l'enrichit).
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Bamako"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"

# Comptes (django-allauth) : connexion par email, pas de nom d'utilisateur (ticket #3).
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.SignupForm"
# Vérification « optionnelle » : l'email de confirmation part, le compte sert tout de suite.
# À passer en "mandatory" si les faux comptes arrivent (docs/security.md).
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Sugu] "
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
# Sur un téléphone personnel, on reste connecté : pas de case « Se souvenir de moi ».
ACCOUNT_SESSION_REMEMBER = True
# Lien de réinitialisation du mot de passe valable une heure.
PASSWORD_RESET_TIMEOUT = 60 * 60
# Limitation de débit (docs/security.md) : 5 connexions ratées par compte et par IP sur
# 15 min, 3 inscriptions par IP et par heure. Les compteurs vivent dans le cache Django.
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/15m/ip,5/15m/key",
    "signup": "3/h/ip",
}

# Cache partagé entre les processus Gunicorn, sans Redis (ADR 0001) : table créée par la
# migration core 0001. Dev et test le remplacent par un cache en mémoire.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# Django 6.1 : les emails se configurent par MAILERS (le dict), plus par EMAIL_BACKEND.
# Chaque environnement définit le sien ; le défaut ci-dessous ne doit jamais servir.
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.dummy.EmailBackend"}}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Sugu <no-reply@sugu.ml>")
