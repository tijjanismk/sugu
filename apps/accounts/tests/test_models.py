import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_identifie_par_email_normalise():
    user = User.objects.create_user(
        email="Awa@EXAMPLE.ML", password="Baobab-2026-solide", display_name="Awa"
    )
    assert user.email == "Awa@example.ml"
    assert user.check_password("Baobab-2026-solide")
    assert not user.is_staff
    assert not user.is_superuser
    assert not user.phone_verified
    assert str(user) == "Awa"


@pytest.mark.django_db
def test_create_user_sans_email_refuse():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x", display_name="Sans email")


@pytest.mark.django_db
def test_create_superuser_a_les_droits_admin():
    admin = User.objects.create_superuser(
        email="admin@example.ml", password="Baobab-2026-solide", display_name="Admin"
    )
    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.django_db
def test_create_superuser_sans_is_staff_refuse():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.ml", password="x", display_name="Admin", is_staff=False
        )


@pytest.mark.django_db
def test_email_unique():
    User.objects.create_user(email="awa@example.ml", password="x", display_name="Awa")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="awa@example.ml", password="y", display_name="Awa 2")


def test_pas_de_nom_utilisateur():
    assert User.USERNAME_FIELD == "email"
    field_names = {f.name for f in User._meta.get_fields()}
    assert "username" not in field_names
    assert {"display_name", "phone", "phone_verified"} <= field_names
