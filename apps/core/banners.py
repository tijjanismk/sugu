"""Bannières de l'accueil (ticket #8, ajout du 2026-10-17).

Gérées dans l'admin. L'image envoyée est vérifiée et réencodée en WebP comme une photo
d'annonce (apps/listings/images.py) : 1200 px et 600 px de large, sans métadonnées. Format
attendu 2:1 ; une image d'un autre format est refusée plutôt que recadrée, pour ne jamais
couper le texte écrit dessus (retour du 2026-10-15 sur les photos tronquées).
"""

import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image

from apps.listings.images import open_image, webp_file

from .models import Banner

LARGE_WIDTH = 1200
SMALL_WIDTH = 600
RATIO = 2.0
RATIO_TOLERANCE = 0.1  # 1200 × 545 à 1200 × 667 passent
MAX_SHOWN = 5  # au-delà, personne ne fait défiler ; garde l'accueil léger


@dataclass
class ProcessedBanner:
    large: ContentFile
    small: ContentFile
    width: int
    height: int


def _resized(image: Image.Image, width: int) -> Image.Image:
    if image.width <= width:
        return image.copy()  # jamais agrandie
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def process_banner(uploaded) -> ProcessedBanner:
    """Valide et réencode l'image d'une bannière. Lève ValidationError si elle est refusée."""
    image = open_image(uploaded)
    ratio = image.width / image.height
    if abs(ratio - RATIO) > RATIO * RATIO_TOLERANCE:
        raise ValidationError(
            f"Format attendu : deux fois plus large que haute, par exemple 1200 × 600 px. "
            f"Votre image : {image.width} × {image.height} px.",
            code="ratio",
        )
    if image.width < SMALL_WIDTH:
        raise ValidationError(
            f"Image trop petite : {SMALL_WIDTH} px de large au moins, {LARGE_WIDTH} conseillés.",
            code="too_small",
        )
    large = _resized(image, LARGE_WIDTH)
    return ProcessedBanner(
        large=webp_file(large),
        small=webp_file(_resized(image, SMALL_WIDTH)),
        width=large.width,
        height=large.height,
    )


def set_image(banner: Banner, processed: ProcessedBanner) -> None:
    """Pose les fichiers d'une image traitée (sans enregistrer la bannière). Les fichiers
    d'une image remplacée sont effacés une fois la transaction validée."""
    old = [f.name for f in (banner.image, banner.image_small) if f and f.name]
    name = uuid.uuid4().hex
    banner.image.save(f"{name}-1200.webp", processed.large, save=False)
    banner.image_small.save(f"{name}-600.webp", processed.small, save=False)
    banner.width, banner.height = processed.width, processed.height
    if old:
        storage = banner.image.storage
        transaction.on_commit(lambda: [storage.delete(n) for n in old])


def active_banners(now=None) -> list[Banner]:
    """Bannières à afficher : actives et dans leur période, dans l'ordre choisi."""
    now = now or timezone.now()
    return list(
        Banner.objects.filter(is_active=True)
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))[:MAX_SHOWN]
    )
