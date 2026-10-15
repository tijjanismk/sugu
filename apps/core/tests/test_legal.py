"""Pages légales et « À propos » (ticket #17) : en ligne, liées dans le pied de page, et
signalées par `check --deploy` tant qu'elles restent à compléter."""

from types import SimpleNamespace

import pytest
from django.urls import reverse

from apps.core import checks
from apps.listings.tests.factories import ListingFactory

pytestmark = pytest.mark.django_db

PAGES = [
    ("core:about", "À propos de Sugu"),
    ("core:legal_notice", "Mentions légales"),
    ("core:privacy", "Politique de confidentialité"),
]


@pytest.mark.parametrize(("name", "heading"), PAGES)
def test_pages_en_ligne_pour_tous(client, name, heading):
    response = client.get(reverse(name))

    assert response.status_code == 200
    assert f"<h1>{heading}</h1>" in response.content.decode()


def test_le_pied_de_page_mene_aux_pages_legales(client):
    html = client.get(reverse("core:home")).content.decode()

    assert '<footer class="sg-footer">' in html
    for name, _ in PAGES:
        assert f'href="{reverse(name)}"' in html


def test_pas_de_pied_de_page_dans_les_parcours(client, django_user_model):
    user = django_user_model.objects.create_user(email="a@exemple.ml", password="x" * 12)
    client.force_login(user)

    html = client.get(reverse("listings:create")).content.decode()

    assert "sg-footer" not in html


def test_linscription_mene_a_la_politique_de_confidentialite(client):
    html = client.get(reverse("account_signup")).content.decode()

    assert f'href="{reverse("core:privacy")}"' in html


def test_la_politique_decrit_le_telephone_visible_des_membres(client):
    """Ce que dit la politique doit rester vrai (templates/listings/detail.html)."""
    html = client.get(reverse("core:privacy")).content.decode()

    assert "n'est visible que par les membres connectés" in html
    listing = ListingFactory(published=True, user__phone="+22376123456")
    page = client.get(listing.get_absolute_url()).content.decode()
    assert "76 12 34 56" not in page and "tel:" not in page


def test_check_deploy_trouve_les_pages_legales():
    checks.check_legal_pages(None)  # chaque gabarit existe (sinon TemplateDoesNotExist)


def test_check_deploy_signale_les_pages_a_completer(monkeypatch):
    sources = {"legal/privacy.html": "Hébergé par [À COMPLÉTER : hébergeur]."}
    monkeypatch.setattr(
        checks,
        "get_template",
        lambda name: SimpleNamespace(template=SimpleNamespace(source=sources.get(name, "Fini."))),
    )

    messages = checks.check_legal_pages(None)

    assert [message.id for message in messages] == ["sugu.W003"]
    assert "legal/privacy.html" in messages[0].msg
    sources.clear()
    assert checks.check_legal_pages(None) == []
