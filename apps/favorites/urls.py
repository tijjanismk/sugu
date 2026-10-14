from django.urls import path

from . import views

app_name = "favorites"

urlpatterns = [
    path("favoris/", views.favorite_list, name="list"),
    path("favoris/<int:listing_pk>/", views.favorite_set, name="set"),
]
