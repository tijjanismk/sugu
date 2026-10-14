from django.apps import AppConfig


class ListingsConfig(AppConfig):
    name = "apps.listings"
    verbose_name = "Annonces"

    def ready(self):
        from . import signals  # noqa: F401
