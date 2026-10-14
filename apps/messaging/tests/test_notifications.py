"""Email de nouveau message (ticket #12, ajout du 2026-10-14)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.tests.factories import MOT_DE_PASSE, UserFactory
from apps.listings.tests.factories import ListingFactory
from apps.messaging import notifications, services
from apps.messaging.models import Conversation, Message

pytestmark = pytest.mark.django_db

SITE = "https://sugu.test"


@pytest.fixture
def seller():
    return UserFactory(display_name="Aminata Koné", email="aminata@example.ml")


@pytest.fixture
def buyer():
    return UserFactory(display_name="Moussa", email="moussa@example.ml")


@pytest.fixture
def listing(seller):
    return ListingFactory(user=seller, published=True, title="Vélo de course Peugeot")


@pytest.fixture
def send(django_capture_on_commit_callbacks):
    """Envoie un message comme la vue (avec l'adresse du site) et exécute l'envoi d'email
    prévu après validation de la transaction."""

    def _send(conversation, sender, body):
        with django_capture_on_commit_callbacks(execute=True):
            return services.send_message(conversation, sender, body, base_url=SITE)

    return _send


@pytest.fixture
def conversation(listing, buyer):
    # Sans base_url : pas d'email, la boîte d'envoi reste vide pour chaque test.
    return services.start_conversation(buyer, listing, "Bonjour")


def _read_all(conversation, reader, minutes_ago):
    conversation.messages.exclude(sender=reader).update(
        read_at=timezone.now() - timedelta(minutes=minutes_ago)
    )


# --- Par la vue ------------------------------------------------------------------------------


def test_premier_message_email_au_vendeur(
    client, buyer, seller, listing, django_capture_on_commit_callbacks
):
    client.force_login(buyer)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("messaging:start", args=[listing.pk]), {"body": "Prix ferme ?"})

    conversation = Conversation.objects.get()
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["aminata@example.ml"]
    assert email.subject == "[Sugu] Nouveau message de Moussa"
    assert f"http://testserver/messages/{conversation.pk}/" in email.body
    assert "Vélo de course Peugeot" in email.body
    assert "Prix ferme" not in email.body  # jamais le texte du message
    html = email.alternatives[0].content
    assert "Prix ferme" not in html
    assert "http://testserver/comptes/profil/" in html  # lien pour ne plus en recevoir


def test_reponse_par_la_vue_email_a_lacheteur(
    client, seller, conversation, django_capture_on_commit_callbacks
):
    client.force_login(seller)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            conversation.get_absolute_url(), {"body": "Oui"}, headers={"HX-Request": "true"}
        )

    assert [email.to for email in mail.outbox] == [["moussa@example.ml"]]


# --- Règles d'envoi --------------------------------------------------------------------------


def test_un_seul_email_tant_que_la_conversation_nest_pas_ouverte(send, buyer, conversation):
    send(conversation, buyer, "Toujours là ?")  # « Bonjour » est déjà non lu
    send(conversation, buyer, "Allô ?")

    assert mail.outbox == []


def test_premier_non_lu_apres_lecture_nouvel_email(send, buyer, seller, conversation):
    _read_all(conversation, seller, minutes_ago=60)

    send(conversation, buyer, "Je peux passer ce soir ?")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [seller.email]


def test_pas_demail_pendant_un_echange_en_direct(send, buyer, seller, conversation):
    _read_all(conversation, seller, minutes_ago=2)  # le vendeur a la conversation ouverte

    send(conversation, buyer, "Je suis devant le marché.")

    assert mail.outbox == []


def test_avoir_ecrit_recemment_ne_suffit_pas(send, buyer, seller, conversation):
    # L'acheteur vient d'écrire puis a fermé l'application : la réponse lui est signalée.
    send(conversation, seller, "Oui, il est disponible.")

    assert [email.to for email in mail.outbox] == [[buyer.email]]


def test_option_desactivee(send, buyer, seller, conversation):
    _read_all(conversation, seller, minutes_ago=60)
    seller.notify_messages = False
    seller.save(update_fields=["notify_messages"])
    conversation.refresh_from_db()  # comme une nouvelle requête : vendeur relu

    send(conversation, buyer, "Encore disponible ?")

    assert mail.outbox == []


def test_jamais_vers_un_compte_supprime(buyer, seller, conversation):
    account_services.delete_account(buyer)

    assert not notifications.should_notify(
        Message(conversation=conversation, sender=seller, body="?", pk=10**9)
    )


def test_lauteur_ne_recoit_rien(send, buyer, seller, conversation):
    _read_all(conversation, seller, minutes_ago=60)

    send(conversation, buyer, "Bonsoir")

    assert all(email.to != [buyer.email] for email in mail.outbox)


def test_sans_adresse_du_site_pas_demail(
    buyer, seller, conversation, django_capture_on_commit_callbacks
):
    _read_all(conversation, seller, minutes_ago=60)
    with django_capture_on_commit_callbacks(execute=True):
        services.send_message(conversation, buyer, "Message d'un script")

    assert mail.outbox == []


def test_panne_demail_le_message_part_quand_meme(
    send, buyer, seller, conversation, monkeypatch, caplog
):
    _read_all(conversation, seller, minutes_ago=60)

    def broken(*args, **kwargs):
        raise ConnectionRefusedError("SMTP injoignable")

    monkeypatch.setattr(notifications, "send_mail", broken)

    message = send(conversation, buyer, "Toujours là ?")

    assert Message.objects.filter(pk=message.pk).exists()
    assert "Email de nouveau message non envoyé" in caplog.text
    assert seller.email not in caplog.text


def test_nom_sur_une_seule_ligne_dans_le_sujet(send, seller, conversation):
    # Un nom avec retour à la ligne ne doit pas casser l'en-tête de l'email.
    conversation.buyer.display_name = "Moussa\nBcc: x@example.ml"
    conversation.buyer.save(update_fields=["display_name"])
    _read_all(conversation, seller, minutes_ago=60)

    send(conversation, conversation.buyer, "Bonjour encore")

    assert mail.outbox[0].subject == "[Sugu] Nouveau message de Moussa Bcc: x@example.ml"
    assert mail.outbox[0].bcc == []


# --- Profil ----------------------------------------------------------------------------------


def test_case_du_profil(client, seller):
    client.force_login(seller)
    assert (
        "Me prévenir par email des nouveaux messages"
        in client.get(reverse("account_profile")).content.decode()
    )

    client.post(reverse("account_profile"), {"display_name": "Aminata Koné", "phone": ""})

    seller.refresh_from_db()
    assert seller.notify_messages is False  # case décochée


def test_active_par_defaut():
    assert UserFactory().notify_messages is True
    assert MOT_DE_PASSE  # comptes de test utilisables
