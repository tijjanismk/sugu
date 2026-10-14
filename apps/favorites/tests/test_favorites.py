"""Favoris (ticket #11) : bascule htmx et sans JavaScript, connexion obligatoire, unicité,
page « Mes favoris »."""

import pytest
from django.db import IntegrityError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.favorites import services
from apps.favorites.models import Favorite
from apps.listings.models import ListingStatus
from apps.listings.tests.factories import ListingFactory

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def buyer():
    return UserFactory()


@pytest.fixture
def listing():
    return ListingFactory(published=True, title="Vélo de course Peugeot")


@pytest.fixture
def buyer_client(client, buyer):
    client.force_login(buyer)
    return client


def _set_url(listing):
    return reverse("favorites:set", args=[listing.pk])


# --- Modèle et service -------------------------------------------------------------------


def test_un_favori_est_unique_par_utilisateur_et_annonce(buyer, listing):
    Favorite.objects.create(user=buyer, listing=listing)
    with pytest.raises(IntegrityError):
        Favorite.objects.create(user=buyer, listing=listing)


def test_mettre_deux_fois_en_favori_ne_cree_quune_ligne(buyer, listing):
    services.set_favorite(buyer, listing, True)
    services.set_favorite(buyer, listing, True)
    assert Favorite.objects.filter(user=buyer, listing=listing).count() == 1


def test_retirer_un_favori_absent_ne_fait_rien(buyer, listing):
    assert services.set_favorite(buyer, listing, False) is False
    assert not Favorite.objects.exists()


# --- Bascule ----------------------------------------------------------------------------


def test_bascule_htmx_renvoie_le_bouton_seul_et_actif(buyer_client, buyer, listing):
    response = buyer_client.post(_set_url(listing), {"on": "1", "variant": "card"}, headers=HTMX)

    assert response.status_code == 200
    html = response.content.decode()
    assert "<html" not in html
    assert 'aria-pressed="true"' in html
    assert 'name="on" value="0"' in html  # le prochain clic retire le favori
    assert "sg-card__fav" in html
    assert Favorite.objects.filter(user=buyer, listing=listing).exists()


def test_bascule_htmx_retire_le_favori(buyer_client, buyer, listing):
    Favorite.objects.create(user=buyer, listing=listing)

    response = buyer_client.post(_set_url(listing), {"on": "0", "variant": "bar"}, headers=HTMX)

    html = response.content.decode()
    assert 'aria-pressed="false"' in html
    assert "sg-fav" in html  # la variante de la barre du haut est conservée
    assert not Favorite.objects.exists()


def test_double_clic_ne_change_rien(buyer_client, buyer, listing):
    for _ in range(2):
        buyer_client.post(_set_url(listing), {"on": "1"}, headers=HTMX)
    assert Favorite.objects.filter(user=buyer, listing=listing).count() == 1


def test_sans_javascript_retour_a_la_page_dorigine(buyer_client, buyer, listing):
    response = buyer_client.post(_set_url(listing), {"on": "1", "next": "/recherche/?q=velo"})

    assert response.status_code == 302
    assert response.url == "/recherche/?q=velo"
    assert Favorite.objects.filter(user=buyer, listing=listing).exists()


def test_une_adresse_dun_autre_site_est_ignoree(buyer_client, listing):
    response = buyer_client.post(_set_url(listing), {"on": "1", "next": "https://evil.example/"})

    assert response.url == listing.get_absolute_url()


def test_non_connecte_redirige_vers_la_connexion(client, listing):
    response = client.post(_set_url(listing), {"on": "1", "next": "/recherche/?q=velo"})

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))
    assert "next=/recherche/%3Fq%3Dvelo" in response.url
    assert not Favorite.objects.exists()


def test_non_connecte_en_htmx_redirige_la_page_entiere(client, listing):
    headers = {**HTMX, "HX-Current-URL": "http://testserver/?page=2"}

    response = client.post(_set_url(listing), {"on": "1"}, headers=headers)

    assert response.status_code == 200
    assert response["HX-Redirect"].startswith(reverse("account_login"))
    assert "next=/%3Fpage%3D2" in response["HX-Redirect"]
    assert not Favorite.objects.exists()


def test_get_refuse(buyer_client, listing):
    assert buyer_client.get(_set_url(listing)).status_code == 405
    assert not Favorite.objects.exists()


def test_jeton_csrf_obligatoire(buyer, listing):
    client = Client(enforce_csrf_checks=True)
    client.force_login(buyer)

    assert client.post(_set_url(listing), {"on": "1"}).status_code == 403
    assert not Favorite.objects.exists()


@pytest.mark.parametrize("status", [ListingStatus.DRAFT, ListingStatus.REMOVED])
def test_annonce_invisible_introuvable(buyer_client, status):
    hidden = ListingFactory(status=status)

    assert buyer_client.post(_set_url(hidden), {"on": "1"}).status_code == 404
    assert not Favorite.objects.exists()


# --- Cœurs affichés ------------------------------------------------------------------------


def test_le_coeur_est_actif_sur_les_cartes_de_laccueil(buyer_client, buyer, listing):
    other = ListingFactory(published=True)
    Favorite.objects.create(user=buyer, listing=listing)

    html = buyer_client.get(reverse("core:home")).content.decode()

    assert html.count('aria-pressed="true"') == 1
    assert html.count('aria-pressed="false"') == 1
    assert f"Ajouter aux favoris : {other.title}" in html


def test_pas_de_coeur_sur_ses_propres_annonces(client, listing):
    client.force_login(listing.user)

    home = client.get(reverse("core:home")).content.decode()
    detail = client.get(listing.get_absolute_url()).content.decode()

    assert reverse("favorites:set", args=[listing.pk]) not in home
    assert reverse("favorites:set", args=[listing.pk]) not in detail


def test_coeur_dans_la_barre_de_la_page_annonce(buyer_client, buyer, listing):
    Favorite.objects.create(user=buyer, listing=listing)

    html = buyer_client.get(listing.get_absolute_url()).content.decode()

    assert 'class="sg-btn sg-btn--icon sg-fav"' in html
    assert 'aria-pressed="true"' in html


def test_visiteur_voit_des_coeurs_inactifs(client, listing):
    html = client.get(reverse("core:home")).content.decode()

    assert 'aria-pressed="false"' in html
    assert 'aria-pressed="true"' not in html


def test_accueil_nombre_de_requetes_constant(buyer_client, buyer):
    def count_queries():
        with CaptureQueriesContext(connection) as ctx:
            assert buyer_client.get(reverse("core:home")).status_code == 200
        return len(ctx)

    for item in ListingFactory.create_batch(3, published=True):
        Favorite.objects.create(user=buyer, listing=item)
    few = count_queries()
    for item in ListingFactory.create_batch(6, published=True):
        Favorite.objects.create(user=buyer, listing=item)

    assert count_queries() == few


# --- Page « Mes favoris » ------------------------------------------------------------------


def test_mes_favoris_exige_la_connexion(client):
    response = client.get(reverse("favorites:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_mes_favoris_vide(buyer_client):
    html = buyer_client.get(reverse("favorites:list")).content.decode()

    assert "Aucun favori pour l'instant" in html


def test_mes_favoris_ne_montre_que_les_miens(buyer_client, buyer, listing):
    someone_else = UserFactory()
    theirs = ListingFactory(published=True, title="Frigo Samsung")
    Favorite.objects.create(user=buyer, listing=listing)
    Favorite.objects.create(user=someone_else, listing=theirs)

    html = buyer_client.get(reverse("favorites:list")).content.decode()

    assert listing.title in html
    assert theirs.title not in html


def test_mes_favoris_garde_les_vendues_et_cache_les_retirees(buyer_client, buyer):
    sold = ListingFactory(status=ListingStatus.SOLD, published_at=timezone.now(), title="Vendu")
    removed = ListingFactory(status=ListingStatus.REMOVED, title="Retiré du site")
    for item in (sold, removed):
        Favorite.objects.create(user=buyer, listing=item)

    html = buyer_client.get(reverse("favorites:list")).content.decode()

    assert "sg-card--sold" in html
    assert removed.title not in html


def test_mes_favoris_les_plus_recents_dabord(buyer_client, buyer):
    first, second = ListingFactory.create_batch(2, published=True)
    Favorite.objects.create(user=buyer, listing=second)
    Favorite.objects.create(user=buyer, listing=first)

    page = buyer_client.get(reverse("favorites:list")).context["page_obj"]

    assert list(page) == [first, second]


def test_mes_favoris_voir_plus_en_htmx(buyer_client, buyer, settings):
    for item in ListingFactory.create_batch(21, published=True):
        Favorite.objects.create(user=buyer, listing=item)

    response = buyer_client.get(reverse("favorites:list") + "?page=2", headers=HTMX)

    html = response.content.decode()
    assert "<html" not in html
    assert html.count("sg-card-slot") == 1


def test_lien_favoris_dans_la_barre_basse(client):
    html = client.get(reverse("core:home")).content.decode()

    assert f'href="{reverse("favorites:list")}"' in html


def test_sur_la_recherche_le_retour_garde_les_seuls_filtres_valides(client, listing):
    html = client.get(reverse("listings:search"), {"q": "velo", "price_min": "abc"}).content
    assert 'name="next" value="/recherche/?q=velo"' in html.decode()
