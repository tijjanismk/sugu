from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


def _unique_slug(model, base: str, instance_pk) -> str:
    """Premier slug libre parmi `base`, `base-2`, `base-3`…"""
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


class Category(TimeStampedModel):
    """Catégorie d'annonce, sur deux niveaux au plus (une catégorie, ses sous-catégories)."""

    name = models.CharField("nom", max_length=60)
    slug = models.SlugField("slug", max_length=80, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="catégorie parente",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    icon = models.CharField(
        "icône", max_length=40, blank=True, help_text="Nom d'icône Lucide (ex. smartphone)."
    )
    order = models.PositiveIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(parent=F("id")), name="category_not_its_own_parent"
            ),
        ]

    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent_id else self.name

    def clean(self):
        super().clean()
        self._validate_hierarchy()

    def _validate_hierarchy(self):
        if self.parent_id is None:
            return
        if self.pk is not None and self.parent_id == self.pk:
            raise ValidationError({"parent": "Une catégorie ne peut pas être sa propre parente."})
        if self.parent.parent_id is not None:
            raise ValidationError(
                {"parent": "Deux niveaux au plus : choisissez une catégorie principale."}
            )
        if self.pk is not None and self.children.exists():
            raise ValidationError(
                {"parent": "Cette catégorie a des sous-catégories : elle doit rester principale."}
            )

    def save(self, *args, **kwargs):
        # La règle des deux niveaux vaut aussi hors formulaire (admin, seed, shell).
        self._validate_hierarchy()
        if not self.slug:
            base = slugify(self.name)
            taken = Category.objects.filter(slug=base).exclude(pk=self.pk).exists()
            if taken and self.parent_id:
                base = f"{self.parent.slug}-{base}"
            self.slug = _unique_slug(Category, base, self.pk)
        super().save(*args, **kwargs)

    @property
    def is_root(self) -> bool:
        return self.parent_id is None


class City(TimeStampedModel):
    name = models.CharField("nom", max_length=80)
    region = models.CharField("région", max_length=80, blank=True)
    slug = models.SlugField("slug", max_length=80, unique=True, blank=True)

    class Meta:
        verbose_name = "ville"
        verbose_name_plural = "villes"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(City, slugify(self.name), self.pk)
        super().save(*args, **kwargs)
