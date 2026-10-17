from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Banner


@receiver(post_delete, sender=Banner)
def delete_banner_files(sender, instance: Banner, **kwargs):
    """Supprime les deux fichiers WebP d'une bannière une fois la suppression validée."""
    files = [f for f in (instance.image, instance.image_small) if f and f.name]

    def _delete():
        for file in files:
            file.storage.delete(file.name)

    transaction.on_commit(_delete)
