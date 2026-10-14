from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Length
from django.db.models.lookups import LessThanOrEqual
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

# Configuration de recherche plein texte créée par la migration listings.0003 : le français de
# PostgreSQL plus unaccent, pour que « velo » trouve « Vélo de course ».
SEARCH_CONFIG = "french_unaccent"
DESCRIPTION_MAX_LENGTH = 2000
MAX_PHOTOS = 6
# Durée pendant laquelle une baisse de prix est signalée aux acheteurs.
PRICE_DROP_BADGE_DAYS = 14
# Une annonce est « Nouvelle » pendant ses premières 24 heures (design/components/Badge).
NEW_BADGE_HOURS = 24
# Distance de la ville indiquée par le vendeur (« à 20 km de Bamako »), en km.
MAX_DISTANCE_KM = 300


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


class ListingStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    PUBLISHED = "published", "Publiée"
    RESERVED = "reserved", "Réservée"  # V2 (réservation) : aucune transition n'y mène en V1
    SOLD = "sold", "Vendue"
    REMOVED = "removed", "Retirée"


# Passages de statut autorisés (docs/tests.md : published → sold oui, sold → published non).
# `removed` est définitif. Les transitions vers `reserved` arriveront avec la V2.
ALLOWED_TRANSITIONS = {
    ListingStatus.DRAFT: {ListingStatus.PUBLISHED, ListingStatus.REMOVED},
    ListingStatus.PUBLISHED: {ListingStatus.SOLD, ListingStatus.REMOVED},
    ListingStatus.RESERVED: {ListingStatus.PUBLISHED, ListingStatus.SOLD, ListingStatus.REMOVED},
    ListingStatus.SOLD: {ListingStatus.REMOVED},
    ListingStatus.REMOVED: set(),
}

# Statuts d'une annonce qui a été publiée : published_at est alors obligatoire. Ce sont aussi
# les annonces visibles de tous sur leur page (une annonce vendue garde sa page, avec un bandeau).
PUBLISHED_STATUSES = [ListingStatus.PUBLISHED, ListingStatus.RESERVED, ListingStatus.SOLD]


class PaymentMethod(models.TextChoices):
    CASH_ON_DELIVERY = "cash_on_delivery", "Paiement à la livraison"
    MOBILE_MONEY = "mobile_money", "Mobile money"


class Listing(TimeStampedModel):
    """Annonce. Les changements de statut et de prix passent par services.py."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="vendeur",
        on_delete=models.PROTECT,  # un compte supprimé est anonymisé, pas détruit (#13)
        related_name="listings",
    )
    category = models.ForeignKey(
        Category, verbose_name="catégorie", on_delete=models.PROTECT, related_name="listings"
    )
    city = models.ForeignKey(
        City, verbose_name="ville", on_delete=models.PROTECT, related_name="listings"
    )
    # Lieu précis, facultatif (ajout du 2026-10-14) : « Sabalibougou », « Commune V »…
    neighborhood = models.CharField("quartier ou commune", max_length=80, blank=True)
    # Pour un objet hors de la ville : « à 20 km de Bamako ».
    distance_km = models.PositiveSmallIntegerField(
        "distance de la ville (km)", null=True, blank=True
    )
    title = models.CharField("titre", max_length=80)
    description = models.TextField(
        "description", validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)]
    )
    price = models.PositiveIntegerField(
        "prix (FCFA)", null=True, blank=True, help_text="Vide : « À débattre »."
    )
    previous_price = models.PositiveIntegerField(
        "prix avant la baisse", null=True, blank=True, editable=False
    )
    price_dropped_at = models.DateTimeField(
        "baisse de prix le", null=True, blank=True, editable=False
    )
    payment_methods = ArrayField(
        models.CharField(max_length=20, choices=PaymentMethod.choices),
        verbose_name="modes de règlement",
        default=list,
        blank=True,
    )
    status = models.CharField(
        "statut", max_length=12, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )
    published_at = models.DateTimeField("publiée le", null=True, blank=True)
    # Maintenu par un trigger PostgreSQL (migration listings.0003) : ne jamais l'écrire ici.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = "annonce"
        verbose_name_plural = "annonces"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="listing_status_published_idx"),
            GinIndex(fields=["search_vector"], name="listing_search_vector_gin"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ListingStatus.values), name="listing_status_valid"
            ),
            models.CheckConstraint(
                condition=Q(distance_km__isnull=True)
                | Q(distance_km__gte=1, distance_km__lte=MAX_DISTANCE_KM),
                name="listing_distance_km_range",
            ),
            models.CheckConstraint(
                condition=Q(payment_methods__contained_by=PaymentMethod.values),
                name="listing_payment_methods_valid",
            ),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length("description"), DESCRIPTION_MAX_LENGTH),
                name="listing_description_max_length",
            ),
            models.CheckConstraint(
                condition=~Q(status__in=PUBLISHED_STATUSES) | Q(published_at__isnull=False),
                name="listing_published_has_date",
            ),
            models.CheckConstraint(
                condition=Q(previous_price__isnull=True, price_dropped_at__isnull=True)
                | Q(
                    previous_price__isnull=False,
                    price_dropped_at__isnull=False,
                    price__isnull=False,
                    previous_price__gt=F("price"),
                ),
                name="listing_price_drop_coherent",
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listings:detail", kwargs={"pk": self.pk, "slug": self.slug})

    @property
    def slug(self) -> str:
        """Slug du titre pour l'URL (lisible, jamais utilisé pour retrouver l'annonce)."""
        return slugify(self.title)[:60].strip("-") or "annonce"

    @property
    def place_label(self) -> str:
        """Lieu affiché, quartier puis ville (design/README.md) : « Sabalibougou, Bamako »,
        « À 20 km de Bamako », « Moribabougou, à 20 km de Bamako »."""
        city = self.city.name
        where = f"à {self.distance_km} km de {city}" if self.distance_km else city
        label = f"{self.neighborhood}, {where}" if self.neighborhood else where
        return label[0].upper() + label[1:]

    @property
    def is_sold(self) -> bool:
        return self.status == ListingStatus.SOLD

    @property
    def is_new(self) -> bool:
        if self.published_at is None:
            return False
        return timezone.now() - self.published_at < timedelta(hours=NEW_BADGE_HOURS)

    @property
    def card_badge(self) -> str | None:
        """Le badge unique d'une carte : Vendu, sinon Prix en baisse, sinon Nouveau."""
        if self.is_sold:
            return "sold"
        if self.has_recent_price_drop:
            return "drop"
        if self.is_new:
            return "new"
        return None

    def can_change_status_to(self, new_status: str) -> bool:
        return new_status in ALLOWED_TRANSITIONS[ListingStatus(self.status)]

    @property
    def price_drop_until(self):
        """Fin de la mention « Prix en baisse » (montrée au vendeur dans le formulaire)."""
        if self.price_dropped_at is None:
            return None
        return self.price_dropped_at + timedelta(days=PRICE_DROP_BADGE_DAYS)

    @property
    def has_recent_price_drop(self) -> bool:
        """Vrai pendant PRICE_DROP_BADGE_DAYS jours après une baisse de prix."""
        if self.price_dropped_at is None:
            return False
        return timezone.now() - self.price_dropped_at <= timedelta(days=PRICE_DROP_BADGE_DAYS)


def photo_upload_to(instance: Photo, filename: str) -> str:
    return f"listings/{instance.listing_id}/{filename}"


class Photo(TimeStampedModel):
    """Photo d'annonce déjà réencodée en WebP (ticket #7) ; l'original n'est jamais conservé."""

    listing = models.ForeignKey(
        Listing, verbose_name="annonce", on_delete=models.CASCADE, related_name="photos"
    )
    large = models.ImageField("version 1200 px", upload_to=photo_upload_to, max_length=255)
    thumb = models.ImageField("miniature 400 px", upload_to=photo_upload_to, max_length=255)
    order = models.PositiveSmallIntegerField("ordre", default=0, help_text="0 : couverture.")
    width = models.PositiveSmallIntegerField("largeur")
    height = models.PositiveSmallIntegerField("hauteur")

    class Meta:
        verbose_name = "photo"
        verbose_name_plural = "photos"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["listing", "order"], name="photo_unique_order"),
            models.CheckConstraint(condition=Q(order__lt=MAX_PHOTOS), name="photo_order_max"),
        ]

    def __str__(self):
        return f"{self.listing} — photo {self.order}"
