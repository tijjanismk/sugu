"""Annonces (ticket #6) : transitions de statut, baisse de prix, contraintes, recherche."""

from datetime import timedelta

import pytest
from django.contrib.postgres.search import SearchQuery
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.listings import services
from apps.listings.models import (
    ALLOWED_TRANSITIONS,
    DESCRIPTION_MAX_LENGTH,
    SEARCH_CONFIG,
    Listing,
    ListingStatus,
    Photo,
)
from apps.listings.services import InvalidStatusTransition, PriceLocked

from .factories import ListingFactory

pytestmark = pytest.mark.django_db

S = ListingStatus


# --- Transitions de statut ---------------------------------------------------------------

AUTORISEES = [(S.DRAFT, S.PUBLISHED), (S.DRAFT, S.REMOVED), (S.PUBLISHED, S.SOLD),
              (S.PUBLISHED, S.REMOVED), (S.SOLD, S.REMOVED)]  # fmt: skip
INTERDITES = [(S.SOLD, S.PUBLISHED), (S.REMOVED, S.PUBLISHED), (S.REMOVED, S.DRAFT),
              (S.PUBLISHED, S.DRAFT), (S.DRAFT, S.SOLD), (S.PUBLISHED, S.RESERVED),
              (S.SOLD, S.SOLD)]  # fmt: skip


def _listing_in(status):
    published_at = None if status == S.DRAFT else timezone.now()
    return ListingFactory(status=status, published_at=published_at)


@pytest.mark.parametrize(("depart", "arrivee"), AUTORISEES)
def test_transition_autorisee(depart, arrivee):
    listing = _listing_in(depart)

    services.change_status(listing, arrivee)

    listing.refresh_from_db()
    assert listing.status == arrivee


@pytest.mark.parametrize(("depart", "arrivee"), INTERDITES)
def test_transition_interdite(depart, arrivee):
    listing = _listing_in(depart)

    with pytest.raises(InvalidStatusTransition):
        services.change_status(listing, arrivee)

    listing.refresh_from_db()
    assert listing.status == depart


def test_removed_est_definitif():
    assert ALLOWED_TRANSITIONS[S.REMOVED] == set()


def test_aucune_transition_ne_mene_a_reserved_en_v1():
    assert all(S.RESERVED not in targets for targets in ALLOWED_TRANSITIONS.values())


def test_la_premiere_publication_fixe_published_at():
    listing = ListingFactory()
    assert listing.published_at is None

    services.publish(listing)

    listing.refresh_from_db()
    assert listing.published_at is not None
    assert listing.status == S.PUBLISHED


def test_vendre_garde_la_date_de_publication():
    listing = ListingFactory(published=True)
    published_at = listing.published_at

    services.mark_sold(listing)

    listing.refresh_from_db()
    assert listing.status == S.SOLD
    assert listing.published_at == published_at


def test_change_status_lit_l_etat_en_base_pas_l_objet_en_memoire():
    listing = ListingFactory(published=True)
    stale = Listing.objects.get(pk=listing.pk)
    services.mark_sold(listing)

    # `stale` croit encore l'annonce publiée : la transition sold → sold est refusée.
    with pytest.raises(InvalidStatusTransition):
        services.mark_sold(stale)


# --- Baisse de prix ----------------------------------------------------------------------


def test_une_baisse_sur_une_annonce_publiee_memorise_l_ancien_prix():
    listing = ListingFactory(published=True, price=50000)

    services.update_price(listing, 45000)

    listing.refresh_from_db()
    assert listing.price == 45000
    assert listing.previous_price == 50000
    assert listing.price_dropped_at is not None
    assert listing.has_recent_price_drop


def test_deux_baisses_successives_gardent_le_dernier_prix_affiche():
    listing = ListingFactory(published=True, price=50000)

    services.update_price(listing, 45000)
    services.update_price(listing, 40000)

    listing.refresh_from_db()
    assert listing.previous_price == 45000
    assert listing.price == 40000


def test_une_hausse_efface_la_baisse():
    listing = ListingFactory(published=True, price=50000)
    services.update_price(listing, 45000)

    services.update_price(listing, 48000)

    listing.refresh_from_db()
    assert listing.price == 48000
    assert listing.previous_price is None
    assert listing.price_dropped_at is None


def test_passer_a_debattre_efface_la_baisse():
    listing = ListingFactory(published=True, price=50000)
    services.update_price(listing, 45000)

    services.update_price(listing, None)

    listing.refresh_from_db()
    assert listing.price is None
    assert listing.previous_price is None


def test_un_brouillon_n_a_pas_de_baisse():
    listing = ListingFactory(price=50000)

    services.update_price(listing, 40000)

    listing.refresh_from_db()
    assert listing.price == 40000
    assert listing.previous_price is None


def test_un_prix_qui_ne_change_pas_garde_la_baisse():
    listing = ListingFactory(published=True, price=50000)
    services.update_price(listing, 45000)

    services.update_price(listing, 45000)

    listing.refresh_from_db()
    assert listing.previous_price == 50000


@pytest.mark.parametrize("status", [S.SOLD, S.REMOVED])
def test_le_prix_d_une_annonce_vendue_ou_retiree_ne_change_plus(status):
    listing = _listing_in(status)

    with pytest.raises(PriceLocked):
        services.update_price(listing, 1000)


def test_la_mention_de_baisse_s_eteint_apres_14_jours():
    listing = ListingFactory(published=True, price=50000)
    services.update_price(listing, 45000)
    Listing.objects.filter(pk=listing.pk).update(
        price_dropped_at=timezone.now() - timedelta(days=15)
    )

    listing.refresh_from_db()

    assert listing.previous_price == 50000
    assert not listing.has_recent_price_drop


# --- Contraintes en base -----------------------------------------------------------------


def _viole(**fields):
    listing = ListingFactory(published=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        Listing.objects.filter(pk=listing.pk).update(**fields)


def test_la_base_refuse_un_prix_negatif():
    _viole(price=-1)


def test_la_base_refuse_un_mode_de_reglement_inconnu():
    _viole(payment_methods=["cheque"])


def test_la_base_refuse_un_statut_inconnu():
    _viole(status="archived")


def test_la_base_refuse_une_annonce_publiee_sans_date():
    _viole(published_at=None)


def test_la_base_refuse_un_ancien_prix_inferieur_au_prix():
    _viole(previous_price=10000, price_dropped_at=timezone.now(), price=50000)


def test_la_base_refuse_une_description_trop_longue():
    _viole(description="x" * (DESCRIPTION_MAX_LENGTH + 1))


def test_la_validation_refuse_une_description_trop_longue():
    listing = ListingFactory.build(description="x" * (DESCRIPTION_MAX_LENGTH + 1))

    with pytest.raises(ValidationError) as excinfo:
        listing.full_clean(exclude=["user", "category", "city"])
    assert "description" in excinfo.value.message_dict


def test_un_brouillon_retire_peut_ne_pas_avoir_ete_publie():
    listing = ListingFactory()

    services.remove(listing)

    listing.refresh_from_db()
    assert listing.status == S.REMOVED
    assert listing.published_at is None


# --- Recherche plein texte (trigger) -----------------------------------------------------


def _cherche(texte):
    return list(Listing.objects.filter(search_vector=SearchQuery(texte, config=SEARCH_CONFIG)))


def test_le_trigger_remplit_le_vecteur_de_recherche():
    listing = ListingFactory(title="Vélo de course Peugeot")

    listing.refresh_from_db()

    assert listing.search_vector


def test_velo_trouve_velo_de_course_sans_accent():
    listing = ListingFactory(title="Vélo de course Peugeot")
    ListingFactory(title="Canapé trois places")

    assert _cherche("velo") == [listing]


def test_la_recherche_trouve_les_pluriels_et_la_description():
    listing = ListingFactory(title="Appartement F3", description="Deux chambres climatisées")

    assert _cherche("appartements") == [listing]
    assert _cherche("chambre") == [listing]


def test_le_vecteur_suit_une_modification_du_titre():
    listing = ListingFactory(title="Vélo de course")

    listing.title = "Moto Jakarta"
    listing.save()

    assert _cherche("moto") == [listing]
    assert _cherche("velo") == []


def test_changer_le_statut_ne_recalcule_pas_le_vecteur_inutilement():
    listing = ListingFactory(title="Vélo de course")

    services.publish(listing)

    assert _cherche("velo") == [listing]


# --- Photos ------------------------------------------------------------------------------


def _photo(listing, order):
    return Photo.objects.create(
        listing=listing, large=f"l{order}.webp", thumb=f"t{order}.webp", order=order,
        width=1200, height=900,
    )  # fmt: skip


def test_deux_photos_ne_peuvent_pas_avoir_le_meme_rang():
    listing = ListingFactory()
    _photo(listing, 0)

    with pytest.raises(IntegrityError), transaction.atomic():
        _photo(listing, 0)


def test_six_photos_au_plus():
    listing = ListingFactory()
    for order in range(6):
        _photo(listing, order)

    with pytest.raises(IntegrityError), transaction.atomic():
        _photo(listing, 6)


def test_les_photos_sont_supprimees_avec_l_annonce():
    listing = ListingFactory()
    _photo(listing, 1)
    _photo(listing, 0)

    assert [p.order for p in listing.photos.all()] == [0, 1]
    listing.delete()
    assert Photo.objects.count() == 0
