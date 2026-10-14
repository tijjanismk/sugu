from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

from apps.core.models import TimeStampedModel

MESSAGE_MAX_LENGTH = 1000


class Conversation(TimeStampedModel):
    """Échange entre un acheteur et le vendeur à propos d'une annonce (ticket #12). Rien n'est
    détruit en cascade : un compte supprimé est anonymisé (#13), une annonce est retirée, pas
    effacée, et l'historique sert de preuve en cas de litige (docs/security.md)."""

    listing = models.ForeignKey(
        "listings.Listing",
        verbose_name="annonce",
        on_delete=models.PROTECT,
        related_name="conversations",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="acheteur",
        on_delete=models.PROTECT,
        related_name="conversations_as_buyer",
    )
    # Dénormalisé (docs/database.md) : « mes conversations » sans jointure sur l'annonce.
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="vendeur",
        on_delete=models.PROTECT,
        related_name="conversations_as_seller",
    )
    last_message_at = models.DateTimeField("dernier message", null=True, db_index=True)

    class Meta:
        verbose_name = "conversation"
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "buyer"], name="conversation_unique_listing_buyer"
            ),
            models.CheckConstraint(
                condition=~Q(buyer=F("seller")), name="conversation_buyer_is_not_seller"
            ),
        ]

    def __str__(self):
        return f"{self.buyer} → {self.listing}"

    def get_absolute_url(self):
        return reverse("messaging:conversation", args=[self.pk])

    def other_party(self, user):
        return self.seller if user.pk == self.buyer_id else self.buyer


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.PROTECT,
        related_name="+",
    )
    body = models.TextField("message", max_length=MESSAGE_MAX_LENGTH)
    created_at = models.DateTimeField("envoyé le", auto_now_add=True)
    read_at = models.DateTimeField("lu le", null=True, blank=True)

    class Meta:
        verbose_name = "message"
        ordering = ["created_at", "pk"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="message_conversation_date")
        ]

    def __str__(self):
        return self.body[:50]
