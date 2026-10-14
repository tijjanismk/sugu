from dataclasses import dataclass
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .images import process_photo
from .models import (
    MAX_PHOTOS,
    PUBLISHED_STATUSES,
    Category,
    City,
    Listing,
    ListingStatus,
    Photo,
)
from .seed_data import CATEGORIES, CITIES, DEMO_LISTINGS, DEMO_SELLER

HOME_CATEGORY_COUNT = 8
PAGE_SIZE = 20


# --- Lecture -----------------------------------------------------------------------------


def with_cover(queryset):
    """Ajoute `cover_photos` (la photo 0) et les relations d'une carte, sans requête par carte."""
    return queryset.select_related("city", "category").prefetch_related(
        Prefetch("photos", queryset=Photo.objects.filter(order=0), to_attr="cover_photos")
    )


def latest_listings():
    """Annonces publiées, les plus récentes d'abord (accueil, ticket #8)."""
    return with_cover(Listing.objects.filter(status=ListingStatus.PUBLISHED)).order_by(
        "-published_at", "-pk"
    )


def get_visible_listing(pk: int) -> Listing:
    """Page d'une annonce : publiée, réservée ou vendue. Brouillon et retirée : 404."""
    queryset = Listing.objects.select_related("user", "city", "category").prefetch_related("photos")
    return get_object_or_404(queryset, pk=pk, status__in=PUBLISHED_STATUSES)


class InvalidStatusTransition(ValidationError):
    """Passage de statut interdit (voir models.ALLOWED_TRANSITIONS)."""


class PriceLocked(ValidationError):
    """Le prix d'une annonce vendue ou retirée ne change plus."""


# --- Statut et prix ----------------------------------------------------------------------


@transaction.atomic
def change_status(listing: Listing, new_status: str) -> Listing:
    """Change le statut si la transition est permise ; la première publication fixe
    `published_at`. La ligne est verrouillée : deux requêtes simultanées ne peuvent pas
    appliquer deux transitions à partir du même état."""
    locked = Listing.objects.select_for_update().get(pk=listing.pk)
    if not locked.can_change_status_to(new_status):
        raise InvalidStatusTransition(
            f"Impossible de passer une annonce « {locked.get_status_display()} » "
            f"au statut « {ListingStatus(new_status).label} »."
        )
    locked.status = new_status
    fields = ["status", "updated_at"]
    if new_status == ListingStatus.PUBLISHED and locked.published_at is None:
        locked.published_at = timezone.now()
        fields.append("published_at")
    locked.save(update_fields=fields)
    listing.status, listing.published_at = locked.status, locked.published_at
    return listing


def publish(listing: Listing) -> Listing:
    return change_status(listing, ListingStatus.PUBLISHED)


def mark_sold(listing: Listing) -> Listing:
    return change_status(listing, ListingStatus.SOLD)


def remove(listing: Listing) -> Listing:
    return change_status(listing, ListingStatus.REMOVED)


@transaction.atomic
def update_price(listing: Listing, new_price: int | None) -> Listing:
    """Change le prix. Sur une annonce publiée, une baisse mémorise le prix affiché juste avant
    (`previous_price`) et sa date ; une hausse ou « à débattre » (None) efface la baisse.
    Un brouillon n'a pas de baisse : personne n'a vu l'ancien prix."""
    locked = Listing.objects.select_for_update().get(pk=listing.pk)
    if locked.status in (ListingStatus.SOLD, ListingStatus.REMOVED):
        raise PriceLocked("Le prix d'une annonce vendue ou retirée ne peut plus changer.")
    if new_price is not None and new_price < 0:
        raise ValidationError("Le prix doit être positif.")

    old_price = locked.price
    is_drop = (
        locked.status == ListingStatus.PUBLISHED
        and old_price is not None
        and new_price is not None
        and new_price < old_price
    )
    if is_drop:
        locked.previous_price = old_price
        locked.price_dropped_at = timezone.now()
    elif new_price != old_price:
        locked.previous_price = None
        locked.price_dropped_at = None
    locked.price = new_price
    locked.save(update_fields=["price", "previous_price", "price_dropped_at", "updated_at"])
    listing.price = locked.price
    listing.previous_price, listing.price_dropped_at = (
        locked.previous_price,
        locked.price_dropped_at,
    )
    return listing


# --- Dépôt d'annonce ---------------------------------------------------------------------


def create_listing(user, *, data: dict, photos: list) -> Listing:
    """Crée et publie une annonce avec ses photos (ticket #7).

    Toutes les photos sont traitées avant la moindre écriture : si l'une est refusée, rien
    n'est enregistré. Seules les versions WebP sont stockées, jamais l'original.
    `data` : title, description, category, city, neighborhood, distance_km, price,
    payment_methods (formulaire validé).
    """
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ValidationError(f"Ajoutez de 1 à {MAX_PHOTOS} photos.")
    processed = []
    for index, uploaded in enumerate(photos, start=1):
        try:
            processed.append(process_photo(uploaded))
        except ValidationError as exc:
            raise ValidationError(f"Photo {index} : {' '.join(exc.messages)}") from exc

    written = []  # fichiers déjà écrits, à effacer si la transaction échoue
    try:
        with transaction.atomic():
            listing = Listing.objects.create(
                user=user,
                title=data["title"],
                description=data["description"],
                category=data["category"],
                city=data["city"],
                neighborhood=data.get("neighborhood") or "",
                distance_km=data.get("distance_km"),
                price=data.get("price"),
                payment_methods=list(data.get("payment_methods") or []),
            )
            for order, photo in enumerate(processed):
                name = uuid4().hex
                item = Photo(listing=listing, order=order, width=photo.width, height=photo.height)
                item.large.save(f"{name}-1200.webp", photo.large, save=False)
                written.append(item.large)
                item.thumb.save(f"{name}-400.webp", photo.thumb, save=False)
                written.append(item.thumb)
                item.save()
            publish(listing)
    except Exception:
        for file in written:
            file.storage.delete(file.name)
        raise
    return listing


# --- Données de référence et de démonstration --------------------------------------------


@dataclass
class SeedReport:
    categories_created: int = 0
    cities_created: int = 0
    listings_created: int = 0


@transaction.atomic
def seed_reference_data() -> SeedReport:
    """Charge catégories et villes de référence. Idempotent : chaque ligne est retrouvée par son
    slug ; un second passage ne crée rien et remet les valeurs de référence."""
    report = SeedReport()
    for position, (name, slug, icon, children) in enumerate(CATEGORIES, start=1):
        parent, created = Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "order": position * 10, "parent": None},
        )
        report.categories_created += created
        for child_position, (child_name, child_slug) in enumerate(children, start=1):
            _, created = Category.objects.update_or_create(
                slug=child_slug,
                defaults={
                    "name": child_name,
                    "icon": "",
                    "order": child_position * 10,
                    "parent": parent,
                },
            )
            report.categories_created += created
    for name, slug, region in CITIES:
        _, created = City.objects.update_or_create(
            slug=slug, defaults={"name": name, "region": region}
        )
        report.cities_created += created
    return report


@transaction.atomic
def seed_demo_listings() -> int:
    """Annonces de démonstration (sans photo) d'un vendeur de démo sans mot de passe utilisable.
    Idempotent : une annonce est retrouvée par (vendeur, titre). À ne pas lancer en production.
    Renvoie le nombre d'annonces créées."""
    User = get_user_model()
    seller, created = User.objects.get_or_create(
        email=DEMO_SELLER["email"], defaults={"display_name": DEMO_SELLER["display_name"]}
    )
    if created:
        seller.set_unusable_password()
        seller.save(update_fields=["password"])

    now = timezone.now()
    created_count = 0
    for item in DEMO_LISTINGS:
        previous_price = item.get("previous_price")
        content = {
            "category": Category.objects.get(slug=item["category"]),
            "city": City.objects.get(slug=item["city"]),
            "neighborhood": item.get("neighborhood", ""),
            "distance_km": item.get("distance_km"),
            "description": item["description"],
            "price": item["price"],
            "payment_methods": item["payment_methods"],
            # Une baisse de démo reste « récente » : chaque seed relance sa fenêtre de 14 jours.
            "previous_price": previous_price,
            "price_dropped_at": now if previous_price else None,
        }
        _, created = Listing.objects.update_or_create(
            user=seller,
            title=item["title"],
            defaults=content,
            create_defaults={
                **content,
                "status": ListingStatus.PUBLISHED,
                "published_at": now,
            },
        )
        created_count += created
    return created_count


def home_categories():
    """Catégories principales affichées en tuiles sur l'accueil (design/components/CategoryTile)."""
    return Category.objects.filter(parent__isnull=True).order_by("order", "name")[
        :HOME_CATEGORY_COUNT
    ]
