"""Images générées en mémoire pour les tests (aucun fichier réel)."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

GPS_IFD = 0x8825
ORIENTATION = 0x0112
MAKE = 0x010F


def image_bytes(width=800, height=600, fmt="JPEG", mode="RGB", color=(200, 80, 40), exif=None):
    image = Image.new(mode, (width, height), color)
    buffer = io.BytesIO()
    kwargs = {"exif": exif} if exif is not None else {}
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def uploaded(name="photo.jpg", content=None, content_type="image/jpeg", **image_kwargs):
    if content is None:
        content = image_bytes(**image_kwargs)
    return SimpleUploadedFile(name, content, content_type=content_type)


def exif_with_gps(orientation=None):
    """EXIF d'une photo de téléphone : marque, position GPS, orientation facultative."""
    exif = Image.Exif()
    exif[MAKE] = "Tecno"
    if orientation:
        exif[ORIENTATION] = orientation
    exif[GPS_IFD] = {1: "N", 2: (12.0, 38.0, 0.0), 3: "W", 4: (8.0, 0.0, 0.0)}
    return exif
