"""Référencement de la page annonce (ticket #8, ajout du 2026-10-15) : description, aperçu de
partage (Open Graph) et données structurées schema.org pour les résultats enrichis de Google."""

import json

from django.http import HttpRequest
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

from apps.core.templatetags.sugu_format import fcfa

from .models import Listing, ListingStatus

DESCRIPTION_LENGTH = 155
AVAILABILITY = {
    ListingStatus.PUBLISHED: "https://schema.org/InStock",
    ListingStatus.RESERVED: "https://schema.org/LimitedAvailability",
    ListingStatus.SOLD: "https://schema.org/SoldOut",
}


def _json_ld(data: dict) -> str:
    """JSON pour <script type="application/ld+json"> : <, > et & échappés, comme json_script,
    pour qu'un titre ne puisse pas fermer la balise."""
    text = json.dumps(data, ensure_ascii=False)
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        text = text.replace(char, escaped)
    return mark_safe(text)  # noqa: S308 — échappé ci-dessus


def listing_seo(request: HttpRequest, listing: Listing) -> dict:
    """`seo` pour base.html, et `structured_data` (JSON-LD) pour la page annonce."""
    url = request.build_absolute_uri(listing.get_absolute_url())
    summary = " ".join(strip_tags(listing.description).split())
    description = Truncator(f"{fcfa(listing.price)} · {listing.place_label} — {summary}").chars(
        DESCRIPTION_LENGTH
    )
    photos = list(listing.photos.all())
    images = [request.build_absolute_uri(photo.large.url) for photo in photos]

    seo = {
        "description": description,
        "og_title": f"{listing.title} · {fcfa(listing.price)}",
        "og_type": "product",
        # Annonce vendue : gardée pour mémoire, mais plus proposée par les moteurs de recherche.
        "noindex": listing.status == ListingStatus.SOLD,
    }
    if photos:
        seo.update(image=images[0], image_width=photos[0].width, image_height=photos[0].height)

    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": listing.title,
        "description": Truncator(summary).chars(500),
        "category": listing.category.name,
        "url": url,
    }
    if images:
        product["image"] = images
    if listing.price is not None:  # « À débattre » : pas d'offre chiffrée
        product["offers"] = {
            "@type": "Offer",
            "price": str(listing.price),
            "priceCurrency": "XOF",
            "availability": AVAILABILITY.get(ListingStatus(listing.status)),
            "url": url,
            "seller": {"@type": "Person", "name": listing.user.display_name},
        }
    return {"seo": seo, "structured_data": _json_ld(product)}
