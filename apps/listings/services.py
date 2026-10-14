import re
from dataclasses import dataclass
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .images import process_photo
from .models import (
    MAX_PHOTOS,
    PUBLISHED_STATUSES,
    SEARCH_CONFIG,
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


MAX_SEARCH_TERMS = 8
_WORD = re.compile(r"[^\W_]+")


def search_query(text: str) -> SearchQuery | None:
    """Mots-clés → requête plein texte. Chaque mot est cherché aussi en début de mot (« sams »
    trouve « Samsung ») et tous doivent être présents. Seuls lettres et chiffres atteignent
    PostgreSQL : la syntaxe tsquery (& | ! : *) saisie par l'utilisateur est neutralisée."""
    words = _WORD.findall(text.lower())[:MAX_SEARCH_TERMS]
    if not words:
        return None
    raw = " & ".join(_term(word) for word in words)
    return SearchQuery(raw, config=SEARCH_CONFIG, search_type="raw")


def _term(word: str) -> str:
    """Le racinisateur français laisse « vélos » intact (il ne retire le pluriel que de certains
    mots) : un mot en -s ou -x est aussi cherché sans sa dernière lettre (vélos → vélo)."""
    if len(word) > 3 and word[-1] in "sx":
        return f"({word}:* | {word[:-1]}:*)"
    return f"{word}:*"


def search_listings(*, q=None, category=None, city=None, price_min=None, price_max=None):
    """Recherche (ticket #9) parmi les annonces publiées : les vendues et retirées n'y sont
    jamais. Une catégorie principale inclut ses sous-catégories. Un filtre de prix écarte les
    annonces « à débattre ». Avec des mots-clés : les plus pertinentes d'abord (mot dans le
    titre > quartier > description), puis les plus récentes ; sans mot-clé : par date."""
    listings = Listing.objects.filter(status=ListingStatus.PUBLISHED)
    if category is not None:
        listings = listings.filter(Q(category=category) | Q(category__parent=category))
    if city is not None:
        listings = listings.filter(city=city)
    if price_min is not None:
        listings = listings.filter(price__gte=price_min)
    if price_max is not None:
        listings = listings.filter(price__lte=price_max)

    query = search_query(q or "")
    if query is None:
        return with_cover(listings).order_by("-published_at", "-pk")
    listings = listings.filter(search_vector=query).annotate(
        rank=SearchRank(F("search_vector"), query)
    )
    return with_cover(listings).order_by("-rank", "-published_at", "-pk")


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


def _process_all(photos: list, *, first_number: int = 1) -> list:
    """Traite toutes les photos avant la moindre écriture : une seule refusée, rien n'est fait."""
    processed = []
    for index, uploaded in enumerate(photos, start=first_number):
        try:
            processed.append(process_photo(uploaded))
        except ValidationError as exc:
            raise ValidationError(f"Photo {index} : {' '.join(exc.messages)}") from exc
    return processed


def _store_photos(listing: Listing, processed: list, first_order: int, written: list) -> None:
    """Écrit les versions WebP et crée les Photo ; `written` reçoit les fichiers écrits pour
    pouvoir les effacer si la transaction échoue."""
    for order, photo in enumerate(processed, start=first_order):
        name = uuid4().hex
        item = Photo(listing=listing, order=order, width=photo.width, height=photo.height)
        item.large.save(f"{name}-1200.webp", photo.large, save=False)
        written.append(item.large)
        item.thumb.save(f"{name}-400.webp", photo.thumb, save=False)
        written.append(item.thumb)
        item.save()


def _delete_files(files: list) -> None:
    for file in files:
        file.storage.delete(file.name)


def create_listing(user, *, data: dict, photos: list) -> Listing:
    """Crée et publie une annonce avec ses photos (ticket #7).

    Toutes les photos sont traitées avant la moindre écriture : si l'une est refusée, rien
    n'est enregistré. Seules les versions WebP sont stockées, jamais l'original.
    `data` : title, description, category, city, neighborhood, distance_km, price,
    payment_methods (formulaire validé).
    """
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ValidationError(f"Ajoutez de 1 à {MAX_PHOTOS} photos.")
    processed = _process_all(photos)

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
            _store_photos(listing, processed, 0, written)
            publish(listing)
    except Exception:
        _delete_files(written)
        raise
    return listing


# --- Gestion par le vendeur (ticket #10) --------------------------------------------------
# Les vues vérifient déjà le propriétaire (403) ; les services le revérifient : une action ne
# peut jamais porter sur l'annonce d'un autre, quel que soit le chemin qui l'appelle.

EDITABLE_STATUSES = (ListingStatus.DRAFT, ListingStatus.PUBLISHED)
EDITABLE_FIELDS = (
    "title",
    "description",
    "category",
    "city",
    "neighborhood",
    "distance_km",
    "payment_methods",
)


def check_owner(listing: Listing, user) -> None:
    if not user.is_authenticated or listing.user_id != user.pk:
        raise PermissionDenied("Cette annonce ne vous appartient pas.")


def _check_editable(listing: Listing) -> None:
    if listing.status not in EDITABLE_STATUSES:
        raise ValidationError("Une annonce vendue ou supprimée ne se modifie plus.")


@transaction.atomic
def update_listing(user, listing: Listing, data: dict) -> Listing:
    """Modifie le contenu d'une annonce ; le prix passe par update_price (baisse mémorisée)."""
    check_owner(listing, user)
    locked = Listing.objects.select_for_update().get(pk=listing.pk)
    _check_editable(locked)
    for field in EDITABLE_FIELDS:
        value = data.get(field)
        if field == "neighborhood":
            value = value or ""
        elif field == "payment_methods":
            value = list(value or [])
        setattr(locked, field, value)
    # Titre, quartier et description dans update_fields : le trigger recalcule la recherche.
    locked.save(update_fields=[*EDITABLE_FIELDS, "updated_at"])
    update_price(locked, data.get("price"))
    return locked


def seller_mark_sold(user, listing: Listing) -> Listing:
    check_owner(listing, user)
    return mark_sold(listing)


def seller_remove(user, listing: Listing) -> Listing:
    """« Supprimer » pour le vendeur : statut removed, l'annonce disparaît partout. Rien n'est
    effacé en base ni sur le stockage (preuves en cas de litige, docs/security.md)."""
    check_owner(listing, user)
    return remove(listing)


def add_photos(user, listing: Listing, photos: list) -> None:
    """Ajoute des photos à la suite des existantes, 6 au plus au total."""
    check_owner(listing, user)
    _check_editable(listing)
    if not photos:
        raise ValidationError("Choisissez au moins une photo.")
    existing = listing.photos.count()
    if existing + len(photos) > MAX_PHOTOS:
        raise ValidationError(
            f"{MAX_PHOTOS} photos au plus : vous pouvez en ajouter {MAX_PHOTOS - existing}."
        )
    processed = _process_all(photos, first_number=existing + 1)
    written = []
    try:
        with transaction.atomic():
            Listing.objects.select_for_update().get(pk=listing.pk)
            start = listing.photos.count()  # relu sous verrou
            if start + len(processed) > MAX_PHOTOS:
                raise ValidationError(f"{MAX_PHOTOS} photos au plus.")
            _store_photos(listing, processed, start, written)
    except Exception:
        _delete_files(written)
        raise


@transaction.atomic
def remove_photo(user, photo: Photo) -> None:
    """Retire une photo et renumérote les suivantes : si c'était la couverture (0), la suivante
    devient la couverture. Une annonce garde au moins une photo."""
    listing = Listing.objects.select_for_update().get(pk=photo.listing_id)
    check_owner(listing, user)
    _check_editable(listing)
    if listing.photos.count() <= 1:
        raise ValidationError("Une annonce garde au moins une photo : ajoutez-en une autre avant.")
    removed_order = photo.order
    photo.delete()  # les fichiers sont effacés après validation (signals.py)
    # Ordre croissant : chaque rang libéré est réoccupé avant le suivant (contrainte unique).
    for later in listing.photos.filter(order__gt=removed_order).order_by("order"):
        later.order -= 1
        later.save(update_fields=["order", "updated_at"])


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
