from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.listings.sitemaps import SITEMAPS

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),  # secrète en production (ticket #15)
    path("comptes/", include("apps.accounts.urls")),
    path("", include("apps.listings.urls")),
    path("", include("apps.favorites.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.core.urls")),
    # Référencement (ticket #15, 2026-10-15)
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
