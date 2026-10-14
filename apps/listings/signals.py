from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Photo


@receiver(post_delete, sender=Photo)
def delete_photo_files(sender, instance: Photo, **kwargs):
    """Supprime les fichiers WebP (disque en dev, R2 en prod) une fois la suppression validée.
    Aussi appelé pour chaque photo quand l'annonce est supprimée (cascade)."""
    files = [f for f in (instance.large, instance.thumb) if f and f.name]

    def _delete():
        for file in files:
            file.storage.delete(file.name)

    transaction.on_commit(_delete)
