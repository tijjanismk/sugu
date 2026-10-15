"""Plan du site pour les moteurs de recherche (référencement, ticket #15, 2026-10-15) : servi à
/sitemap.xml, annoncé dans /robots.txt et dans Google Search Console."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from . import services
from .models import Category, City, Listing


class HomeSitemap(Sitemap):
    changefreq = "hourly"
    priority = 1.0

    def items(self):
        return ["core:home"]

    def location(self, item):
        return reverse(item)


class BrowseSitemap(Sitemap):
    """Pages catégorie et ville qui ont au moins une annonce en ligne (les autres ne sont pas
    indexées)."""

    changefreq = "daily"
    priority = 0.8

    def items(self):
        categories = dict(Category.objects.values_list("pk", "slug"))
        cities = dict(City.objects.values_list("pk", "slug"))
        pages = []
        for (category_id, city_id), count in services.published_counts().items():
            if not count:
                continue
            if category_id and city_id:
                args = [categories[category_id], cities[city_id]]
                pages.append(reverse("listings:category_city", args=args))
            elif category_id:
                pages.append(reverse("listings:category", args=[categories[category_id]]))
            else:
                pages.append(reverse("listings:city", args=[cities[city_id]]))
        return sorted(pages)

    def location(self, item):
        return item


class ListingSitemap(Sitemap):
    """Annonces en ligne ou réservées ; les vendues ne sont plus proposées (noindex)."""

    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return (
            Listing.objects.filter(status__in=services.INDEXED_STATUSES)
            .only("pk", "title", "updated_at")
            .order_by("-published_at", "-pk")
        )

    def lastmod(self, listing):
        return listing.updated_at


SITEMAPS = {"accueil": HomeSitemap, "pages": BrowseSitemap, "annonces": ListingSitemap}
