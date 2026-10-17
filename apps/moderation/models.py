from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.listings.models import Listing


class ReportReason(models.TextChoices):
    SCAM = "scam", "Arnaque ou fausse annonce"
    PROHIBITED = "prohibited", "Objet interdit ou illégal"
    WRONG_CATEGORY = "wrong_category", "Mauvaise catégorie"
    DUPLICATE = "duplicate", "Déjà vendue ou en double"
    OTHER = "other", "Autre"


class ReportStatus(models.TextChoices):
    OPEN = "open", "À examiner"
    UPHELD = "upheld", "Retenu (annonce retirée)"
    DISMISSED = "dismissed", "Classé sans suite"


class Report(TimeStampedModel):
    """Signalement d'une annonce par un membre (ticket #49). Les décisions passent par
    services.py : retrait de l'annonce ou classement sans suite."""

    listing = models.ForeignKey(
        Listing, verbose_name="annonce", on_delete=models.CASCADE, related_name="reports"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="signalé par",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reason = models.CharField("motif", max_length=20, choices=ReportReason.choices)
    details = models.TextField("précision", max_length=500, blank=True)
    status = models.CharField(
        "état", max_length=10, choices=ReportStatus.choices, default=ReportStatus.OPEN
    )
    handled_at = models.DateTimeField("traité le", null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="traité par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["listing", "reporter"], name="report_once_per_member"),
            models.CheckConstraint(
                condition=models.Q(status__in=ReportStatus.values), name="report_status_valid"
            ),
        ]
        indexes = [models.Index(fields=["status", "listing"], name="report_status_listing_idx")]

    def __str__(self):
        return f"{self.listing} — {self.get_reason_display()}"


class ReportedListing(Listing):
    """Vue de l'admin sur les annonces qui ont des signalements à examiner (ticket #49)."""

    class Meta:
        proxy = True
        verbose_name = "annonce signalée"
        verbose_name_plural = "annonces signalées"
