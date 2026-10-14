"""Email de nouveau message (ticket #12, ajout du 2026-10-14).

Un seul email par conversation tant que le destinataire ne l'a pas ouverte : c'est le premier
message non lu qui le déclenche, pas chacun des suivants. L'email ne contient pas le texte du
message (vie privée ; un lien d'arnaque ne part pas depuis l'adresse de Sugu).

Pas de file d'attente en V1 : l'envoi se fait dans la requête, après validation de la
transaction. Une panne du serveur d'email est journalisée et n'empêche jamais le message.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import Message

logger = logging.getLogger(__name__)

# Destinataire en pleine conversation (il y a lu un message récemment : la page ouverte marque
# lus les messages qui arrivent) : pas d'email. Sinon, en direct, chaque message lu puis suivi
# d'un autre en enverrait un. Avoir écrit ne compte pas : on écrit puis on ferme l'application.
ACTIVE_WINDOW = timedelta(minutes=15)


def should_notify(message: Message) -> bool:
    """Vrai si le message est le premier non lu de la conversation pour son destinataire, que
    celui-ci n'y est pas actif en ce moment et qu'il veut (et peut) recevoir l'email."""
    recipient = message.conversation.other_party(message.sender)
    if not (recipient.is_active and recipient.notify_messages and recipient.email):
        return False
    if recipient.is_deleted:
        return False
    earlier_unread = (
        message.conversation.messages.filter(read_at__isnull=True, pk__lt=message.pk)
        .exclude(sender=recipient)
        .exists()
    )
    if earlier_unread:
        return False
    since = timezone.now() - ACTIVE_WINDOW
    active = (
        message.conversation.messages.filter(read_at__gte=since).exclude(sender=recipient).exists()
    )
    return not active


def _one_line(text: str) -> str:
    """Un nom saisi par un utilisateur ne doit pas pouvoir ajouter une ligne d'en-tête."""
    return " ".join(text.split())


def send_new_message_email(message: Message, base_url: str) -> None:
    conversation = message.conversation
    recipient = conversation.other_party(message.sender)
    context = {
        "sender": _one_line(message.sender.display_name),
        "recipient": recipient.display_name,
        "listing_title": conversation.listing.title,
        "conversation_url": base_url + conversation.get_absolute_url(),
        "profile_url": base_url + reverse("account_profile"),
    }
    subject = f"{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}Nouveau message de {context['sender']}"
    try:
        send_mail(
            subject,
            render_to_string("messaging/email/new_message.txt", context),
            None,
            [recipient.email],
            html_message=render_to_string("messaging/email/new_message.html", context),
        )
    except Exception:
        # Ni l'adresse ni le texte dans le journal (docs/security.md).
        logger.exception("Email de nouveau message non envoyé (message %s)", message.pk)
