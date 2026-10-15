import sys

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core import backups

MIN_DUMP_BYTES = 1024  # un pg_dump vide ou interrompu fait quelques octets


class Command(BaseCommand):
    help = (
        "Envoie sur le bucket de sauvegarde le pg_dump lu sur l'entrée standard "
        "(scripts/backup.sh)."
    )

    def handle(self, *args, **options):
        data = sys.stdin.buffer.read()
        if len(data) < MIN_DUMP_BYTES:
            raise CommandError(
                f"Sauvegarde vide ou incomplète ({len(data)} octets) : rien n'est envoyé."
            )
        if not backups.is_configured():
            # Pas une erreur : scripts/backup.sh a déjà gardé la copie du serveur.
            # `check --deploy` le signale (sugu.W004).
            self.stdout.write(backups.NOT_CONFIGURED)
            return
        s3 = backups.client()
        for key in backups.keys_for(timezone.localdate()):
            s3.put_object(Bucket=backups.bucket(), Key=key, Body=data)
            self.stdout.write(f"Envoyée : {backups.bucket()}/{key} ({len(data)} octets)")
