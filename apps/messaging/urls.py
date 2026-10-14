from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("messages/", views.inbox, name="inbox"),
    path("messages/<int:pk>/", views.conversation, name="conversation"),
    path("messages/<int:pk>/nouveaux/", views.poll, name="poll"),
    path("annonce/<int:listing_pk>/contacter/", views.start, name="start"),
]
