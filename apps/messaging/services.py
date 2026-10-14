from dataclasses import dataclass
from functools import partial

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.listings.models import Listing, ListingStatus

from . import notifications
from .models import Conversation, Message

# Une nouvelle conversation ne s'ouvre que sur une annonce encore disponible ; une conversation
# commencée continue quel que soit le statut de l'annonce.
CONTACTABLE_STATUSES = [ListingStatus.PUBLISHED, ListingStatus.RESERVED]


class CannotContactSelf(PermissionDenied):
    """Un vendeur ne peut pas s'écrire à propos de sa propre annonce."""


def conversations_for(user):
    """Les conversations dont l'utilisateur est l'acheteur ou le vendeur : le filtre est fait
    dans la requête, jamais après coup (docs/security.md)."""
    return Conversation.objects.filter(Q(buyer=user) | Q(seller=user))


def get_conversation(user, pk: int) -> Conversation:
    """Conversation d'un participant ; celle des autres : 404 (on ne révèle pas qu'elle existe)."""
    queryset = conversations_for(user).select_related("listing", "buyer", "seller")
    return get_object_or_404(queryset, pk=pk)


def find_conversation(listing: Listing, buyer) -> Conversation | None:
    return Conversation.objects.filter(listing=listing, buyer=buyer).first()


def start_conversation(
    buyer, listing: Listing, body: str, *, base_url: str | None = None
) -> Conversation:
    """Premier message d'un acheteur : la conversation n'est créée qu'avec lui (pas de
    conversation vide). Si elle existe déjà, le message s'y ajoute."""
    if listing.user_id == buyer.pk:
        raise CannotContactSelf("Vous ne pouvez pas vous écrire à vous-même.")
    with transaction.atomic():
        conversation, _ = Conversation.objects.get_or_create(
            listing=listing, buyer=buyer, defaults={"seller_id": listing.user_id}
        )
        send_message(conversation, buyer, body, base_url=base_url)
    return conversation


def send_message(
    conversation: Conversation, sender, body: str, *, base_url: str | None = None
) -> Message:
    """`base_url` (« https://sugu.ml ») : adresse du site pour les liens de l'email de nouveau
    message, envoyé après validation si c'est le premier non lu (notifications.py). Sans
    adresse (scripts, données de démo) : pas d'email."""
    if sender.pk not in (conversation.buyer_id, conversation.seller_id):
        raise PermissionDenied("Vous ne participez pas à cette conversation.")
    if conversation.other_party(sender).is_deleted:
        raise PermissionDenied("Ce compte a été supprimé.")
    message = Message.objects.create(conversation=conversation, sender=sender, body=body)
    Conversation.objects.filter(pk=conversation.pk).update(
        last_message_at=message.created_at, updated_at=message.created_at
    )
    if base_url and notifications.should_notify(message):
        transaction.on_commit(partial(notifications.send_new_message_email, message, base_url))
    return message


def mark_read(conversation: Conversation, reader) -> int:
    """Les messages reçus deviennent lus quand le destinataire ouvre la conversation (ou que le
    rafraîchissement les lui affiche)."""
    return (
        conversation.messages.filter(read_at__isnull=True)
        .exclude(sender=reader)
        .update(read_at=timezone.now())
    )


def _unread_for(user) -> Q:
    return Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)


def unread_count(user) -> int:
    """Messages reçus et pas encore lus, toutes conversations confondues (barre de navigation)."""
    return (
        Message.objects.filter(read_at__isnull=True)
        .exclude(sender=user)
        .filter(Q(conversation__buyer=user) | Q(conversation__seller=user))
        .count()
    )


def inbox(user):
    """Liste des conversations, la plus récemment active d'abord, avec le dernier message et le
    nombre de non-lus, en une requête."""
    last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at", "-pk")
    return (
        conversations_for(user)
        .filter(last_message_at__isnull=False)
        .select_related("listing", "buyer", "seller")
        .annotate(
            unread=Count("messages", filter=_unread_for(user)),
            last_body=Subquery(last.values("body")[:1]),
            last_sender_id=Subquery(last.values("sender_id")[:1]),
        )
        .order_by("-last_message_at", "-pk")
    )


@dataclass
class ThreadItem:
    message: Message
    mine: bool
    new_day: bool  # premier message d'un jour : séparateur « Aujourd'hui », « Hier », « 12 oct. »


def thread_items(messages, viewer, previous: Message | None = None) -> list[ThreadItem]:
    items = []
    day = timezone.localtime(previous.created_at).date() if previous else None
    for message in messages:
        message_day = timezone.localtime(message.created_at).date()
        items.append(ThreadItem(message, message.sender_id == viewer.pk, message_day != day))
        day = message_day
    return items


def messages_after(conversation: Conversation, after_pk: int):
    """Messages arrivés après celui que la page affiche en dernier (rafraîchissement htmx), et
    ce dernier message pour savoir s'il faut un séparateur de jour."""
    new = list(conversation.messages.filter(pk__gt=after_pk))
    previous = conversation.messages.filter(pk=after_pk).first() if new and after_pk else None
    return new, previous
