"""Parcours 3 (docs/tests.md) : ajout et retrait d'un favori depuis la liste, sans recharger."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_ajout_et_retrait_dun_favori(buyer, listing):
    page = buyer.page
    page.goto(f"/recherche/?q={listing.word}")
    heart = page.get_by_role("button", name=f"Ajouter aux favoris : {listing.title}")
    expect(heart).to_have_attribute("aria-pressed", "false")

    page.evaluate("window.sansRechargement = true")
    heart.click()
    expect(heart).to_have_attribute("aria-pressed", "true")
    assert page.evaluate("window.sansRechargement") is True  # bascule htmx, page intacte

    page.goto("/favoris/")
    heart = page.get_by_role("button", name=f"Ajouter aux favoris : {listing.title}")
    expect(heart).to_have_attribute("aria-pressed", "true")
    heart.click()
    expect(heart).to_have_attribute("aria-pressed", "false")

    page.reload()
    expect(page.get_by_text("Aucun favori pour l'instant")).to_be_visible()
