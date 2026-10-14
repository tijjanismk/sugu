"""Dépôt d'annonce avec photos (ticket #7) : parcours complet côté serveur."""

import time
from pathlib import Path

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.listings import forms as listing_forms
from apps.listings import services
from apps.listings.models import Listing, ListingStatus, Photo

from .factories import CategoryFactory, CityFactory
from .images import exif_with_gps, image_bytes, uploaded

pytestmark = pytest.mark.django_db

URL = reverse("listings:create")


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def seller(client):
    user = UserFactory()
    client.force_login(user)
    return user


@pytest.fixture
def categories():
    phones = CategoryFactory(name="Téléphones")
    return phones, CategoryFactory(name="Smartphones", parent=phones)


@pytest.fixture
def city():
    return CityFactory(name="Bamako")


def _data(categories, city, photos, **extra):
    _, smartphones = categories
    return {
        "title": "Samsung Galaxy A15",
        "category": smartphones.pk,
        "city": city.pk,
        "price": "85 000",
        "payment_methods": ["mobile_money"],
        "description": "Écran sans rayure, avec chargeur.",
        "photos": photos,
        **extra,
    }


def _photos(n, **kwargs):
    return [uploaded(name=f"IMG_{i}.jpg", width=3000, height=2000, **kwargs) for i in range(n)]


def _stored_files(media: Path):
    return sorted(p for p in media.rglob("*") if p.is_file())


# --- Accès -------------------------------------------------------------------------------


def test_deposer_exige_d_etre_connecte(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_le_formulaire_propose_les_sous_categories_par_groupe(client, seller, categories, city):
    html = client.get(URL).content.decode()

    assert '<optgroup label="Téléphones">' in html
    assert "Smartphones" in html
    assert 'enctype="multipart/form-data"' in html


def test_le_lien_deposer_de_la_navigation_mene_au_formulaire(client):
    html = client.get(reverse("core:home")).content.decode()

    assert f'class="sg-bottomnav__post" href="{URL}"' in html


# --- Dépôt réussi ------------------------------------------------------------------------


def test_une_annonce_avec_3_photos_est_creee_en_moins_de_5_s(
    client, seller, categories, city, _media
):
    data = _data(categories, city, _photos(3))  # images générées hors chronométrage
    start = time.perf_counter()
    response = client.post(URL, data)
    elapsed = time.perf_counter() - start

    assert response.status_code == 302, response.context["form"].errors
    assert response.url == reverse("core:home")
    assert elapsed < 5, f"dépôt en {elapsed:.2f} s"

    listing = Listing.objects.get()
    assert listing.user == seller
    assert listing.status == ListingStatus.PUBLISHED
    assert listing.published_at is not None
    assert listing.price == 85000
    assert listing.payment_methods == ["mobile_money"]
    assert [p.order for p in listing.photos.all()] == [0, 1, 2]
    assert all((p.width, p.height) == (1200, 800) for p in listing.photos.all())


def test_seules_les_versions_webp_sont_stockees(client, seller, categories, city, _media):
    client.post(URL, _data(categories, city, _photos(2)))

    files = _stored_files(_media)
    assert len(files) == 4  # 2 photos × (1200 px + miniature)
    assert all(f.suffix == ".webp" for f in files)
    assert not any("IMG_" in f.name for f in files)  # aucun original, même renommé


def test_les_photos_stockees_n_ont_plus_de_gps(client, seller, categories, city, _media):
    photo = uploaded(name="IMG_gps.jpg", content=image_bytes(exif=exif_with_gps()))

    client.post(URL, _data(categories, city, [photo]))

    for path in _stored_files(_media):
        assert b"Exif" not in path.read_bytes()


def test_prix_vide_signifie_a_debattre(client, seller, categories, city):
    client.post(URL, _data(categories, city, _photos(1), price=""))

    assert Listing.objects.get().price is None


def test_un_message_confirme_la_publication(client, seller, categories, city):
    response = client.post(URL, _data(categories, city, _photos(1)), follow=True)

    assert "Annonce publiée" in response.content.decode()


# --- Refus -------------------------------------------------------------------------------


def _refused(client, data):
    response = client.post(URL, data)
    assert response.status_code == 200
    assert not Listing.objects.exists()
    return response.context["form"]


def test_un_fichier_qui_n_est_pas_une_image_est_rejete(client, seller, categories, city, _media):
    faux = uploaded(name="photo.jpg", content=b"%PDF-1.7 pas une image")

    form = _refused(client, _data(categories, city, [_photos(1)[0], faux]))

    assert "Photo 2" in str(form.errors["photos"])
    assert _stored_files(_media) == []  # rien d'écrit, pas même la photo valide


def test_au_moins_une_photo(client, seller, categories, city):
    form = _refused(client, _data(categories, city, []))

    assert form.errors["photos"]


def test_six_photos_au_plus(client, seller, categories, city):
    form = _refused(client, _data(categories, city, _photos(7)))

    assert "6 photos au plus" in str(form.errors["photos"])


def test_une_photo_trop_lourde_est_refusee(client, seller, categories, city, monkeypatch):
    monkeypatch.setattr(listing_forms, "MAX_UPLOAD_BYTES", 1000)

    form = _refused(client, _data(categories, city, _photos(1)))

    assert "8 Mo au plus" in str(form.errors["photos"])


def test_une_categorie_principale_est_refusee(client, seller, categories, city):
    phones, _ = categories

    form = _refused(client, _data(categories, city, _photos(1), category=phones.pk))

    assert form.errors["category"]


def test_un_prix_en_lettres_est_refuse(client, seller, categories, city):
    form = _refused(client, _data(categories, city, _photos(1), price="cinquante mille"))

    assert form.errors["price"]


def test_un_mode_de_reglement_inconnu_est_refuse(client, seller, categories, city):
    form = _refused(client, _data(categories, city, _photos(1), payment_methods=["cheque"]))

    assert form.errors["payment_methods"]


# --- Limitation de débit -----------------------------------------------------------------


def test_le_depot_est_limite(client, seller, categories, city, settings):
    settings.ACCOUNT_RATE_LIMITS = {**settings.ACCOUNT_RATE_LIMITS, "listing_create": "1/h/user"}
    assert client.post(URL, _data(categories, city, _photos(1))).status_code == 302

    response = client.post(URL, _data(categories, city, _photos(1), title="Deuxième"))

    assert response.status_code == 429
    assert Listing.objects.count() == 1


def test_une_erreur_de_formulaire_n_epuise_pas_le_quota(client, seller, categories, city, settings):
    settings.ACCOUNT_RATE_LIMITS = {**settings.ACCOUNT_RATE_LIMITS, "listing_create": "1/h/user"}
    client.post(URL, _data(categories, city, []))  # refusé : aucune photo

    response = client.post(URL, _data(categories, city, _photos(1)))

    assert response.status_code == 302


# --- Fichiers et transactions ------------------------------------------------------------


def test_supprimer_une_photo_supprime_ses_fichiers(
    client, seller, categories, city, _media, django_capture_on_commit_callbacks
):
    client.post(URL, _data(categories, city, _photos(2)))
    photo = Photo.objects.first()

    with django_capture_on_commit_callbacks(execute=True):
        photo.delete()

    assert len(_stored_files(_media)) == 2


def test_supprimer_l_annonce_supprime_tous_les_fichiers(
    client, seller, categories, city, _media, django_capture_on_commit_callbacks
):
    client.post(URL, _data(categories, city, _photos(3)))

    with django_capture_on_commit_callbacks(execute=True):
        Listing.objects.get().delete()

    assert _stored_files(_media) == []


def test_un_echec_en_base_ne_laisse_aucun_fichier(
    client, seller, categories, city, _media, monkeypatch
):
    def panne(listing):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(services, "publish", panne)

    with pytest.raises(RuntimeError):
        client.post(URL, _data(categories, city, _photos(2)))

    assert not Listing.objects.exists()
    assert _stored_files(_media) == []
