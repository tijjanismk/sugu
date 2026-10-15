"""Sauvegardes de la base vers un bucket compatible S3 : Cloudflare R2 en production (ticket #17).

`scripts/backup.sh` fait le `pg_dump` dans le conteneur de la base, en garde une copie sur le
serveur, puis passe le fichier à `manage.py sauvegarde_envoyer` qui l'envoie ici ;
`scripts/restore.sh` le récupère avec `sauvegarde_telecharger`.

Deux préfixes, chacun avec sa règle de cycle de vie dans R2 (docs/runbook.md) : `quotidien/`
gardé 30 jours, `mensuel/` (la sauvegarde du 1er du mois) gardé un an. Le serveur n'efface
donc jamais rien lui-même dans le bucket.

Clés et bucket séparés de ceux des photos : un jeton qui fuit ne donne pas accès aux deux.
"""

from datetime import date

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DAILY_PREFIX = "quotidien/"
MONTHLY_PREFIX = "mensuel/"
NOT_CONFIGURED = (
    "Copie hors du serveur non configurée : BACKUP_S3_ENDPOINT_URL, BACKUP_ACCESS_KEY_ID et "
    "BACKUP_SECRET_ACCESS_KEY (docs/runbook.md, « Sauvegardes »)."
)


def is_configured() -> bool:
    config = settings.BACKUP_STORAGE
    return bool(config["endpoint_url"] and config["access_key"] and config["secret_key"])


def client():
    if not is_configured():
        raise ImproperlyConfigured(NOT_CONFIGURED)
    config = settings.BACKUP_STORAGE
    return boto3.client(
        "s3",
        endpoint_url=config["endpoint_url"],
        aws_access_key_id=config["access_key"],
        aws_secret_access_key=config["secret_key"],
        region_name="auto",
        # Adresses du type <endpoint>/<bucket>/… : R2 les accepte, le bucket local de la
        # répétition générale aussi (pas de sous-domaine par bucket).
        config=Config(s3={"addressing_style": "path"}),
    )


def bucket() -> str:
    return settings.BACKUP_STORAGE["bucket"]


def keys_for(day: date) -> list[str]:
    """Où ranger la sauvegarde du jour : toujours dans `quotidien/`, et aussi dans `mensuel/`
    le 1er du mois."""
    keys = [f"{DAILY_PREFIX}sugu-{day:%Y-%m-%d}.dump"]
    if day.day == 1:
        keys.append(f"{MONTHLY_PREFIX}sugu-{day:%Y-%m}.dump")
    return keys


def list_backups(s3=None) -> list[dict]:
    """Toutes les sauvegardes du bucket, les plus récentes d'abord."""
    s3 = s3 or client()
    objects = []
    for prefix in (DAILY_PREFIX, MONTHLY_PREFIX):
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=prefix):
            objects += page.get("Contents", [])
    return sorted(objects, key=lambda o: o["LastModified"], reverse=True)
