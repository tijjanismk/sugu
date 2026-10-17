from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("annonce/<int:pk>/signaler/", views.report_listing, name="report"),
]
