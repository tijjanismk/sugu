from django.core.management.base import BaseCommand

from apps.core import backups


class Command(BaseCommand):
    help = "Liste les sauvegardes du bucket, les plus récentes d'abord."

    def handle(self, *args, **options):
        objects = backups.list_backups()
        for item in objects:
            when = f"{item['LastModified']:%Y-%m-%d %H:%M}"
            self.stdout.write(f"{item['Key']}  {item['Size']} octets  {when}")
        if not objects:
            self.stdout.write("Aucune sauvegarde dans le bucket.")
