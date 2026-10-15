import sys

from django.core.management.base import BaseCommand

from apps.core import backups


class Command(BaseCommand):
    help = "Écrit sur la sortie standard la sauvegarde demandée (scripts/restore.sh)."

    def add_arguments(self, parser):
        parser.add_argument("key", help="ex. quotidien/sugu-2026-10-15.dump (sauvegarde_lister)")

    def handle(self, *args, key, **options):
        response = backups.client().get_object(Bucket=backups.bucket(), Key=key)
        for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
            sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
