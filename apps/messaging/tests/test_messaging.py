"""Messagerie (ticket #12) : démarrage depuis une annonce, envoi htmx et sans JavaScript,
rafraîchissement, lecture, compteur de non-lus, permissions."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.core.templatetags.sugu_format import day_label, initials
from apps.listings import services as listing_services
from apps.listings.models import ListingStatus
from apps.listings.tests.factories import ListingFactory
from apps.messaging import services
from apps.messaging.models import Conversation, Message

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def seller():
    return UserFactory(display_name="Aminata Koné")


@pytest.fixture
def buyer():
    return UserFactory(display_name="Moussa Traoré")


@pytest.fixture
def listing(seller):
    return ListingFactory(user=seller, published=True, title="Vélo de course Peugeot")


@pytest.fixture
def conversation(listing, buyer):
    return services.start_conversation(buyer, listing, "Bonjour, le vélo est disponible ?")


def _client(client, user):
    client.force_login(user)
    return client


def _start_url(listing):
    return reverse("messaging:start", args=[listing.pk])


def _poll(client, conversation, after, **headers):
    url = reverse("messaging:poll", args=[conversation.pk])
    return client.get(url, {"apres": after}, headers={**HTMX, **headers})


# --- Démarrer une conversation -----------------------------------------------------------------


def test_la_page_annonce_propose_decrire_au_vendeur(client, buyer, listing):
    html = _client(client, buyer).get(listing.get_absolute_url()).content.decode()

    assert f'href="{_start_url(listing)}"' in html
    assert "Écrire au vendeur" in html
    assert "sg-bottomnav" not in html  # l'action de la page remplace la barre de navigation


def test_pas_de_bouton_pour_le_vendeur_ni_sur_une_annonce_vendue(client, seller, listing):
    own = _client(client, seller).get(listing.get_absolute_url()).content.decode()
    assert _start_url(listing) not in own

    listing_services.mark_sold(listing)
    client.force_login(UserFactory())
    sold = client.get(listing.get_absolute_url()).content.decode()
    assert _start_url(listing) not in sold


def test_visiteur_redirige_vers_la_connexion(client, listing):
    response = client.get(_start_url(listing))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))
    assert "next=" in response.url


def test_premier_message_propose_et_rappel_de_prudence(client, buyer, listing):
    html = _client(client, buyer).get(_start_url(listing)).content.decode()

    assert 'value="Bonjour, l&#x27;objet est-il toujours disponible ?"' in html
    assert "Restez prudent" in html
    assert not Conversation.objects.exists()  # pas de conversation vide


def test_le_premier_message_cree_la_conversation(client, buyer, seller, listing):
    response = _client(client, buyer).post(_start_url(listing), {"body": "Il roule bien ?"})

    conversation = Conversation.objects.get()
    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()
    assert (conversation.buyer, conversation.seller, conversation.listing) == (
        buyer,
        seller,
        listing,
    )
    assert conversation.messages.get().body == "Il roule bien ?"
    assert conversation.last_message_at is not None


def test_conversation_existante_on_y_retourne(client, buyer, listing, conversation):
    response = _client(client, buyer).get(_start_url(listing))

    assert response.url == conversation.get_absolute_url()
    assert Conversation.objects.count() == 1


def test_un_vendeur_ne_peut_pas_se_contacter_lui_meme(client, seller, listing):
    _client(client, seller)

    assert client.get(_start_url(listing)).status_code == 403
    assert client.post(_start_url(listing), {"body": "Moi-même"}).status_code == 403
    with pytest.raises(services.CannotContactSelf):
        services.start_conversation(seller, listing, "Moi-même")
    assert not Conversation.objects.exists()


def test_la_base_refuse_acheteur_egal_vendeur(seller, listing):
    with pytest.raises(IntegrityError):
        Conversation.objects.create(listing=listing, buyer=seller, seller=seller)


def test_une_seule_conversation_par_annonce_et_acheteur(buyer, seller, listing, conversation):
    with pytest.raises(IntegrityError):
        Conversation.objects.create(listing=listing, buyer=buyer, seller=seller)


def test_annonce_vendue_pas_de_nouvelle_conversation(client, buyer, listing):
    listing_services.mark_sold(listing)

    response = _client(client, buyer).post(_start_url(listing), {"body": "Encore là ?"})

    assert response.url == listing.get_absolute_url()
    assert not Conversation.objects.exists()


@pytest.mark.parametrize("status", [ListingStatus.DRAFT, ListingStatus.REMOVED])
def test_annonce_invisible_introuvable(client, buyer, status):
    hidden = ListingFactory(status=status)

    assert _client(client, buyer).get(_start_url(hidden)).status_code == 404


def test_nouvelles_conversations_limitees(client, buyer, settings):
    settings.ACCOUNT_RATE_LIMITS = {
        **settings.ACCOUNT_RATE_LIMITS,
        "conversation_start": "1/h/user",
    }
    first, second = ListingFactory.create_batch(2, published=True)
    _client(client, buyer)
    assert client.post(_start_url(first), {"body": "Bonjour"}).status_code == 302

    assert client.post(_start_url(second), {"body": "Bonjour"}).status_code == 429
    assert Conversation.objects.count() == 1


# --- Ouvrir une conversation -------------------------------------------------------------------


def test_ouvrir_marque_lus_les_messages_recus(client, seller, buyer, conversation):
    services.send_message(conversation, seller, "Oui, toujours disponible.")

    _client(client, seller).get(conversation.get_absolute_url())

    received = conversation.messages.get(sender=buyer)
    mine = conversation.messages.get(sender=seller)
    assert received.read_at is not None
    assert mine.read_at is None  # mon propre message n'est lu que par l'autre


def test_fil_de_la_conversation(client, seller, buyer, conversation):
    services.send_message(conversation, seller, "Oui, passez à Hamdallaye.")

    html = _client(client, buyer).get(conversation.get_absolute_url()).content.decode()

    assert "Bonjour, le vélo est disponible ?" in html
    assert "Oui, passez à Hamdallaye." in html
    assert html.count("sg-msg--me") == 1
    assert "Aujourd&#x27;hui" in html
    assert '<h1 class="sg-topbar__title">Aminata Koné</h1>' in html
    assert "Vélo de course Peugeot" in html  # l'annonce en tête de conversation
    assert "sg-bottomnav" not in html


def test_coche_lu_quand_lautre_a_ouvert(client, seller, buyer, conversation):
    html = _client(client, buyer).get(conversation.get_absolute_url()).content.decode()
    assert ", envoyé" in html

    _client(client, seller).get(conversation.get_absolute_url())
    html = _client(client, buyer).get(conversation.get_absolute_url()).content.decode()
    assert ", lu" in html


def test_le_texte_est_echappe_et_les_liens_cliquables(client, seller, buyer, conversation):
    services.send_message(conversation, seller, "<script>alert(1)</script> https://maps.app/x")

    html = _client(client, buyer).get(conversation.get_absolute_url()).content.decode()

    assert "<script>alert(1)" not in html
    assert "&lt;script&gt;" in html
    assert '<a href="https://maps.app/x" rel="nofollow">' in html


def test_un_autre_utilisateur_ne_voit_pas_la_conversation(client, conversation):
    intruder = _client(client, UserFactory())
    url = conversation.get_absolute_url()

    assert intruder.get(url).status_code == 404
    assert intruder.post(url, {"body": "Coucou"}).status_code == 404
    assert _poll(intruder, conversation, 0).status_code == 404
    assert conversation.messages.count() == 1


def test_send_message_refuse_un_tiers(conversation):
    with pytest.raises(services.PermissionDenied):
        services.send_message(conversation, UserFactory(), "Coucou")


# --- Envoyer ---------------------------------------------------------------------------------


def test_envoi_htmx_ajoute_la_bulle_sans_recharger(client, seller, buyer, conversation):
    last = conversation.messages.get()
    url = conversation.get_absolute_url()

    response = _client(client, seller).post(
        url, {"body": "Oui, il est là.", "apres": last.pk}, headers=HTMX
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert html.count('class="sg-msg ') == 1  # une seule bulle : la mienne
    assert "Oui, il est là." in html
    new = conversation.messages.latest("pk")
    assert f'name="apres" value="{new.pk}"' in html  # le rafraîchisseur repart de là
    conversation.refresh_from_db()
    assert conversation.last_message_at == new.created_at


def test_envoi_htmx_apporte_aussi_les_messages_arrives_entre_temps(
    client, seller, buyer, conversation
):
    last = conversation.messages.get()
    services.send_message(conversation, buyer, "Vous êtes là ?")

    response = _client(client, seller).post(
        conversation.get_absolute_url(), {"body": "Oui !", "apres": last.pk}, headers=HTMX
    )

    html = response.content.decode()
    assert "Vous êtes là ?" in html
    assert "Oui !" in html


def test_envoi_sans_javascript(client, seller, conversation):
    response = _client(client, seller).post(conversation.get_absolute_url(), {"body": "Oui."})

    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()
    assert conversation.messages.count() == 2


@pytest.mark.parametrize(
    ("body", "error"),
    [("   ", "Écrivez un message."), ("x" * 1001, "1000 caractères au plus.")],
)
def test_message_vide_ou_trop_long(client, seller, conversation, body, error):
    _client(client, seller)

    response = client.post(conversation.get_absolute_url(), {"body": body}, headers=HTMX)

    assert response["HX-Retarget"] == "#composer-error"
    assert error in response.content.decode()
    assert conversation.messages.count() == 1

    page = client.post(conversation.get_absolute_url(), {"body": body})
    assert error in page.content.decode()
    assert 'aria-invalid="true"' in page.content.decode()


def test_messages_limites(client, seller, conversation, settings):
    settings.ACCOUNT_RATE_LIMITS = {**settings.ACCOUNT_RATE_LIMITS, "message_send": "1/h/user"}
    _client(client, seller)
    client.post(conversation.get_absolute_url(), {"body": "Un"})

    blocked = client.post(conversation.get_absolute_url(), {"body": "Deux"}, headers=HTMX)

    assert "beaucoup de messages" in blocked.content.decode()
    assert client.post(conversation.get_absolute_url(), {"body": "Deux"}).status_code == 429
    assert conversation.messages.count() == 2


# --- Rafraîchissement -------------------------------------------------------------------------


def test_rien_de_neuf_204(client, buyer, conversation):
    last = conversation.messages.get()

    response = _poll(_client(client, buyer), conversation, last.pk)

    assert response.status_code == 204


def test_nouveau_message_affiche_et_marque_lu(client, seller, buyer, conversation):
    last = conversation.messages.get()
    services.send_message(conversation, seller, "Je suis au marché.")

    response = _poll(_client(client, buyer), conversation, last.pk)

    html = response.content.decode()
    assert "Je suis au marché." in html
    assert "sg-thread__day" not in html  # même jour que le message précédent
    assert conversation.messages.get(sender=seller).read_at is not None


def test_separateur_quand_le_jour_change(client, seller, buyer, conversation):
    last = conversation.messages.get()
    Message.objects.filter(pk=last.pk).update(created_at=timezone.now() - timedelta(days=1))
    services.send_message(conversation, seller, "Bonjour, oui.")

    html = _poll(_client(client, buyer), conversation, last.pk).content.decode()

    assert "Aujourd&#x27;hui" in html


def test_rafraichissement_get_seulement(client, buyer, conversation):
    url = reverse("messaging:poll", args=[conversation.pk])
    assert _client(client, buyer).post(url).status_code == 405


def test_session_expiree_recharge_la_page_sur_la_connexion(client, conversation):
    current = f"http://testserver{conversation.get_absolute_url()}"

    response = _poll(client, conversation, 0, **{"HX-Current-URL": current})

    assert response["HX-Redirect"].startswith(reverse("account_login"))


def test_valeur_apres_invalide_ignoree(client, buyer, conversation):
    response = _poll(_client(client, buyer), conversation, "abc")

    assert response.status_code == 200  # tout le fil depuis le début, pas d'erreur


# --- Boîte de réception et compteur -----------------------------------------------------------


def test_boite_vide(client, buyer):
    html = _client(client, buyer).get(reverse("messaging:inbox")).content.decode()

    assert "Aucun message pour l'instant" in html  # include with : texte littéral non échappé


def test_boite_exige_la_connexion(client):
    response = client.get(reverse("messaging:inbox"))

    assert response.url.startswith(reverse("account_login"))


def test_boite_ne_montre_que_mes_conversations(client, seller, buyer, conversation):
    other = services.start_conversation(UserFactory(), ListingFactory(published=True), "Salut")

    html = _client(client, seller).get(reverse("messaging:inbox")).content.decode()

    assert conversation.get_absolute_url() in html
    assert other.get_absolute_url() not in html
    assert "Moussa Traoré · Vélo de course Peugeot" in html
    assert "sg-list__item--unread" in html
    assert "1 non lu" in html


def test_boite_plus_recente_dabord_et_vous(client, buyer, conversation):
    older = services.start_conversation(buyer, ListingFactory(published=True), "Prix ?")
    Conversation.objects.filter(pk=older.pk).update(
        last_message_at=timezone.now() - timedelta(hours=2)
    )

    response = _client(client, buyer).get(reverse("messaging:inbox"))

    assert list(response.context["page_obj"]) == [conversation, older]
    assert "Vous : Bonjour, le vélo est disponible ?" in response.content.decode()


def test_boite_nombre_de_requetes_constant(client, seller):
    _client(client, seller)

    def count_queries():
        with CaptureQueriesContext(connection) as ctx:
            client.get(reverse("messaging:inbox"))
        return len(ctx)

    for _ in range(2):
        services.start_conversation(
            UserFactory(), ListingFactory(user=seller, published=True), "Bonjour"
        )
    few = count_queries()
    for _ in range(5):
        services.start_conversation(
            UserFactory(), ListingFactory(user=seller, published=True), "Bonjour"
        )

    assert count_queries() == few


def test_compteur_de_non_lus(client, seller, buyer, conversation):
    second = services.start_conversation(
        buyer, ListingFactory(user=seller, published=True), "Et celui-ci ?"
    )
    services.send_message(second, buyer, "Toujours dispo ?")
    services.send_message(conversation, seller, "Oui.")  # mon message : pas compté

    assert services.unread_count(seller) == 3
    html = _client(client, seller).get(reverse("core:home")).content.decode()
    assert '<span class="sg-bottomnav__count">3<span class="sr-only"> non lus</span>' in html

    client.get(second.get_absolute_url())
    assert services.unread_count(seller) == 1
    client.get(conversation.get_absolute_url())
    assert services.unread_count(seller) == 0
    html = client.get(reverse("core:home")).content.decode()
    assert "sg-bottomnav__count" not in html


def test_compteur_plafonne_a_99(client, seller, buyer, conversation):
    Message.objects.bulk_create(
        Message(conversation=conversation, sender=buyer, body="?") for _ in range(120)
    )

    html = _client(client, seller).get(reverse("core:home")).content.decode()

    assert ">99+<" in html


def test_visiteur_pas_de_compteur(client, conversation):
    html = client.get(reverse("core:home")).content.decode()

    assert "sg-bottomnav__count" not in html


def test_lien_messages_de_la_barre(client):
    html = client.get(reverse("core:home")).content.decode()

    assert f'class="sg-bottomnav__item" href="{reverse("messaging:inbox")}"' in html


# --- Formats -----------------------------------------------------------------------------------


def test_initiales():
    assert initials("Aminata Koné") == "AK"
    assert initials("Moussa") == "M"
    assert initials("awa diallo traoré") == "AD"
    assert initials("") == ""


def test_separateur_de_jour():
    now = timezone.now()
    assert day_label(now, now) == "Aujourd'hui"
    assert day_label(now - timedelta(days=1), now) == "Hier"
    old = timezone.localtime(now - timedelta(days=400))
    assert day_label(old, now).endswith(str(old.year))
