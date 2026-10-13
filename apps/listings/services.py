from dataclasses import dataclass

from django.db import transaction

from .models import Category, City
from .seed_data import CATEGORIES, CITIES

HOME_CATEGORY_COUNT = 8


@dataclass
class SeedReport:
    categories_created: int = 0
    cities_created: int = 0


@transaction.atomic
def seed_reference_data() -> SeedReport:
    """Charge catégories et villes de référence. Idempotent : chaque ligne est retrouvée par son
    slug ; un second passage ne crée rien et remet les valeurs de référence."""
    report = SeedReport()
    for position, (name, slug, icon, children) in enumerate(CATEGORIES, start=1):
        parent, created = Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "order": position * 10, "parent": None},
        )
        report.categories_created += created
        for child_position, (child_name, child_slug) in enumerate(children, start=1):
            _, created = Category.objects.update_or_create(
                slug=child_slug,
                defaults={
                    "name": child_name,
                    "icon": "",
                    "order": child_position * 10,
                    "parent": parent,
                },
            )
            report.categories_created += created
    for name, slug, region in CITIES:
        _, created = City.objects.update_or_create(
            slug=slug, defaults={"name": name, "region": region}
        )
        report.cities_created += created
    return report


def home_categories():
    """Catégories principales affichées en tuiles sur l'accueil (design/components/CategoryTile)."""
    return Category.objects.filter(parent__isnull=True).order_by("order", "name")[
        :HOME_CATEGORY_COUNT
    ]
