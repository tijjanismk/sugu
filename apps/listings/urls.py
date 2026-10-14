from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("recherche/", views.search, name="search"),
    path("deposer/", views.listing_create, name="create"),
    path("annonce/<int:pk>-<slug:slug>/", views.listing_detail, name="detail"),
]
