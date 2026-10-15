"""Traitement des photos d'annonce (ticket #7, docs/security.md « Entrées utilisateur »).

Chaque photo est ouverte par Pillow puis **réencodée** en WebP : un fichier qui n'est pas une
image valide est rejeté, les métadonnées (EXIF, dont la position GPS) disparaissent, et
l'original n'est jamais conservé. Deux versions : 1200 px proportionnelle pour la page de
l'annonce, miniature proportionnelle qui tient dans 400×300 pour la carte. Jamais recadrée
(retour du 2026-10-15 : un logo carré perdait son haut et son bas) : la carte la centre
sur son fond.
"""

import io
import math
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

LARGE_MAX_SIZE = 1200
THUMB_SIZE = (400, 300)
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
# Au-delà, l'image est refusée avant décodage (protection contre les bombes de décompression).
MAX_PIXELS = 40_000_000
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP"}
LARGE_QUALITY = 80
THUMB_QUALITY = 75
# Effort d'encodage WebP (0-6) : 2 est près de trois fois plus rapide que 4, pour 1 % de poids
# en plus ; c'est ce qui tient le dépôt de 3 photos sous 5 s (ticket #7).
WEBP_METHOD = 2

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@dataclass
class ProcessedPhoto:
    large: ContentFile
    thumb: ContentFile
    width: int
    height: int


def _open_verified(uploaded) -> Image.Image:
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"Photo trop lourde ({uploaded.size // (1024 * 1024)} Mo). 8 Mo au plus.",
            code="too_large",
        )
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as probe:
            if probe.format not in ACCEPTED_FORMATS:
                raise ValidationError(
                    "Format non accepté : envoyez une photo JPEG, PNG ou WebP.", code="format"
                )
            if probe.width * probe.height > MAX_PIXELS:
                raise ValidationError("Image trop grande en pixels.", code="too_many_pixels")
            probe.verify()  # détecte un fichier tronqué ou corrompu
        uploaded.seek(0)
        image = Image.open(uploaded)
        if image.format == "JPEG":
            # Décode directement à 1/2, 1/4 ou 1/8 de la taille tant que le grand côté garde
            # 1200 px : bien plus rapide sur une photo de téléphone de 12 Mpx.
            scale = LARGE_MAX_SIZE / max(image.size)
            image.draft("RGB", (math.ceil(image.width * scale), math.ceil(image.height * scale)))
        image.load()
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError(
            "Ce fichier n'est pas une image valide.", code="invalid_image"
        ) from exc
    return image


def _to_rgb(image: Image.Image) -> Image.Image:
    """Aplati la transparence sur fond blanc : une photo d'annonce n'en a pas besoin."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _webp(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    # Aucun paramètre exif / icc_profile : le fichier produit ne contient aucune métadonnée.
    image.save(buffer, format="WEBP", quality=quality, method=WEBP_METHOD)
    return buffer.getvalue()


def make_thumb(large: Image.Image) -> Image.Image:
    """Miniature de carte depuis la version 1200 px : la photo entière, dans 400×300."""
    return ImageOps.contain(large, THUMB_SIZE, Image.Resampling.LANCZOS)


def thumb_file(large: Image.Image) -> ContentFile:
    return ContentFile(_webp(make_thumb(large), THUMB_QUALITY))


def process_photo(uploaded) -> ProcessedPhoto:
    """Valide et réencode une photo envoyée. Lève ValidationError si elle est refusée."""
    image = _open_verified(uploaded)
    image = ImageOps.exif_transpose(image)  # applique l'orientation avant de jeter l'EXIF
    image = _to_rgb(image)

    large = image.copy()
    large.thumbnail((LARGE_MAX_SIZE, LARGE_MAX_SIZE), Image.Resampling.LANCZOS)  # sans agrandir

    return ProcessedPhoto(
        large=ContentFile(_webp(large, LARGE_QUALITY)),
        thumb=thumb_file(large),
        width=large.width,
        height=large.height,
    )
