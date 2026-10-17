from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class TimeStampedModel(models.Model):
    """`created_at` et `updated_at` sur toutes les tables métier (docs/database.md)."""

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


def validate_banner_link(value: str) -> None:
    """Une page de Sugu (« /categorie/… ») ou une adresse https. Jamais « javascript: » ni
    « //autre-site » (qui sortirait du site en ayant l'air d'un chemin)."""
    if value.startswith("/") and not value.startswith("//"):
        return
    if value.startswith("https://") and len(value) > len("https://"):
        return
    raise ValidationError(
        "Indiquez une page de Sugu (commençant par /) ou une adresse en https://.",
        code="invalid_link",
    )


class Banner(TimeStampedModel):
    """Bannière image en haut de l'accueil (ticket #8, ajout du 2026-10-17).

    L'image est réencodée en WebP en deux largeurs (apps/core/banners.py), comme les photos
    d'annonce ; l'original n'est jamais conservé."""

    image = models.ImageField("image 1200 px", upload_to="banners/", max_length=255)
    image_small = models.ImageField("image 600 px", upload_to="banners/", max_length=255)
    width = models.PositiveSmallIntegerField("largeur")
    height = models.PositiveSmallIntegerField("hauteur")
    alt = models.CharField(
        "texte de la bannière",
        max_length=150,
        help_text="Lu aux personnes aveugles et affiché si l'image ne charge pas : "
        "reprenez le texte écrit sur l'image.",
    )
    link = models.CharField(
        "lien",
        max_length=300,
        blank=True,
        validators=[validate_banner_link],
        help_text="Facultatif. Une page de Sugu (/categorie/vehicules/) ou une adresse https://…",
    )
    is_active = models.BooleanField("active", default=True)
    starts_at = models.DateTimeField(
        "début", null=True, blank=True, help_text="Facultatif : affichée à partir de ce moment."
    )
    ends_at = models.DateTimeField(
        "fin", null=True, blank=True, help_text="Facultatif : retirée de l'accueil à ce moment."
    )
    order = models.PositiveSmallIntegerField("ordre", default=0, help_text="0 : la première.")

    class Meta:
        verbose_name = "bannière"
        verbose_name_plural = "bannières"
        ordering = ["order", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__isnull=True)
                | Q(ends_at__isnull=True)
                | Q(ends_at__gt=F("starts_at")),
                name="banner_ends_after_start",
            ),
        ]

    def __str__(self):
        return self.alt

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La fin doit venir après le début."})
