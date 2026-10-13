from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Charge les données de démonstration (catégories, villes, annonces). Rempli au ticket #5."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories-only", action="store_true", help="Catégories et villes seulement"
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Rien à charger pour l'instant : le ticket #5 remplit cette commande."
            )
        )
