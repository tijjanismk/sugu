"""Parcours 2 (docs/tests.md) : un acheteur contacte un vendeur → le vendeur voit le message et
répond ; la réponse arrive chez l'acheteur sans recharger (rafraîchissement htmx 10 s)."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

FIRST_MESSAGE = "Bonjour, l'objet est-il toujours disponible ?"
REPLY = "Oui, toujours disponible. Passez demain."


def test_acheteur_contacte_vendeur_qui_repond(seller, buyer, listing):
    # L'acheteur écrit depuis l'annonce, avec le message proposé.
    buyer.page.goto(listing.url)
    buyer.page.get_by_role("link", name="Écrire au vendeur").click()
    expect(buyer.page.get_by_label("Message", exact=True)).to_have_value(FIRST_MESSAGE)
    buyer.page.get_by_role("button", name="Envoyer").click()
    expect(buyer.page.locator(".sg-msg--me", has_text=FIRST_MESSAGE)).to_be_visible()
    conversation_url = buyer.page.url

    # Le vendeur voit la pastille de non-lus, ouvre la conversation et répond.
    seller.page.goto("/")
    expect(seller.page.locator(".sg-bottomnav__count")).to_contain_text("1")
    seller.page.goto("/messages/")
    seller.page.locator(".sg-list__item", has_text=listing.title).click()
    expect(seller.page.locator(".sg-msg", has_text=FIRST_MESSAGE)).to_be_visible()
    seller.page.get_by_label("Message", exact=True).fill(REPLY)
    seller.page.get_by_label("Message", exact=True).press("Enter")
    expect(seller.page.locator(".sg-msg--me", has_text=REPLY)).to_be_visible()
    expect(seller.page.get_by_label("Message", exact=True)).to_have_value(
        ""
    )  # champ vidé après l'envoi

    # Ouvrir la conversation a remis le compteur à zéro.
    seller.page.goto("/")
    expect(seller.page.locator(".sg-bottomnav__count")).to_have_count(0)

    # La réponse arrive chez l'acheteur sans qu'il recharge la page.
    assert buyer.page.url == conversation_url
    reply = buyer.page.locator(".sg-msg:not(.sg-msg--me)", has_text=REPLY)
    expect(reply).to_be_visible(timeout=15_000)
