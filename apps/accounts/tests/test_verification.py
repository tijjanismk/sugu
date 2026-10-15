"""Email confirmé obligatoire pour déposer et écrire à un vendeur (ticket #3, ajout du
2026-10-15)."""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse

from apps.listings.models import Listing
from apps.listings.tests.factories import ListingFactory
from apps.messaging.models import Conversation

from .factories import UserFactory

pytestmark = pytest.mark.django_db

CONFIRM = "Confirmez votre adresse email"


@pytest.fixture(autouse=True)
def _verification_on(settings):
    settings.VERIFIED_EMAIL_REQUIRED = True


def _user(client, *, verified):
    user = UserFactory()
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=verified)
    client.force_login(user)
    return user


def test_depot_bloque_sans_email_confirme_et_lien_renvoye(client):
    user = _user(client, verified=False)

    response = client.get(reverse("listings:create"))

    html = response.content.decode()
    assert CONFIRM in html
    assert user.email in html
    assert 'name="title"' not in html  # pas de formulaire de dépôt
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


def test_un_post_de_depot_ne_cree_rien(client):
    _user(client, verified=False)

    client.post(reverse("listings:create"), {"title": "Vélo"})

    assert not Listing.objects.exists()


def test_le_lien_nest_pas_renvoye_a_chaque_page(client):
    _user(client, verified=False)

    for _ in range(3):
        client.get(reverse("listings:create"))

    assert len(mail.outbox) == 1  # délai entre deux envois (allauth)


def test_depot_ouvert_avec_email_confirme(client):
    _user(client, verified=True)

    html = client.get(reverse("listings:create")).content.decode()

    assert CONFIRM not in html
    assert "Publier l&#x27;annonce" in html or "Publier l'annonce" in html


def test_compte_sans_adresse_enregistree(client):
    """Un compte créé par createsuperuser n'a pas de ligne EmailAddress : elle est créée et le
    lien part quand même."""
    user = UserFactory()
    client.force_login(user)

    html = client.get(reverse("listings:create")).content.decode()

    assert CONFIRM in html
    assert EmailAddress.objects.filter(user=user, verified=False).exists()
    assert len(mail.outbox) == 1


def test_premier_message_bloque_sans_email_confirme(client):
    _user(client, verified=False)
    listing = ListingFactory(published=True)

    get = client.get(reverse("messaging:start", args=[listing.pk]))
    client.post(reverse("messaging:start", args=[listing.pk]), {"body": "Bonjour"})

    assert CONFIRM in get.content.decode()
    assert not Conversation.objects.exists()


def test_visiteur_vers_la_connexion(client):
    response = client.get(reverse("listings:create"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_parcourir_reste_ouvert(client):
    _user(client, verified=False)
    listing = ListingFactory(published=True)

    for url in (reverse("core:home"), reverse("listings:search"), listing.get_absolute_url()):
        assert client.get(url).status_code == 200
    assert client.get(reverse("favorites:list")).status_code == 200


def test_reglage_desactive(client, settings):
    settings.VERIFIED_EMAIL_REQUIRED = False
    _user(client, verified=False)

    html = client.get(reverse("listings:create")).content.decode()

    assert CONFIRM not in html
    assert mail.outbox == []
