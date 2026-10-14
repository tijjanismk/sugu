"""Profil et contact (ticket #13) : profil, téléphone réservé aux connectés, déconnexion des
autres appareils, suppression de compte par anonymisation."""

import pytest
from allauth.account.models import EmailAddress
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.templatetags.sugu_format import month_year, phone
from apps.favorites.models import Favorite
from apps.listings import services as listing_services
from apps.listings.models import ListingStatus
from apps.listings.tests.factories import CityFactory, ListingFactory
from apps.messaging import services as messaging
from apps.messaging.models import Message

from .factories import MOT_DE_PASSE, UserFactory

pytestmark = pytest.mark.django_db

PROFILE = "account_profile"


@pytest.fixture
def seller():
    return UserFactory(display_name="Aminata Koné", phone="+22376123456")


@pytest.fixture
def listing(seller):
    return ListingFactory(user=seller, published=True, title="Vélo de course Peugeot")


def _logged_in(user):
    client = Client()
    client.force_login(user)
    return client


def _is_logged_in(client):
    return "_auth_user_id" in client.session


# --- Profil --------------------------------------------------------------------------------


def test_profil_exige_la_connexion(client):
    response = client.get(reverse(PROFILE))

    assert response.url.startswith(reverse("account_login"))


def test_profil_modifie_nom_telephone_et_ville(seller):
    bamako = CityFactory(name="Bamako")
    client = _logged_in(seller)

    response = client.post(
        reverse(PROFILE),
        {"display_name": "Aminata K.", "phone": "+223 76-12.34 56", "city": bamako.pk},
    )

    assert response.status_code == 302
    seller.refresh_from_db()
    assert (seller.display_name, seller.phone, seller.city) == (
        "Aminata K.",
        "+22376123456",
        bamako,
    )


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"display_name": "Aminata", "phone": "12ab"}, "Numéro invalide"),
        ({"display_name": "Aminata", "phone": "1234"}, "Numéro invalide"),
        ({"display_name": "Voir jiji.ml", "phone": ""}, "Les liens vers d"),
        ({"display_name": "", "phone": ""}, "Ce champ est obligatoire"),
    ],
)
def test_profil_valeurs_refusees(seller, data, error):
    response = _logged_in(seller).post(reverse(PROFILE), data)

    assert response.status_code == 200
    assert error in response.content.decode()
    seller.refresh_from_db()
    assert seller.display_name == "Aminata Koné"


def test_le_profil_ne_touche_que_le_mien(seller):
    other = UserFactory(display_name="Moussa")

    _logged_in(seller).post(reverse(PROFILE), {"display_name": "Changé", "phone": ""})

    other.refresh_from_db()
    assert other.display_name == "Moussa"


def test_inscription_normalise_le_telephone(client):
    client.post(
        reverse("account_signup"),
        {
            "display_name": "Awa",
            "email": "awa@example.ml",
            "phone": "76 12 34 56",
            "password1": MOT_DE_PASSE,
        },
    )

    assert UserFactory._meta.model.objects.get(email="awa@example.ml").phone == "76123456"


# --- Téléphone sur l'annonce --------------------------------------------------------------


def test_telephone_masque_aux_visiteurs(client, listing):
    html = client.get(listing.get_absolute_url()).content.decode()

    # Ni le numéro enregistré ni sa forme affichée : rien dans la page, pas même caché.
    assert "22376123456" not in html
    assert "76 12 34 56" not in html
    assert "tel:" not in html
    assert "Se connecter pour voir le numéro" in html
    assert f"?next={listing.get_absolute_url()}" in html


def test_telephone_visible_une_fois_connecte(listing):
    html = _logged_in(UserFactory()).get(listing.get_absolute_url()).content.decode()

    assert 'href="tel:+22376123456"' in html
    assert "+223 76 12 34 56" in html
    assert "Se connecter pour voir le numéro" not in html


def test_vendeur_sans_telephone(client):
    quiet = ListingFactory(user=UserFactory(phone=""), published=True)

    html = client.get(quiet.get_absolute_url()).content.decode()

    assert "Se connecter pour voir le numéro" not in html
    assert "tel:" not in html


def test_ligne_vendeur(client, seller, listing):
    ListingFactory(user=seller, published=True)
    ListingFactory(user=seller, status=ListingStatus.DRAFT)

    html = client.get(listing.get_absolute_url()).content.decode()

    assert '<p class="sg-seller__name">Aminata Koné</p>' in html
    assert f"Membre depuis {month_year(seller.date_joined)} · 2 annonces" in html
    assert ">AK<" in html


def test_format_du_telephone():
    assert phone("+22376123456") == "+223 76 12 34 56"
    assert phone("76123456") == "76 12 34 56"
    assert phone("+2250712345678") == "+2250712345678"


def test_mois_annee():
    assert month_year(timezone.datetime(2026, 10, 3, tzinfo=timezone.UTC)) == "oct. 2026"


# --- Déconnecter mes autres appareils -----------------------------------------------------


def test_deconnecter_les_autres_appareils(seller):
    phone, laptop = _logged_in(seller), _logged_in(seller)

    response = laptop.post(reverse("account_sign_out_others"))

    assert response.status_code == 302
    assert phone.get(reverse(PROFILE)).status_code == 302  # renvoyé vers la connexion
    assert not _is_logged_in(phone)
    assert laptop.get(reverse(PROFILE)).status_code == 200  # celui-ci reste connecté


def test_deconnecter_partout_par_get_ne_fait_rien(seller):
    phone, laptop = _logged_in(seller), _logged_in(seller)

    assert laptop.get(reverse("account_sign_out_others")).status_code == 405
    assert phone.get(reverse(PROFILE)).status_code == 200


def test_sessions_existantes_valides_tant_que_la_version_vaut_zero(seller):
    # Le hachage de session est celui de Django tant que session_version vaut 0 : la mise en
    # production de ce ticket ne déconnecte personne.
    from django.contrib.auth.base_user import AbstractBaseUser

    assert seller.get_session_auth_hash() == AbstractBaseUser._get_session_auth_hash(seller)


# --- Suppression du compte ----------------------------------------------------------------


@pytest.fixture
def history(seller, listing):
    """Un acheteur a écrit au vendeur, qui a répondu ; le vendeur a un favori."""
    buyer = UserFactory(display_name="Moussa")
    conversation = messaging.start_conversation(buyer, listing, "Il est disponible ?")
    messaging.send_message(conversation, seller, "Oui, passez demain.")
    Favorite.objects.create(user=seller, listing=ListingFactory(published=True))
    sold = ListingFactory(user=seller, published=True)
    listing_services.mark_sold(sold)
    return {"buyer": buyer, "conversation": conversation, "sold": sold}


def test_mauvais_mot_de_passe_rien_ne_change(seller, listing):
    client = _logged_in(seller)

    response = client.post(reverse("account_delete"), {"password": "faux"})

    assert "Mot de passe incorrect." in response.content.decode()
    seller.refresh_from_db()
    assert seller.is_active and not seller.is_deleted
    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED


def test_suppression_anonymise_sans_detruire(seller, listing, history):
    email = seller.email
    client = _logged_in(seller)

    response = client.post(reverse("account_delete"), {"password": MOT_DE_PASSE})

    assert response.url == reverse("core:home")
    assert not _is_logged_in(client)
    seller.refresh_from_db()
    assert seller.display_name == "Compte supprimé"
    assert (seller.phone, seller.city, seller.is_active) == ("", None, False)
    assert seller.email != email and seller.email.endswith("@sugu.invalid")
    assert not seller.has_usable_password()
    assert seller.deleted_at is not None
    # Annonces retirées mais gardées, messages gardés, favoris et adresses supprimés.
    for item in (listing, history["sold"]):
        item.refresh_from_db()
        assert item.status == ListingStatus.REMOVED
    assert Message.objects.filter(sender=seller).count() == 1
    assert history["conversation"].messages.count() == 2
    assert not Favorite.objects.filter(user=seller).exists()
    assert not EmailAddress.objects.filter(user=seller).exists()


def test_apres_suppression_plus_de_connexion_et_email_libre(client, seller, history):
    email = seller.email
    _logged_in(seller).post(reverse("account_delete"), {"password": MOT_DE_PASSE})

    client.post(reverse("account_login"), {"login": email, "password": MOT_DE_PASSE})
    assert not _is_logged_in(client)

    client.post(
        reverse("account_signup"),
        {"display_name": "Nouvelle", "email": email, "phone": "", "password1": MOT_DE_PASSE},
    )
    assert UserFactory._meta.model.objects.filter(email=email).exists()


def test_le_correspondant_garde_la_conversation_sans_pouvoir_ecrire(seller, history):
    _logged_in(seller).post(reverse("account_delete"), {"password": MOT_DE_PASSE})
    conversation = history["conversation"]
    buyer = _logged_in(history["buyer"])

    html = buyer.get(conversation.get_absolute_url()).content.decode()

    assert "Oui, passez demain." in html
    assert "Compte supprimé" in html
    assert "vous ne pouvez plus lui écrire" in html
    assert 'name="body"' not in html
    assert buyer.post(conversation.get_absolute_url(), {"body": "Allô ?"}).status_code == 403
    assert conversation.messages.count() == 2


def test_suppression_par_get_ne_supprime_pas(seller):
    response = _logged_in(seller).get(reverse("account_delete"))

    assert response.status_code == 200
    seller.refresh_from_db()
    assert not seller.is_deleted


def test_essais_de_mot_de_passe_limites(seller, settings):
    settings.ACCOUNT_RATE_LIMITS = {**settings.ACCOUNT_RATE_LIMITS, "account_delete": "2/h/user"}
    client = _logged_in(seller)
    for _ in range(2):
        client.post(reverse("account_delete"), {"password": "faux"})

    response = client.post(reverse("account_delete"), {"password": MOT_DE_PASSE})

    assert response.status_code == 429
    seller.refresh_from_db()
    assert not seller.is_deleted


def test_barre_du_haut_lien_profil(seller):
    html = _logged_in(seller).get(reverse("core:home")).content.decode()

    assert f'href="{reverse(PROFILE)}"' in html
