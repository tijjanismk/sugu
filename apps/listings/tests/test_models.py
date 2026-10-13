"""Catégories et villes : slug et hiérarchie à deux niveaux (ticket #5)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.listings.models import Category, City

pytestmark = pytest.mark.django_db


# --- Slug --------------------------------------------------------------------------------


def test_le_slug_vient_du_nom_sans_accents():
    category = Category.objects.create(name="Téléphones et Électroménager")

    assert category.slug == "telephones-et-electromenager"


def test_un_slug_fourni_est_garde():
    category = Category.objects.create(name="Vélos et motos", slug="velos-motos")

    assert category.slug == "velos-motos"


def test_le_slug_ne_change_pas_quand_on_renomme():
    category = Category.objects.create(name="Mode")

    category.name = "Mode et beauté"
    category.save()

    assert category.slug == "mode"


def test_une_sous_categorie_homonyme_prend_le_prefixe_du_parent():
    Category.objects.create(name="Accessoires")
    phones = Category.objects.create(name="Téléphones")

    accessories = Category.objects.create(name="Accessoires", parent=phones)

    assert accessories.slug == "telephones-accessoires"


def test_deux_categories_principales_homonymes_ont_des_slugs_distincts():
    first = Category.objects.create(name="Divers")
    second = Category.objects.create(name="Divers")

    assert first.slug == "divers"
    assert second.slug == "divers-2"


def test_le_slug_est_unique_en_base():
    Category.objects.create(name="Mode", slug="mode")

    with pytest.raises(IntegrityError):
        Category.objects.create(name="Autre", slug="mode")


def test_la_ville_a_un_slug_sans_accents():
    city = City.objects.create(name="Ségou", region="Ségou")

    assert city.slug == "segou"
    assert str(city) == "Ségou"


# --- Hiérarchie --------------------------------------------------------------------------


def test_une_sous_categorie_est_rattachee_a_sa_parente():
    phones = Category.objects.create(name="Téléphones")
    smartphones = Category.objects.create(name="Smartphones", parent=phones)

    assert phones.is_root
    assert not smartphones.is_root
    assert list(phones.children.all()) == [smartphones]
    assert str(smartphones) == "Téléphones › Smartphones"


def test_un_troisieme_niveau_est_refuse():
    phones = Category.objects.create(name="Téléphones")
    smartphones = Category.objects.create(name="Smartphones", parent=phones)

    with pytest.raises(ValidationError):
        Category.objects.create(name="Android", parent=smartphones)
    assert not Category.objects.filter(name="Android").exists()


def test_une_categorie_avec_des_enfants_ne_peut_pas_devenir_enfant():
    phones = Category.objects.create(name="Téléphones")
    Category.objects.create(name="Smartphones", parent=phones)
    electronics = Category.objects.create(name="Électronique")

    phones.parent = electronics
    with pytest.raises(ValidationError):
        phones.save()


def test_une_categorie_ne_peut_pas_etre_sa_propre_parente():
    phones = Category.objects.create(name="Téléphones")

    phones.parent = phones
    with pytest.raises(ValidationError):
        phones.full_clean()


def test_la_base_refuse_aussi_une_categorie_parente_d_elle_meme():
    phones = Category.objects.create(name="Téléphones")

    # Contourne save() : la contrainte CHECK de PostgreSQL prend le relais.
    with pytest.raises(IntegrityError):
        Category.objects.filter(pk=phones.pk).update(parent=phones)


def test_les_categories_sont_triees_par_ordre_puis_nom():
    Category.objects.create(name="B", order=20)
    Category.objects.create(name="C", order=10)
    Category.objects.create(name="A", order=20)

    assert [c.name for c in Category.objects.all()] == ["C", "A", "B"]
