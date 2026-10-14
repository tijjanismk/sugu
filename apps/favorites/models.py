from django.conf import settings
from django.db import models


class Favorite(models.Model):
    """Une annonce mise de côté par un utilisateur (ticket #11, docs/database.md)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "favori"
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="favorite_unique_user_listing")
        ]

    def __str__(self):
        return f"{self.user} → {self.listing}"
