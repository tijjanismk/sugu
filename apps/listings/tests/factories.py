import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.listings.models import Category, City, Listing, ListingStatus, PaymentMethod


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Catégorie {n}")
    icon = "grid"


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f"Ville {n}")
    region = "Région"


class ListingFactory(factory.django.DjangoModelFactory):
    """Brouillon par défaut ; `ListingFactory(published=True)` pour une annonce publiée."""

    class Meta:
        model = Listing

    class Params:
        published = factory.Trait(
            status=ListingStatus.PUBLISHED,
            published_at=factory.LazyFunction(timezone.now),
        )

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    city = factory.SubFactory(CityFactory)
    title = factory.Sequence(lambda n: f"Annonce {n}")
    description = "Bon état, à voir sur place."
    price = 50000
    payment_methods = factory.LazyFunction(lambda: [PaymentMethod.CASH_ON_DELIVERY])
