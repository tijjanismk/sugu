"""Gestion de mes annonces (ticket #10) : permissions, modification, prix, photos, vente,
suppression."""

import re

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.listings import services
from apps.listings.forms import LINK_ERROR
from apps.listings.models import Listing, ListingStatus, Photo

from .factories import CategoryFactory, CityFactory, ListingFactory
from .images import uploaded

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def seller():
    return UserFactory()


@pytest.fixture
def listing(seller):
    phones = CategoryFactory(name="Téléphones")
    item = ListingFactory(
        user=seller, published=True, title="Samsung Galaxy A15", price=85000,
        category=CategoryFactory(name="Smartphones", parent=phones),
        city=CityFactory(name="Bamako"),
    )  # fmt: skip
    for order in range(3):
        Photo.objects.create(
            listing=item, order=order, width=1200, height=900,
            large=f"listings/{item.pk}/p{order}-1200.webp",
            thumb=f"listings/{item.pk}/p{order}-400.webp",
        )  # fmt: skip
    return item


def _edit_data(listing, **changes):
    data = {
        "title": listing.title,
        "category": listing.category_id,
        "city": listing.city_id,
        "neighborhood": listing.neighborhood,
        "distance_km": listing.distance_km or "",
        "price": listing.price if listing.price is not None else "",
        "payment_methods": listing.payment_methods,
        "description": listing.description,
    }
    data.update(changes)
    return data


def _urls(listing):
    photo = listing.photos.first()
    return {
        "edit": reverse("listings:edit", args=[listing.pk]),
        "mark_sold": reverse("listings:mark_sold", args=[listing.pk]),
        "delete": reverse("listings:delete", args=[listing.pk]),
        "photo_add": reverse("listings:photo_add", args=[listing.pk]),
        "photo_remove": reverse("listings:photo_remove", args=[listing.pk, photo.pk]),
    }


# --- Permissions : un autre utilisateur essaie --------------------------------------------


@pytest.mark.parametrize("action", ["edit", "mark_sold", "delete", "photo_add", "photo_remove"])
def test_un_autre_utilisateur_recoit_403(client, listing, action):
    client.force_login(UserFactory())
    url = _urls(listing)[action]

    assert client.get(url).status_code == 403
    assert client.post(url, _edit_data(listing, title="Piraté", price=1)).status_code == 403

    listing.refresh_from_db()
    assert listing.title == "Samsung Galaxy A15"
    assert listing.status == ListingStatus.PUBLISHED
    assert listing.price == 85000
    assert listing.photos.count() == 3


@pytest.mark.parametrize("action", ["edit", "mark_sold", "delete", "photo_add", "photo_remove"])
def test_un_visiteur_est_renvoye_vers_la_connexion(client, listing, action):
    response = client.post(_urls(listing)[action])

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_les_services_refusent_aussi_un_autre_utilisateur(listing):
    intruder = UserFactory()

    for call in (
        lambda: services.update_listing(intruder, listing, {"title": "x", "price": 1}),
        lambda: services.seller_mark_sold(intruder, listing),
        lambda: services.seller_remove(intruder, listing),
        lambda: services.remove_photo(intruder, listing.photos.first()),
    ):
        with pytest.raises(services.PermissionDenied):
            call()


def test_mes_annonces_ne_liste_que_les_miennes(client, seller, listing):
    other = ListingFactory(published=True, title="Annonce d'un autre")
    removed = ListingFactory(user=seller, status=ListingStatus.REMOVED, title="Supprimée")
    client.force_login(seller)

    html = client.get(reverse("listings:mine")).content.decode()

    assert listing.title in html
    assert other.title not in html
    assert removed.title not in html


def test_mes_annonces_exige_d_etre_connecte(client):
    response = client.get(reverse("listings:mine"))

    assert response.status_code == 302


def test_le_vendeur_voit_un_lien_de_gestion_sur_sa_page(client, seller, listing):
    edit_url = reverse("listings:edit", args=[listing.pk])

    assert edit_url not in client.get(listing.get_absolute_url()).content.decode()
    client.force_login(seller)
    assert edit_url in client.get(listing.get_absolute_url()).content.decode()


# --- Modification ------------------------------------------------------------------------


def test_modifier_le_contenu_quartier_et_distance(client, seller, listing):
    client.force_login(seller)

    response = client.post(
        _urls(listing)["edit"],
        _edit_data(
            listing, title="Samsung Galaxy A15 neuf", neighborhood="Sabalibougou", distance_km=12
        ),
    )

    assert response.status_code == 302
    listing.refresh_from_db()
    assert listing.title == "Samsung Galaxy A15 neuf"
    assert listing.place_label == "Sabalibougou, à 12 km de Bamako"
    # Le trigger a recalculé la recherche : le nouveau quartier est trouvé.
    assert [item.pk for item in services.search_listings(q="sabalibougou")] == [listing.pk]


def test_baisser_le_prix_affiche_la_baisse_et_l_ancien_prix(client, seller, listing):
    client.force_login(seller)

    client.post(_urls(listing)["edit"], _edit_data(listing, price="75 000"))

    listing.refresh_from_db()
    assert listing.price == 75000
    assert listing.previous_price == 85000
    assert listing.has_recent_price_drop
    form_page = client.get(_urls(listing)["edit"]).content.decode()
    assert "Baisse de prix en cours" in form_page
    assert "Ancien prix : 85 000\xa0FCFA" in form_page
    assert "Prix en baisse" in client.get(listing.get_absolute_url()).content.decode()


def test_monter_le_prix_efface_la_baisse(client, seller, listing):
    services.update_price(listing, 75000)
    client.force_login(seller)

    client.post(_urls(listing)["edit"], _edit_data(listing, price=80000))

    listing.refresh_from_db()
    assert listing.previous_price is None


def test_un_lien_vers_un_autre_site_est_refuse(client, seller, listing):
    client.force_login(seller)

    for field, value in [
        ("description", "Voir aussi sur jiji.ml"),
        ("title", "Promo www.autre-site.com"),
        ("description", "Écrivez-moi : vendeur@gmail.com"),
    ]:
        response = client.post(_urls(listing)["edit"], _edit_data(listing, **{field: value}))
        assert response.status_code == 200
        assert LINK_ERROR.replace("'", "&#x27;") in response.content.decode()
    listing.refresh_from_db()
    assert listing.title == "Samsung Galaxy A15"


def test_le_depot_refuse_aussi_les_liens(client, seller):
    client.force_login(seller)
    phones = CategoryFactory(name="Téléphones")
    data = {
        "title": "Téléphone",
        "category": CategoryFactory(name="Smartphones", parent=phones).pk,
        "city": CityFactory().pk,
        "description": "Plus de photos sur https://autre-site.sn/annonce/42",
        "photos": [uploaded()],
    }

    response = client.post(reverse("listings:create"), data)

    assert response.status_code == 200
    assert not Listing.objects.filter(title="Téléphone").exists()


def test_une_annonce_vendue_ne_se_modifie_plus(client, seller, listing):
    services.mark_sold(listing)
    client.force_login(seller)

    page = client.get(_urls(listing)["edit"]).content.decode()
    client.post(_urls(listing)["edit"], _edit_data(listing, title="Remis en vente"))

    assert "Enregistrer les modifications" not in page
    listing.refresh_from_db()
    assert listing.title == "Samsung Galaxy A15"


# --- Vente et suppression ----------------------------------------------------------------


def test_marquer_vendue_demande_confirmation_puis_garde_l_annonce_visible(client, seller, listing):
    client.force_login(seller)

    confirm = client.get(_urls(listing)["mark_sold"])
    listing.refresh_from_db()
    assert confirm.status_code == 200
    assert listing.status == ListingStatus.PUBLISHED  # un GET ne fait rien

    client.post(_urls(listing)["mark_sold"])

    listing.refresh_from_db()
    assert listing.status == ListingStatus.SOLD
    page = client.get(listing.get_absolute_url())
    assert page.status_code == 200
    assert "Annonce vendue" in page.content.decode()  # bandeau
    assert services.search_listings(q="samsung").count() == 0


def test_supprimer_demande_confirmation_puis_l_annonce_disparait(client, seller, listing):
    client.force_login(seller)
    assert services.search_listings(q="samsung").count() == 1

    assert client.get(_urls(listing)["delete"]).status_code == 200
    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED

    response = client.post(_urls(listing)["delete"])

    assert response.url == reverse("listings:mine")
    listing.refresh_from_db()
    assert listing.status == ListingStatus.REMOVED
    assert Listing.objects.filter(pk=listing.pk).exists()  # pas d'effacement en base
    assert services.search_listings(q="samsung").count() == 0
    assert client.get(listing.get_absolute_url()).status_code == 404
    assert client.get(reverse("listings:edit", args=[listing.pk])).status_code == 404
    assert listing.title not in client.get(reverse("core:home")).content.decode()


def test_une_annonce_vendue_peut_etre_supprimee(client, seller, listing):
    services.mark_sold(listing)
    client.force_login(seller)

    client.post(_urls(listing)["delete"])

    listing.refresh_from_db()
    assert listing.status == ListingStatus.REMOVED


# --- Photos ------------------------------------------------------------------------------


def test_retirer_la_couverture_promeut_la_suivante(client, seller, listing):
    cover, second, third = listing.photos.order_by("order")
    client.force_login(seller)

    client.post(reverse("listings:photo_remove", args=[listing.pk, cover.pk]))

    assert [(p.pk, p.order) for p in listing.photos.order_by("order")] == [
        (second.pk, 0),
        (third.pk, 1),
    ]


def test_retirer_une_photo_du_milieu_renumerote(client, seller, listing):
    cover, second, third = listing.photos.order_by("order")
    client.force_login(seller)

    client.post(reverse("listings:photo_remove", args=[listing.pk, second.pk]))

    assert [(p.pk, p.order) for p in listing.photos.order_by("order")] == [
        (cover.pk, 0),
        (third.pk, 1),
    ]


def test_la_derniere_photo_ne_peut_pas_etre_retiree(client, seller, listing):
    client.force_login(seller)
    for photo in list(listing.photos.order_by("-order"))[:2]:
        client.post(reverse("listings:photo_remove", args=[listing.pk, photo.pk]))
    last = listing.photos.get()

    response = client.post(
        reverse("listings:photo_remove", args=[listing.pk, last.pk]), follow=True
    )

    assert listing.photos.count() == 1
    assert "au moins une photo" in response.content.decode()


def test_une_photo_d_une_autre_annonce_est_introuvable(client, seller, listing):
    mine_too = ListingFactory(user=seller, published=True)
    other_photo = Photo.objects.create(
        listing=mine_too, order=0, width=1, height=1, large="a.webp", thumb="b.webp"
    )
    client.force_login(seller)

    response = client.post(reverse("listings:photo_remove", args=[listing.pk, other_photo.pk]))

    assert response.status_code == 404
    assert Photo.objects.filter(pk=other_photo.pk).exists()


def test_ajouter_des_photos_a_la_suite(client, seller, listing):
    client.force_login(seller)

    client.post(
        _urls(listing)["photo_add"],
        {"photos": [uploaded(name="a.jpg", width=1600, height=1200), uploaded(name="b.jpg")]},
    )

    orders = list(listing.photos.order_by("order").values_list("order", flat=True))
    assert orders == [0, 1, 2, 3, 4]
    new = listing.photos.order_by("order").last()
    assert new.large.name.endswith("-1200.webp")


def test_pas_plus_de_6_photos(client, seller, listing):
    client.force_login(seller)

    response = client.post(
        _urls(listing)["photo_add"],
        {"photos": [uploaded(name=f"{i}.jpg") for i in range(4)]},
        follow=True,
    )

    assert listing.photos.count() == 3
    assert "vous pouvez en ajouter 3" in response.content.decode()


def test_un_fichier_qui_n_est_pas_une_image_n_est_pas_ajoute(client, seller, listing):
    client.force_login(seller)

    client.post(
        _urls(listing)["photo_add"],
        {"photos": [uploaded(name="x.jpg", content=b"pas une image")]},
    )

    assert listing.photos.count() == 3


def test_retirer_une_photo_efface_ses_fichiers(
    client, seller, listing, _media, django_capture_on_commit_callbacks
):
    client.force_login(seller)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(_urls(listing)["photo_add"], {"photos": [uploaded()]})
    added = listing.photos.order_by("order").last()
    files = [_media / added.large.name, _media / added.thumb.name]
    assert all(f.exists() for f in files)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("listings:photo_remove", args=[listing.pk, added.pk]))

    assert not any(f.exists() for f in files)


def test_la_liste_affiche_le_statut(client, seller, listing):
    sold = ListingFactory(user=seller, status=ListingStatus.SOLD, published_at=timezone.now())
    client.force_login(seller)

    html = client.get(reverse("listings:mine")).content.decode()

    assert re.search(r"En ligne</span>", html)
    assert sold.title in html
    assert "sg-badge--sold" in html
