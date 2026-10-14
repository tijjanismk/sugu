from django.core.management.base import BaseCommand

from apps.listings.services import seed_reference_data


class Command(BaseCommand):
    help = (
        "Charge les données de démonstration : catégories et villes (ticket #5), puis annonces "
        "(ticket #6). Idempotent : peut être relancée sans créer de doublon."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories-only", action="store_true", help="Catégories et villes seulement"
        )

    def handle(self, *args, **options):
        report = seed_reference_data()
        self.stdout.write(
            self.style.SUCCESS(
                f"Catégories : {report.categories_created} créée(s). "
                f"Villes : {report.cities_created} créée(s). "
                "Les lignes existantes ont été remises aux valeurs de référence."
            )
        )
        if not options["categories_only"]:
            self.stdout.write("Annonces de démonstration : arrivent avec le ticket #6.")
