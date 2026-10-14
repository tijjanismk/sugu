from django.urls import path

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
]
