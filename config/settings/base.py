"""Réglages communs à tous les environnements. Les valeurs sensibles viennent de l'environnement."""

from pathlib import Path

import environ
from django.utils.csp import CSP

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
    "django.contrib.sitemaps",
    "django.contrib.postgres",
    "django_htmx",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "apps.core",
    "apps.accounts",
    "apps.listings",
    "apps.favorites",
    "apps.messaging",
    "apps.moderation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
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
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navigation",
                "apps.core.context_processors.seo",
                "apps.favorites.context_processors.favorites",
                "apps.messaging.context_processors.unread_messages",
                "apps.accounts.context_processors.auth_options",
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
    # Actions du site (apps/core/ratelimit.py) : dépôt d'annonce par utilisateur (ticket #7) ;
    # la limite par jour est comptée en base (LISTINGS_PER_DAY, #49).
    "listing_create": "5/h/user",
    # Signalements (#49) : un membre qui signale à la chaîne abuse du bouton.
    "listing_report": "10/h/user,30/d/user",
    # Messagerie (ticket #12) : nouvelles conversations (démarchage, arnaques en série) et
    # messages (une négociation en échange quelques dizaines par heure).
    "conversation_start": "10/h/user,30/d/user",
    "message_send": "60/h/user,300/d/user",
    # Suppression de compte (ticket #13) : le mot de passe ne se devine pas par essais.
    "account_delete": "5/h/user",
}

# Politique de sécurité du contenu (ticket #15, docs/security.md) : nos fichiers seulement.
# Les deux scripts en ligne (thème, avant le CSS) portent un nonce ; aucun style en ligne
# (htmx n'injecte pas ses styles d'indicateur, voir base.html). Photos : domaine R2 en
# production ; blob: pour les aperçus du sélecteur de photos. Le formulaire « Continuer avec
# Google » redirige vers accounts.google.com, que form-action doit autoriser.
PHOTOS_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF, "blob:"] + ([f"https://{PHOTOS_DOMAIN}"] if PHOTOS_DOMAIN else []),
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "manifest-src": [CSP.SELF],
    "worker-src": [CSP.SELF],
    "form-action": [CSP.SELF, "https://accounts.google.com"],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "object-src": [CSP.NONE],
}

# Email confirmé obligatoire pour déposer et écrire à un vendeur (ticket #3, 2026-10-15,
# apps/accounts/decorators.py). Suppose des emails réellement livrés (Resend).
VERIFIED_EMAIL_REQUIRED = env.bool("VERIFIED_EMAIL_REQUIRED", default=True)

# Modération (#49, décisions du 2026-10-17) : annonces déposées par compte sur 24 heures, et
# nombre de membres différents dont les signalements masquent une annonce en attendant l'examen.
LISTINGS_PER_DAY = 10
REPORTS_TO_SUSPEND = 3

# Référencement : balise de vérification de Google Search Console (2026-10-15).
GOOGLE_SITE_VERIFICATION = env("GOOGLE_SITE_VERIFICATION", default="")

# Sauvegardes de la base (ticket #17, apps/core/backups.py) : bucket privé et jeton à part,
# distincts de ceux des photos.
BACKUP_STORAGE = {
    "bucket": env("BACKUP_BUCKET", default="sugu-backups"),
    "endpoint_url": env("BACKUP_S3_ENDPOINT_URL", default=""),
    "access_key": env("BACKUP_ACCESS_KEY_ID", default=""),
    "secret_key": env("BACKUP_SECRET_ACCESS_KEY", default=""),
}

# Admin : adresse secrète en production (ADMIN_URL, ticket #15) ; /admin/ en développement.
ADMIN_URL = env("ADMIN_URL", default="admin/")

# Connexion avec Google (ticket #3, ADR 0002). Sans identifiants, le bouton est masqué.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID)
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": (
            [{"client_id": GOOGLE_CLIENT_ID, "secret": env("GOOGLE_CLIENT_SECRET"), "key": ""}]
            if GOOGLE_LOGIN_ENABLED
            else []
        ),
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "OAUTH_PKCE_ENABLED": True,
    }
}
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
# Google ne renvoie que des adresses vérifiées : une adresse déjà inscrite retrouve son compte.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_STORE_TOKENS = False  # aucun jeton Google gardé en base
SOCIALACCOUNT_LOGIN_ON_GET = False  # la redirection vers Google part d'un POST

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
