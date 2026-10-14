from django.core.management.base import BaseCommand

from apps.listings.services import seed_demo_listings, seed_reference_data


class Command(BaseCommand):
    help = (
        "Charge les données de démonstration : catégories et villes, puis annonces de démo. "
        "Idempotent : peut être relancée sans créer de doublon. Pas en production : les "
        "annonces de démo seraient visibles de tous (utiliser --categories-only)."
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
            created = seed_demo_listings()
            self.stdout.write(self.style.SUCCESS(f"Annonces de démo : {created} créée(s)."))
