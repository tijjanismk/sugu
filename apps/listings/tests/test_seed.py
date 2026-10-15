"""Données de référence : `manage.py seed` est idempotent (ticket #5)."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.listings.models import Category, City, Listing, ListingStatus
from apps.listings.seed_data import CATEGORIES, CITIES, DEMO_LISTINGS
from apps.listings.services import seed_demo_listings, seed_reference_data

pytestmark = pytest.mark.django_db

NB_CATEGORIES = len(CATEGORIES) + sum(len(children) for *_, children in CATEGORIES)


def test_seed_cree_les_categories_et_les_villes():
    report = seed_reference_data()

    assert report.categories_created == NB_CATEGORIES
    assert report.cities_created == len(CITIES)
    assert Category.objects.filter(parent__isnull=True).count() == len(CATEGORIES)
    assert City.objects.get(slug="bamako").region == "District de Bamako"
    smartphones = Category.objects.get(slug="smartphones")
    assert smartphones.parent.slug == "telephones"


def test_seed_relance_ne_cree_pas_de_doublon():
    seed_reference_data()

    report = seed_reference_data()

    assert report.categories_created == 0
    assert report.cities_created == 0
    assert Category.objects.count() == NB_CATEGORIES
    assert City.objects.count() == len(CITIES)


def test_seed_remet_les_valeurs_de_reference():
    seed_reference_data()
    Category.objects.filter(slug="mode").update(name="Modifié à la main", order=999)

    seed_reference_data()

    mode = Category.objects.get(slug="mode")
    assert mode.name == "Mode"
    assert mode.order != 999


def test_seed_garde_les_categories_ajoutees_a_la_main():
    Category.objects.create(name="Animaux")

    seed_reference_data()

    assert Category.objects.filter(slug="animaux").exists()


def test_la_commande_seed_est_idempotente():
    out = StringIO()
    call_command("seed", stdout=out)
    call_command("seed", "--categories-only", stdout=out)

    assert Category.objects.count() == NB_CATEGORIES
    assert City.objects.count() == len(CITIES)
    assert "0 créée(s)" in out.getvalue()


def test_les_categories_principales_s_affichent_sur_l_accueil(client):
    seed_reference_data()

    html = client.get(reverse("core:home")).content.decode()

    assert html.count('class="sg-cat"') == 8
    for name, slug, *_ in CATEGORIES[:8]:
        assert name in html
        assert f"/categorie/{slug}/" in html  # page catégorie (référencement)
    # Les sous-catégories ne sont pas des tuiles.
    assert "Smartphones" not in html


def test_l_accueil_sans_categorie_n_affiche_pas_la_section(client):
    html = client.get(reverse("core:home")).content.decode()

    assert "sg-cats" not in html


# --- Annonces de démonstration (ticket #6) -----------------------------------------------


def test_seed_cree_les_annonces_de_demo_publiees():
    seed_reference_data()

    assert seed_demo_listings() == len(DEMO_LISTINGS)
    assert Listing.objects.filter(status=ListingStatus.PUBLISHED).count() == len(DEMO_LISTINGS)
    seller = Listing.objects.first().user
    assert not seller.has_usable_password()
    velo = Listing.objects.get(title__startswith="Vélo de course")
    assert velo.has_recent_price_drop


def test_les_annonces_de_demo_sont_idempotentes():
    seed_reference_data()
    seed_demo_listings()

    assert seed_demo_listings() == 0
    assert Listing.objects.count() == len(DEMO_LISTINGS)


def test_seed_categories_only_ne_cree_pas_d_annonce():
    call_command("seed", "--categories-only", stdout=StringIO())

    assert Listing.objects.count() == 0
