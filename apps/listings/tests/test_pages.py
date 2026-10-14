"""Liste, pagination « Voir plus » et page de l'annonce (ticket #8)."""

import re
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.listings import services
from apps.listings.models import Listing, ListingStatus, Photo

from .factories import ListingFactory

pytestmark = pytest.mark.django_db

HOME = reverse("core:home")
HTMX = {"HX-Request": "true"}


def _published(n, **kwargs):
    now = timezone.now()
    return [
        ListingFactory(published=True, published_at=now - timedelta(minutes=i), **kwargs)
        for i in range(n)
    ]


def _cards(html):
    return re.findall(r'<a class="sg-card[^"]*" href="([^"]+)"', html)


def _photo(listing, order=0, width=1200, height=800):
    return Photo.objects.create(
        listing=listing, order=order, width=width, height=height,
        large=f"listings/{listing.pk}/p{order}-1200.webp",
        thumb=f"listings/{listing.pk}/p{order}-400.webp",
    )  # fmt: skip


# --- Accueil et pagination ---------------------------------------------------------------


def test_l_accueil_montre_20_annonces_et_un_bouton_voir_plus(client):
    _published(25)

    html = client.get(HOME).content.decode()

    assert len(_cards(html)) == 20
    assert 'hx-get="?page=2"' in html
    assert 'href="?page=2"' in html  # sans JavaScript, « Voir plus » reste un lien


def test_voir_plus_en_htmx_renvoie_seulement_la_page_suivante(client):
    listings = _published(25)

    response = client.get(HOME, {"page": 2}, headers=HTMX)

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert "sg-bottomnav" not in html
    assert len(_cards(html)) == 5
    assert _cards(html)[0] == listings[20].get_absolute_url()
    assert "Voir plus" not in html  # dernière page


def test_sans_htmx_la_page_2_est_une_page_complete(client):
    _published(25)

    html = client.get(HOME, {"page": 2}).content.decode()

    assert "<html" in html
    assert len(_cards(html)) == 5


def test_une_page_inexistante_ne_plante_pas(client):
    _published(3)

    assert client.get(HOME, {"page": "abc"}).status_code == 200
    assert client.get(HOME, {"page": 99}, headers=HTMX).status_code == 200


def test_seules_les_annonces_publiees_sont_listees_les_plus_recentes_d_abord(client):
    older, newer = _published(2)[::-1]
    ListingFactory()  # brouillon
    ListingFactory(status=ListingStatus.REMOVED)
    ListingFactory(status=ListingStatus.SOLD, published_at=timezone.now())

    cards = _cards(client.get(HOME).content.decode())

    assert cards == [newer.get_absolute_url(), older.get_absolute_url()]


def test_le_nombre_de_requetes_ne_depend_pas_du_nombre_d_annonces(client):
    def queries_for(n):
        Listing.objects.all().delete()
        for listing in _published(n):
            _photo(listing)
        with CaptureQueriesContext(connection) as ctx:
            client.get(HOME)
        return len(ctx.captured_queries)

    assert queries_for(3) == queries_for(20)


def test_accueil_vide(client):
    html = client.get(HOME).content.decode()

    assert "Aucune annonce pour l'instant" in html


# --- Carte annonce -----------------------------------------------------------------------


def test_les_miniatures_ont_leurs_dimensions_et_les_suivantes_sont_differees(client):
    for listing in _published(6):
        _photo(listing)

    html = client.get(HOME).content.decode()

    images = re.findall(r'<img class="sg-card__media"[^>]*>', html)
    assert len(images) == 6
    assert all('width="400" height="300"' in img for img in images)
    assert ['loading="lazy"' in img for img in images] == [False] * 4 + [True] * 2


def test_une_annonce_sans_photo_garde_la_place_de_l_image(client):
    _published(1)

    html = client.get(HOME).content.decode()

    assert '<div class="sg-card__media">' in html


def test_prix_formate_et_a_debattre(client):
    _published(1, price=45000)
    _published(1, price=None)

    html = client.get(HOME).content.decode()

    assert "45 000\xa0FCFA" in html
    assert "À débattre" in html


def test_baisse_de_prix_recente_ancien_prix_barre_et_badge(client):
    listing = _published(1, price=55000)[0]
    services.update_price(listing, 45000)

    html = client.get(HOME).content.decode()

    assert "Prix en baisse" in html
    assert '<s class="sg-was"><span class="sr-only">au lieu de </span>55 000</s>' in html


def test_la_baisse_n_est_plus_signalee_apres_14_jours(client):
    listing = _published(1, price=55000)[0]
    services.update_price(listing, 45000)
    Listing.objects.filter(pk=listing.pk).update(
        price_dropped_at=timezone.now() - timedelta(days=15),
        published_at=timezone.now() - timedelta(days=20),
    )

    html = client.get(HOME).content.decode()

    assert "Prix en baisse" not in html
    assert "sg-was" not in html


def test_badge_nouveau_les_24_premieres_heures(client):
    ListingFactory(published=True, published_at=timezone.now() - timedelta(hours=2))
    ListingFactory(published=True, published_at=timezone.now() - timedelta(days=2))

    html = client.get(HOME).content.decode()

    assert html.count(">Nouveau</span>") == 1


# --- Page de l'annonce -------------------------------------------------------------------


def test_la_page_de_l_annonce_s_affiche(client):
    listing = ListingFactory(
        published=True, title="Vélo de course Peugeot", price=45000,
        payment_methods=["mobile_money", "cash_on_delivery"],
    )  # fmt: skip

    response = client.get(listing.get_absolute_url())

    html = response.content.decode()
    assert response.status_code == 200
    assert listing.get_absolute_url() == f"/annonce/{listing.pk}-velo-de-course-peugeot/"
    assert "Vélo de course Peugeot" in html
    assert "Mobile money" in html
    assert "Paiement à la livraison" in html
    assert listing.user.display_name in html
    assert "ne payez jamais avant d'avoir vu l'objet" in html


def test_un_slug_errone_redirige_vers_la_bonne_adresse(client):
    listing = ListingFactory(published=True, title="Canapé trois places")

    response = client.get(reverse("listings:detail", kwargs={"pk": listing.pk, "slug": "autre"}))

    assert response.status_code == 301
    assert response.url == listing.get_absolute_url()


@pytest.mark.parametrize("status", [ListingStatus.DRAFT, ListingStatus.REMOVED])
def test_brouillon_et_annonce_retiree_sont_introuvables(client, status):
    listing = ListingFactory(
        status=status, published_at=timezone.now() if status == ListingStatus.REMOVED else None
    )

    assert client.get(listing.get_absolute_url()).status_code == 404


def test_une_annonce_inexistante_est_introuvable(client):
    assert client.get("/annonce/999999-rien/").status_code == 404


def test_une_annonce_vendue_reste_visible_avec_un_bandeau(client):
    listing = ListingFactory(published=True)
    services.mark_sold(listing)

    html = client.get(listing.get_absolute_url()).content.decode()

    assert "Annonce vendue" in html
    assert "sg-badge--sold" in html


def test_la_description_est_du_texte_brut(client):
    listing = ListingFactory(
        published=True, description="Bon état\n<script>alert('pirate')</script>"
    )

    html = client.get(listing.get_absolute_url()).content.decode()

    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "Bon état<br>" in html


def test_la_galerie_reserve_la_place_de_chaque_photo(client):
    listing = ListingFactory(published=True)
    _photo(listing, order=0, width=1200, height=800)
    _photo(listing, order=1, width=900, height=1200)

    html = client.get(listing.get_absolute_url()).content.decode()

    images = re.findall(r'<img src="[^"]+-1200\.webp"[^>]*>', html)
    assert len(images) == 2
    assert 'width="1200" height="800"' in images[0]
    assert 'width="900" height="1200"' in images[1]
    assert 'loading="lazy"' not in images[0]
    assert 'loading="lazy"' in images[1]
    assert "2 photos" in html


def test_la_page_annonce_a_la_baisse_de_prix(client):
    listing = ListingFactory(published=True, price=55000)
    services.update_price(listing, 45000)

    html = client.get(listing.get_absolute_url()).content.decode()

    assert "Prix en baisse" in html
    assert "55 000\xa0FCFA</s>" in html


def test_la_carte_et_la_page_affichent_le_lieu_precis(client):
    listing = ListingFactory(published=True, city__name="Ségou", distance_km=15)

    home = client.get(HOME).content.decode()
    page = client.get(listing.get_absolute_url()).content.decode()

    assert "À 15 km de Ségou" in home
    assert "À 15 km de Ségou" in page
