from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("sante/", views.health, name="health"),
    # Application installable (ticket #14). Le service worker est à la racine pour couvrir
    # tout le site (un fichier sous /static/ ne contrôlerait que /static/).
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("hors-ligne/", views.offline, name="offline"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("robots.txt", views.robots_txt, name="robots"),
    # Pages légales et « À propos » (ticket #17), liées dans le pied de page.
    path(
        "a-propos/",
        TemplateView.as_view(template_name="legal/about.html", extra_context=views.ABOUT),
        name="about",
    ),
    path(
        "mentions-legales/",
        TemplateView.as_view(template_name="legal/legal_notice.html", extra_context=views.LEGAL),
        name="legal_notice",
    ),
    path(
        "confidentialite/",
        TemplateView.as_view(template_name="legal/privacy.html", extra_context=views.PRIVACY),
        name="privacy",
    ),
]
