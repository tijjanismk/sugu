from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("deposer/", views.listing_create, name="create"),
]
