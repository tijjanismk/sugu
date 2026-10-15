from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("recherche/", views.search, name="search"),
    # Pages catégorie et ville (référencement, ticket #9)
    path("categorie/<slug:category>/", views.browse, name="category"),
    path("categorie/<slug:category>/<slug:city>/", views.browse, name="category_city"),
    path("ville/<slug:city>/", views.browse, name="city"),
    path("deposer/", views.listing_create, name="create"),
    path("annonce/<int:pk>-<slug:slug>/", views.listing_detail, name="detail"),
    path("mes-annonces/", views.my_listings, name="mine"),
    path("annonce/<int:pk>/modifier/", views.listing_edit, name="edit"),
    path("annonce/<int:pk>/vendue/", views.listing_mark_sold, name="mark_sold"),
    path("annonce/<int:pk>/supprimer/", views.listing_delete, name="delete"),
    path("annonce/<int:pk>/photos/ajouter/", views.photo_add, name="photo_add"),
    path(
        "annonce/<int:pk>/photos/<int:photo_pk>/retirer/",
        views.photo_remove,
        name="photo_remove",
    ),
]
