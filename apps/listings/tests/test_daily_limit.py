"""Limite de dépôt : 10 annonces par compte sur 24 heures (ticket #49, 2026-10-17)."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.listings import services
from apps.listings.models import Listing

from .factories import CategoryFactory, CityFactory, ListingFactory
from .images import uploaded

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.LISTINGS_PER_DAY = 3


def data():
    return {
        "title": "Chaise en bois",
        "description": "Solide, peu servie.",
        "category": CategoryFactory(parent=CategoryFactory()),
        "city": CityFactory(),
        "price": 5000,
    }


def age(listing, hours):
    Listing.objects.filter(pk=listing.pk).update(created_at=timezone.now() - timedelta(hours=hours))


def test_au_dela_de_la_limite_le_depot_est_refuse():
    user = UserFactory()
    for _ in range(3):
        ListingFactory(user=user, published=True)

    with pytest.raises(services.DailyLimitReached) as error:
        services.create_listing(user, data=data(), photos=[uploaded()])

    assert "3 annonces en 24 heures" in error.value.message
    assert Listing.objects.filter(user=user).count() == 3


def test_les_annonces_de_plus_de_24_heures_ne_comptent_plus():
    user = UserFactory()
    for _ in range(3):
        age(ListingFactory(user=user, published=True), hours=25)

    services.create_listing(user, data=data(), photos=[uploaded()])

    assert Listing.objects.filter(user=user).count() == 4


def test_supprimer_puis_redeposer_ne_rend_pas_de_place():
    user = UserFactory()
    for _ in range(3):
        listing = ListingFactory(user=user, published=True)
    services.seller_remove(user, listing)

    assert isinstance(services.daily_limit_error(user), ValidationError)


def test_la_limite_est_par_compte():
    for _ in range(3):
        ListingFactory(user=UserFactory(), published=True)

    assert services.daily_limit_error(UserFactory()) is None


def test_le_message_dit_quand_redeposer():
    user = UserFactory()
    for hours in (20, 10, 1):
        age(ListingFactory(user=user, published=True), hours=hours)

    error = services.daily_limit_error(user)

    # La plus ancienne des trois (il y a 20 h) libère une place dans 4 heures.
    when = timezone.localtime(timezone.now() + timedelta(hours=4))
    assert f"{when:%H} h {when:%M}" in error.message


def test_la_page_de_depot_previent_des_louverture(client):
    user = UserFactory()
    for _ in range(3):
        ListingFactory(user=user, published=True)
    client.force_login(user)

    html = client.get(reverse("listings:create")).content.decode()

    assert "c&#x27;est le maximum" in html or "c'est le maximum" in html


def test_lenvoi_du_formulaire_affiche_lerreur(client):
    user = UserFactory()
    for _ in range(3):
        ListingFactory(user=user, published=True)
    client.force_login(user)
    form = data()

    response = client.post(
        reverse("listings:create"),
        {
            "title": form["title"],
            "description": form["description"],
            "category": form["category"].pk,
            "city": form["city"].pk,
            "price": "5000",
            "photos": [uploaded()],
        },
    )

    assert response.status_code == 200
    assert "le maximum" in response.content.decode()
    assert Listing.objects.filter(user=user).count() == 3
