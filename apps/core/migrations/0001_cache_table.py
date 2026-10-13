from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Table du DatabaseCache (limitation de débit d'allauth) ; sans effet si le cache
    # configuré n'est pas en base (dev, test). Idempotent.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    """Crée la table du cache partagé en même temps que le reste du schéma (ticket #3)."""

    dependencies = []

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop, elidable=True),
    ]
