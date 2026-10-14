"""Comptes partagés par les parcours de bout en bout (ticket #16, docs/tests.md).

L'inscription est limitée à 3 par heure et par IP (docs/security.md) : les parcours partagent
un vendeur et un acheteur, inscrits une fois par session de tests. Chacun a son propre
navigateur (contexte Playwright), au format téléphone, comme les utilisateurs de Sugu.
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from PIL import Image
from playwright.sync_api import Browser, Page, expect

PASSWORD = "Baobab-2026-solide"
PHONE = {"width": 375, "height": 812}


@dataclass
class Account:
    page: Page
    email: str
    name: str


@dataclass
class Listing:
    title: str
    word: str  # mot unique du titre, pour le retrouver par la recherche
    url: str


def sign_up(browser: Browser, base_url: str, name: str) -> Account:
    context = browser.new_context(base_url=base_url, viewport=PHONE, locale="fr-FR")
    page = context.new_page()
    email = f"{name.lower()}-{uuid4().hex[:8]}@example.ml"
    page.goto("/comptes/inscription/")
    page.fill('input[name="display_name"]', name)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password1"]', PASSWORD)
    page.get_by_role("button", name="Créer mon compte").click()
    expect(page.get_by_role("link", name="Mes annonces")).to_be_visible()
    return Account(page, email, name)


@pytest.fixture(scope="session")
def photo(tmp_path_factory):
    path = tmp_path_factory.mktemp("photos") / "velo.jpg"
    Image.new("RGB", (1200, 900), "#2b3c8e").save(path, quality=85)
    return path


@pytest.fixture(scope="session")
def seller(browser, base_url):
    account = sign_up(browser, base_url, "Aminata")
    yield account
    account.page.context.close()


@pytest.fixture(scope="session")
def buyer(browser, base_url):
    account = sign_up(browser, base_url, "Moussa")
    yield account
    account.page.context.close()


def post_listing(page: Page, photo) -> Listing:
    """Dépôt d'une annonce avec photo, par le formulaire (sélecteur de photos compris)."""
    word = f"e2e{uuid4().hex[:6]}"
    title = f"Vélo de course {word}"
    page.goto("/deposer/")
    page.locator('input[name="photos"]').set_input_files(photo)
    page.get_by_label("Titre").fill(title)
    page.get_by_label("Catégorie").select_option(label="Smartphones")
    page.get_by_label("Ville", exact=True).select_option(label="Bamako")
    page.get_by_label("Prix").fill("45000")
    page.get_by_label("Description").fill("Bon état, pneus neufs, à voir à Hamdallaye.")
    page.get_by_role("button", name="Publier l'annonce").click()
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    return Listing(title, word, page.url)


@pytest.fixture(scope="session")
def listing(seller, photo) -> Listing:
    return post_listing(seller.page, photo)
