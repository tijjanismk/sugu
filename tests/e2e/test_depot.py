"""Parcours 1 (docs/tests.md) : inscription → dépôt d'une annonce avec photo → l'annonce
apparaît en recherche. L'inscription et le dépôt sont faits par les fixtures `seller` et
`listing` (conftest.py)."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_annonce_deposee_trouvee_en_recherche(seller, listing):
    page = seller.page

    # La page de l'annonce montre la photo réencodée par le serveur.
    page.goto(listing.url)
    expect(page.locator(".sg-gallery img")).to_have_count(1)

    page.goto(f"/recherche/?q={listing.word}")
    card = page.locator(".sg-card", has_text=listing.title)
    expect(card).to_be_visible()
    expect(card.locator("img")).to_be_visible()  # miniature de couverture
    card.click()
    expect(page).to_have_url(listing.url)
