"""Admin des annonces : pages accessibles et actions de modération passant par services.py."""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.listings.models import ListingStatus

from .factories import ListingFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser(
        email="admin@example.ml", password="Baobab-2026-solide", display_name="Admin"
    )
    client.force_login(admin)
    return client


def test_les_pages_admin_des_annonces_s_affichent(admin_client):
    listing = ListingFactory(published=True)

    assert admin_client.get(reverse("admin:listings_listing_changelist")).status_code == 200
    page = admin_client.get(reverse("admin:listings_listing_change", args=[listing.pk]))
    assert page.status_code == 200


def test_l_action_retirer_passe_par_les_transitions(admin_client):
    published = ListingFactory(published=True)
    removed = ListingFactory(status=ListingStatus.REMOVED)

    admin_client.post(
        reverse("admin:listings_listing_changelist"),
        {"action": "action_remove", "_selected_action": [published.pk, removed.pk]},
    )

    published.refresh_from_db()
    removed.refresh_from_db()
    assert published.status == ListingStatus.REMOVED
    assert removed.status == ListingStatus.REMOVED


def test_un_non_staff_n_accede_pas_a_l_admin(client):
    client.force_login(User.objects.create_user(email="u@example.ml", display_name="U"))

    response = client.get(reverse("admin:listings_listing_changelist"))

    assert response.status_code == 302
