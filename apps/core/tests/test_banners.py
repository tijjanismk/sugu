"""Bannières de l'accueil (ticket #8, ajout du 2026-10-17)."""

import io
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.core import banners
from apps.core.models import Banner
from apps.listings.tests.images import exif_with_gps, uploaded

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser(
        email="admin@example.ml", password="Baobab-2026-solide", display_name="Admin"
    )
    client.force_login(admin)
    return client


def make_banner(**fields) -> Banner:
    banner = Banner(alt=fields.pop("alt", "Vendez gratuitement en 2 minutes"), **fields)
    banners.set_image(banner, banners.process_banner(uploaded(width=1200, height=600)))
    banner.save()
    return banner


# Traitement de l'image


def test_image_reencodee_en_webp_en_deux_largeurs_sans_metadonnees():
    processed = banners.process_banner(
        uploaded(width=2400, height=1200, exif=exif_with_gps(orientation=1))
    )

    large = Image.open(io.BytesIO(processed.large.read()))
    small = Image.open(io.BytesIO(processed.small.read()))
    assert (large.format, large.size) == ("WEBP", (1200, 600))
    assert small.size == (600, 300)
    assert not large.getexif() and "exif" not in large.info
    assert (processed.width, processed.height) == (1200, 600)


def test_une_petite_image_nest_jamais_agrandie():
    processed = banners.process_banner(uploaded(width=800, height=400))

    assert Image.open(io.BytesIO(processed.large.read())).size == (800, 400)
    assert Image.open(io.BytesIO(processed.small.read())).size == (600, 300)


@pytest.mark.parametrize("size", [(1000, 1000), (1200, 400), (800, 600)])
def test_un_autre_format_que_2_1_est_refuse_sans_recadrer(size):
    with pytest.raises(ValidationError) as error:
        banners.process_banner(uploaded(width=size[0], height=size[1]))

    assert error.value.code == "ratio"
    assert f"{size[0]} × {size[1]} px" in error.value.message


def test_tolerance_de_10_pourcent_sur_le_format():
    banners.process_banner(uploaded(width=1200, height=560))  # 2,14:1, accepté


def test_une_image_trop_petite_est_refusee():
    with pytest.raises(ValidationError) as error:
        banners.process_banner(uploaded(width=500, height=250))

    assert error.value.code == "too_small"


def test_un_fichier_qui_nest_pas_une_image_est_refuse():
    with pytest.raises(ValidationError):
        banners.process_banner(uploaded(name="banniere.jpg", content=b"pas une image"))


def test_remplacer_limage_efface_les_anciens_fichiers(_media, django_capture_on_commit_callbacks):
    banner = make_banner()
    old = [banner.image.name, banner.image_small.name]

    with django_capture_on_commit_callbacks(execute=True):
        banners.set_image(banner, banners.process_banner(uploaded(width=1200, height=600)))
        banner.save()

    assert all(not (_media / name).exists() for name in old)
    assert (_media / banner.image.name).exists() and (_media / banner.image_small.name).exists()


def test_supprimer_la_banniere_efface_ses_fichiers(_media, django_capture_on_commit_callbacks):
    banner = make_banner()
    names = [banner.image.name, banner.image_small.name]

    with django_capture_on_commit_callbacks(execute=True):
        banner.delete()

    assert all(not (_media / name).exists() for name in names)


# Lien et dates


@pytest.mark.parametrize(
    "link", ["/categorie/vehicules/", "/annonce/2-habit-femme/", "https://example.ml/promo"]
)
def test_liens_acceptes(link):
    Banner(alt="x", link=link).clean_fields(exclude=["image", "image_small", "width", "height"])


@pytest.mark.parametrize(
    "link", ["javascript:alert(1)", "//autre-site.com", "http://example.ml", "https://"]
)
def test_liens_refuses(link):
    with pytest.raises(ValidationError) as error:
        Banner(alt="x", link=link).clean_fields(exclude=["image", "image_small", "width", "height"])

    assert "link" in error.value.message_dict


def test_la_fin_doit_venir_apres_le_debut():
    now = timezone.now()
    banner = Banner(alt="x", starts_at=now, ends_at=now - timedelta(days=1))

    with pytest.raises(ValidationError):
        banner.clean()
    with pytest.raises(IntegrityError):
        make_banner(starts_at=now, ends_at=now - timedelta(days=1))


# Sélection et affichage


def test_seules_les_bannieres_actives_et_dans_leur_periode_sont_affichees():
    now = timezone.now()
    shown = make_banner(alt="Affichée")
    make_banner(alt="Désactivée", is_active=False)
    make_banner(alt="Pas encore", starts_at=now + timedelta(days=1))
    make_banner(alt="Terminée", ends_at=now - timedelta(minutes=1))
    in_window = make_banner(
        alt="Dans sa période", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1)
    )

    assert {b.pk for b in banners.active_banners()} == {shown.pk, in_window.pk}


def test_ordre_choisi_et_cinq_au_plus():
    for order in [3, 1, 2, 0, 5, 4]:
        make_banner(alt=f"Bannière {order}", order=order)

    assert [b.order for b in banners.active_banners()] == [0, 1, 2, 3, 4]


def test_accueil_affiche_les_bannieres(client):
    make_banner(alt="Vendez gratuitement", link="/deposer/")
    make_banner(alt="Sans lien", order=1)

    html = client.get(reverse("core:home")).content.decode()

    assert 'aria-label="En ce moment sur Sugu"' in html
    assert '<a class="sg-banner" href="/deposer/">' in html
    assert 'alt="Vendez gratuitement"' in html and 'alt="Sans lien"' in html
    assert '<div class="sg-banner">' in html
    assert 'width="1200" height="600"' in html  # place réservée, pas de saut de page
    assert html.count('fetchpriority="high"') == 1  # seule la première est prioritaire
    assert html.count('loading="lazy"') >= 1
    assert "600w" in html and "1200w" in html
    # La bannière « Installer l'application » reste en place, sous les bannières.
    assert html.index("sg-banners") < html.index("data-install-banner")


def test_sans_banniere_rien_nest_affiche(client):
    make_banner(is_active=False)

    html = client.get(reverse("core:home")).content.decode()

    assert "sg-banners" not in html


def test_voir_plus_ne_renvoie_pas_les_bannieres(client):
    make_banner()

    html = client.get(reverse("core:home"), {"page": 2}, headers={"HX-Request": "true"})

    assert "sg-banners" not in html.content.decode()


# Admin


def test_ajout_dune_banniere_depuis_ladmin(admin_client):
    response = admin_client.post(
        reverse("admin:core_banner_add"),
        {
            "upload": uploaded(width=1600, height=800),
            "alt": "Vendez gratuitement en 2 minutes",
            "link": "/deposer/",
            "is_active": "on",
            "order": "0",
        },
    )

    assert response.status_code == 302
    banner = Banner.objects.get()
    assert banner.image.name.endswith("-1200.webp") and banner.image_small.name.endswith(
        "-600.webp"
    )
    assert (banner.width, banner.height) == (1200, 600)
    assert admin_client.get(reverse("admin:core_banner_changelist")).status_code == 200
    assert (
        admin_client.get(reverse("admin:core_banner_change", args=[banner.pk])).status_code == 200
    )


def test_ladmin_refuse_une_image_au_mauvais_format(admin_client):
    response = admin_client.post(
        reverse("admin:core_banner_add"),
        {"upload": uploaded(width=1000, height=1000), "alt": "Carrée", "order": "0"},
    )

    assert response.status_code == 200
    assert "deux fois plus large que haute" in response.content.decode()
    assert not Banner.objects.exists()


def test_ladmin_exige_une_image_a_la_creation(admin_client):
    response = admin_client.post(
        reverse("admin:core_banner_add"), {"alt": "Sans image", "order": "0"}
    )

    assert response.status_code == 200
    assert "Ajoutez une image." in response.content.decode()


def test_modifier_sans_nouvelle_image_garde_limage(admin_client):
    banner = make_banner()
    name = banner.image.name

    response = admin_client.post(
        reverse("admin:core_banner_change", args=[banner.pk]),
        {"alt": "Nouveau texte", "link": "", "is_active": "on", "order": "2"},
    )

    assert response.status_code == 302
    banner.refresh_from_db()
    assert (banner.alt, banner.order, banner.image.name) == ("Nouveau texte", 2, name)


def test_un_membre_ordinaire_na_pas_acces_a_ladmin_des_bannieres(client):
    user = User.objects.create_user(
        email="membre@example.ml", password="Baobab-2026-solide", display_name="Awa"
    )
    client.force_login(user)

    response = client.get(reverse("admin:core_banner_add"))

    assert response.status_code == 302  # renvoyé vers la connexion de l'admin
    assert not Banner.objects.exists()
