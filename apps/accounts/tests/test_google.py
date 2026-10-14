"""Connexion avec Google (ticket #3, ADR 0002). Google est simulé : l'échange du code contre le
jeton et le décodage du jeton d'identité sont remplacés par une réponse fixe."""

from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.test import Client
from django.urls import reverse

from apps.accounts import services
from apps.accounts.models import User

from .factories import MOT_DE_PASSE, UserFactory

pytestmark = pytest.mark.django_db

CLAIMS = {
    "iss": "https://accounts.google.com",
    "aud": "client-test",
    "sub": "108000000000000000001",
    "email": "awa.diallo@gmail.com",
    "email_verified": True,
    "name": "Awa Diallo",
    "given_name": "Awa",
    "family_name": "Diallo",
    "picture": "https://lh3.googleusercontent.com/a/photo",
}


@pytest.fixture
def google(settings):
    settings.GOOGLE_LOGIN_ENABLED = True
    settings.SOCIALACCOUNT_PROVIDERS = {
        "google": {
            **settings.SOCIALACCOUNT_PROVIDERS["google"],
            "APPS": [{"client_id": "client-test", "secret": "secret-test", "key": ""}],
        }
    }


def _start(client, next_url=None):
    data = {"next": next_url} if next_url else {}
    response = client.post(reverse("google_login"), data)
    assert response.status_code == 302
    return response


def _google_answers(client, claims=CLAIMS):
    """Parcours complet : départ vers Google, puis retour avec un code, Google simulé."""
    location = urlparse(_start(client).url)
    state = parse_qs(location.query)["state"][0]
    token = {"access_token": "jeton", "id_token": "jeton-identite", "expires_in": 3600}
    with (
        mock.patch(
            "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
            return_value=token,
        ),
        mock.patch(
            "allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._decode_id_token",
            return_value=dict(claims),
        ),
    ):
        return client.get(reverse("google_callback"), {"code": "code-google", "state": state})


def _logged_in_user(client):
    user_id = client.session.get("_auth_user_id")
    return User.objects.get(pk=user_id) if user_id else None


# --- Bouton ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("page", "field"), [("account_login", "login"), ("account_signup", "email")]
)
def test_bouton_en_tete_de_page(client, google, page, field):
    html = client.get(reverse(page)).content.decode()

    assert "Continuer avec Google" in html
    assert html.index("data-google-login") < html.index(f'name="{field}"')  # avant le formulaire
    assert f'action="{reverse("google_login")}"' in html


def test_bouton_masque_sans_identifiants(client):
    html = client.get(reverse("account_login")).content.decode()

    assert "Continuer avec Google" not in html


def test_la_redirection_part_dun_post_vers_google(client, google):
    location = urlparse(_start(client).url)
    query = parse_qs(location.query)

    assert location.netloc == "accounts.google.com"
    assert query["client_id"] == ["client-test"]
    assert set(query["scope"][0].split()) == {"openid", "email", "profile"}
    assert "code_challenge" in query  # PKCE
    assert query["redirect_uri"] == ["http://testserver/comptes/google/login/callback/"]


def test_un_lien_get_ne_part_pas_chez_google(client, google):
    response = client.get(reverse("google_login"))

    assert response.status_code == 200  # page de confirmation, pas de redirection


# --- Inscription et connexion -----------------------------------------------------------------


def test_inscription_dun_clic(client, google):
    response = _google_answers(client)

    assert response.status_code == 302
    user = _logged_in_user(client)
    assert user.email == "awa.diallo@gmail.com"
    assert user.display_name == "Awa Diallo"
    assert not user.has_usable_password()
    assert EmailAddress.objects.get(user=user).verified
    assert SocialAccount.objects.get(user=user).uid == CLAIMS["sub"]
    assert not SocialToken.objects.exists()  # aucun jeton Google conservé


def test_seconde_connexion_meme_compte(client, google):
    _google_answers(client)
    client.logout()

    _google_answers(client)

    assert User.objects.count() == 1
    assert _logged_in_user(client).email == CLAIMS["email"]


def test_adresse_verifiee_retrouve_son_compte(client, google):
    existing = UserFactory(email="awa.diallo@gmail.com", display_name="Awa D.")
    EmailAddress.objects.create(user=existing, email=existing.email, verified=True, primary=True)

    _google_answers(client)

    assert User.objects.count() == 1
    assert _logged_in_user(client) == existing
    existing.refresh_from_db()
    assert existing.display_name == "Awa D."  # le nom choisi n'est pas écrasé
    assert existing.check_password(MOT_DE_PASSE)  # le mot de passe reste utilisable


def test_compte_pirate_davance_neutralise(client, google):
    """Quelqu'un s'est inscrit avec l'adresse Gmail d'autrui (jamais vérifiée) et attend.
    Quand la vraie titulaire arrive par Google, elle récupère le compte : le mot de passe de
    l'intrus est effacé et sa session tombe (le hachage de session dépend du mot de passe)."""
    squatter = UserFactory(email="awa.diallo@gmail.com", display_name="Intrus")
    EmailAddress.objects.create(user=squatter, email=squatter.email, verified=False, primary=True)
    intruder = Client()
    intruder.force_login(squatter)

    _google_answers(client)

    assert _logged_in_user(client) == squatter
    squatter.refresh_from_db()
    assert not squatter.has_usable_password()
    assert intruder.get(reverse("account_profile")).status_code == 302  # déconnecté


def test_nom_absent_debut_de_ladresse(client, google):
    claims = {key: value for key, value in CLAIMS.items() if "name" not in key}

    _google_answers(client, claims)

    assert _logged_in_user(client).display_name == "awa.diallo"


def test_retour_a_la_page_demandee(client, google, settings):
    location = urlparse(_start(client, next_url="/deposer/").url)
    state = parse_qs(location.query)["state"][0]
    token = {"access_token": "jeton", "id_token": "jeton-identite", "expires_in": 3600}
    with (
        mock.patch(
            "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
            return_value=token,
        ),
        mock.patch(
            "allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._decode_id_token",
            return_value=dict(CLAIMS),
        ),
    ):
        response = client.get(reverse("google_callback"), {"code": "c", "state": state})

    assert response.url == "/deposer/"


def test_etat_falsifie_refuse(client, google):
    _start(client)

    response = client.get(reverse("google_callback"), {"code": "c", "state": "faux"})

    assert _logged_in_user(client) is None
    assert response.status_code == 401  # page d'erreur d'authentification
    assert "Google" in response.content.decode() or "connexion" in response.content.decode()
    assert not User.objects.exists()


def test_annulation_chez_google(client, google):
    location = urlparse(_start(client).url)
    state = parse_qs(location.query)["state"][0]

    response = client.get(reverse("google_callback"), {"error": "access_denied", "state": state})

    assert response.status_code in (200, 302)
    assert _logged_in_user(client) is None


# --- Suppression de compte (#13) ------------------------------------------------------------


def test_suppression_delie_le_compte_google(client, google):
    _google_answers(client)
    user = _logged_in_user(client)

    services.delete_account(user)

    assert not SocialAccount.objects.filter(user=user).exists()
    client.logout()
    _google_answers(client)  # même compte Google : un nouveau compte, pas l'ancien anonymisé
    assert _logged_in_user(client) != user
