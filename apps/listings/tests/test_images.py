"""Service d'images (ticket #7) : tests unitaires sur des images générées en mémoire."""

import io

import pytest
from django.core.exceptions import ValidationError
from PIL import Image

from apps.listings import images
from apps.listings.images import THUMB_SIZE, process_photo

from .images import GPS_IFD, exif_with_gps, image_bytes, uploaded


def _open(content_file):
    content_file.seek(0)
    image = Image.open(io.BytesIO(content_file.read()))
    image.load()
    return image


def test_une_grande_photo_donne_1200_px_et_une_miniature_400x300():
    result = process_photo(uploaded(width=3000, height=2000))

    large, thumb = _open(result.large), _open(result.thumb)
    assert (large.width, large.height) == (1200, 800)
    assert (result.width, result.height) == (1200, 800)
    assert thumb.size == THUMB_SIZE
    assert large.format == "WEBP"
    assert thumb.format == "WEBP"


def test_une_photo_portrait_garde_ses_proportions():
    result = process_photo(uploaded(width=1500, height=3000))

    assert (result.width, result.height) == (600, 1200)
    assert _open(result.thumb).size == THUMB_SIZE  # recadrée au format de la carte


def test_une_petite_photo_n_est_pas_agrandie():
    result = process_photo(uploaded(width=640, height=480))

    assert (result.width, result.height) == (640, 480)


def test_l_exif_et_la_position_gps_sont_retires():
    source = image_bytes(exif=exif_with_gps())
    assert Image.open(io.BytesIO(source)).getexif().get_ifd(GPS_IFD)  # la source a bien un GPS

    result = process_photo(uploaded(content=source))

    for version in (result.large, result.thumb):
        image = _open(version)
        assert len(image.getexif()) == 0
        assert "exif" not in image.info
        assert "icc_profile" not in image.info


def test_l_orientation_exif_est_appliquee_avant_d_etre_retiree():
    # Photo prise téléphone tourné : pixels en paysage 1600×1200, EXIF « tourner de 90° ».
    source = image_bytes(width=1600, height=1200, exif=exif_with_gps(orientation=6))

    result = process_photo(uploaded(content=source))

    assert (result.width, result.height) == (900, 1200)  # affichée en portrait


def test_la_transparence_est_aplatie_sur_fond_blanc():
    source = image_bytes(width=500, height=500, fmt="PNG", mode="RGBA", color=(0, 0, 0, 0))

    result = process_photo(uploaded(name="logo.png", content=source, content_type="image/png"))

    large = _open(result.large)
    assert large.mode == "RGB"
    assert large.getpixel((10, 10)) == pytest.approx((255, 255, 255), abs=3)


def test_un_webp_est_accepte():
    source = image_bytes(fmt="WEBP")

    result = process_photo(uploaded(name="p.webp", content=source, content_type="image/webp"))

    assert _open(result.large).format == "WEBP"


def test_un_fichier_qui_n_est_pas_une_image_est_rejete():
    faux = uploaded(name="photo.jpg", content=b"%PDF-1.7 ceci n'est pas une photo")

    with pytest.raises(ValidationError) as excinfo:
        process_photo(faux)
    assert excinfo.value.code == "invalid_image"


def test_un_script_deguise_en_photo_est_rejete():
    faux = uploaded(name="photo.jpg", content=b"<script>alert(1)</script>")

    with pytest.raises(ValidationError):
        process_photo(faux)


def test_une_image_tronquee_est_rejetee():
    entiere = image_bytes(width=1200, height=900)

    with pytest.raises(ValidationError):
        process_photo(uploaded(content=entiere[: len(entiere) // 2]))


def test_un_format_non_accepte_est_rejete():
    gif = image_bytes(fmt="GIF", mode="P", color=1)

    with pytest.raises(ValidationError) as excinfo:
        process_photo(uploaded(name="anim.gif", content=gif, content_type="image/gif"))
    assert excinfo.value.code == "format"


def test_une_image_geante_en_pixels_est_rejetee_avant_decodage(monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 100 * 100)

    with pytest.raises(ValidationError) as excinfo:
        process_photo(uploaded(width=200, height=200))
    assert excinfo.value.code == "too_many_pixels"


def test_une_photo_trop_lourde_est_rejetee(monkeypatch):
    monkeypatch.setattr(images, "MAX_UPLOAD_BYTES", 1000)

    with pytest.raises(ValidationError) as excinfo:
        process_photo(uploaded(width=800, height=600))
    assert excinfo.value.code == "too_large"
