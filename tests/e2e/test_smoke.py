"""Parcours Playwright de bout en bout, lancés sur main (le ticket #16 ajoute les parcours)."""

import pytest

pytestmark = pytest.mark.e2e


def test_la_page_d_accueil_s_ouvre(page, base_url):
    page.goto(base_url)
    assert "Sugu" in page.title()
