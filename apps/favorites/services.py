from apps.listings.models import PUBLISHED_STATUSES, Listing
from apps.listings.services import with_cover

from .models import Favorite


def set_favorite(user, listing: Listing, on: bool) -> bool:
    """Met l'annonce en favori ou l'en retire. Le bouton envoie l'état voulu, pas « inverser » :
    un double clic ou une requête rejouée ne change rien. Renvoie l'état final."""
    if on:
        # get_or_create rattrape la violation d'unicité si deux requêtes se croisent.
        Favorite.objects.get_or_create(user=user, listing=listing)
    else:
        Favorite.objects.filter(user=user, listing=listing).delete()
    return on


def favorite_ids(user) -> frozenset[int]:
    """Identifiants des annonces en favori : une requête par page, quel que soit le nombre de
    cartes affichées."""
    return frozenset(Favorite.objects.filter(user=user).values_list("listing_id", flat=True))


def favorite_listings(user):
    """Page « Mes favoris » : les plus récemment ajoutées d'abord. Une annonce vendue reste
    (on voit ce qu'elle est devenue), une annonce retirée disparaît."""
    return with_cover(
        Listing.objects.filter(favorited_by__user=user, status__in=PUBLISHED_STATUSES)
    ).order_by("-favorited_by__created_at", "-favorited_by__pk")
