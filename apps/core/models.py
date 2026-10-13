from django.db import models


class TimeStampedModel(models.Model):
    """`created_at` et `updated_at` sur toutes les tables métier (docs/database.md)."""

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True
