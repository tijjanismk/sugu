from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from apps.listings.images import thumb_file
from apps.listings.models import Photo


class Command(BaseCommand):
    help = (
        "Refait les miniatures des cartes depuis la version 1200 px : photo entière, jamais "
        "recadrée (ticket #8, 2026-10-15). Sans risque à relancer."
    )

    def handle(self, *args, **options):
        done = 0
        for photo in Photo.objects.order_by("pk").iterator():
            with photo.large.open("rb") as file:
                large = Image.open(file)
                large.load()
            old = photo.thumb.name
            photo.thumb.save(
                f"{uuid4().hex}-400.webp", thumb_file(large.convert("RGB")), save=False
            )
            photo.save(update_fields=["thumb"])
            # L'ancienne miniature n'est effacée qu'une fois la nouvelle enregistrée.
            transaction.on_commit(
                lambda name=old, storage=photo.thumb.storage: storage.delete(name)
            )
            done += 1
        self.stdout.write(f"{done} miniature(s) refaite(s).")
