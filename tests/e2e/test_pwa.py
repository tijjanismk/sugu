"""Application installable (ticket #14) : le service worker s'installe et, sans réseau, une page
du site affiche la page hors-ligne au lieu de l'erreur du navigateur."""

import pytest

pytestmark = pytest.mark.e2e


def test_page_hors_ligne_sans_reseau(page, context, base_url):
    page.goto(base_url)
    # Le service worker prend la main sur la page dès son activation (clients.claim). Pas de
    # wait_for_function : il évalue une chaîne dans la page, ce que la CSP interdit (ticket #15).
    for _ in range(50):
        if page.evaluate("() => Boolean(navigator.serviceWorker?.controller)"):
            break
        page.wait_for_timeout(200)
    else:
        pytest.fail("Le service worker n'a pas pris la main sur la page en 10 s.")

    context.set_offline(True)
    try:
        page.goto(f"{base_url}/recherche/?q=velo")
        assert page.locator("h1").inner_text() == "Pas de connexion"
        assert page.url.endswith("/recherche/?q=velo")  # « Réessayer » recharge cette adresse
    finally:
        context.set_offline(False)


def test_manifeste_declare(page, base_url):
    page.goto(base_url)
    href = page.locator('link[rel="manifest"]').get_attribute("href")

    manifest = page.request.get(f"{base_url}{href}").json()

    assert manifest["display"] == "standalone"
    assert {icon["sizes"] for icon in manifest["icons"]} >= {"192x192", "512x512"}
