"""Référencement (demande du 2026-10-15) : robots.txt et plan du site (#15), pages catégorie et
ville (#9), description, aperçu de partage et données structurées de la page annonce (#8)."""

import json
import re

import pytest
from django.urls import reverse

from apps.core.templatetags.sugu_format import fcfa
from apps.listings import services
from apps.listings.models import ListingStatus, Photo

from .factories import CategoryFactory, CityFactory, ListingFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogue():
    phones = CategoryFactory(name="Téléphones")
    smartphones = CategoryFactory(name="Smartphones", parent=phones)
    furniture = CategoryFactory(name="Maison")
    bamako, kati, kayes = (CityFactory(name=n) for n in ("Bamako", "Kati", "Kayes"))
    samsung = ListingFactory(
        published=True, title="Samsung Galaxy A15", category=smartphones, city=bamako, price=85000
    )
    tecno = ListingFactory(published=True, title="Tecno Spark 20", category=smartphones, city=kati)
    removed = ListingFactory(status=ListingStatus.REMOVED, category=smartphones, city=kayes)
    return {
        "phones": phones, "smartphones": smartphones, "furniture": furniture,
        "bamako": bamako, "kati": kati, "kayes": kayes,
        "samsung": samsung, "tecno": tecno, "removed": removed,
    }  # fmt: skip


def _meta(html, name):
    return re.findall(rf'<meta (?:name|property)="{re.escape(name)}" content="([^"]*)"', html)


# --- robots.txt et plan du site (#15) -------------------------------------------------------


def test_robots_exclut_les_pages_privees_et_annonce_le_plan(client, settings):
    settings.ADMIN_URL = "gestion-x7Kq2mPz9LwR4vTn/"

    response = client.get("/robots.txt")

    body = response.content.decode()
    assert response["Content-Type"].startswith("text/plain")
    for name in ("listings:mine", "listings:create", "favorites:list", "messaging:inbox"):
        assert f"Disallow: {reverse(name)}" in body
    assert "Disallow: /comptes/" in body
    assert "Sitemap: http://testserver/sitemap.xml" in body
    assert "gestion-" not in body  # l'adresse de l'admin reste secrète
    assert "Disallow: /recherche/" not in body  # explorable, mais « noindex »


def test_plan_du_site(client, catalogue):
    body = client.get("/sitemap.xml").content.decode()

    for url in (
        "/",
        catalogue["samsung"].get_absolute_url(),
        catalogue["tecno"].get_absolute_url(),
        "/categorie/telephones/",
        "/categorie/smartphones/",
        "/categorie/telephones/bamako/",
        "/categorie/smartphones/kati/",
        "/ville/bamako/",
        "/ville/kati/",
    ):
        assert f"<loc>http://testserver{url}</loc>" in body, url
    assert catalogue["removed"].get_absolute_url() not in body
    assert "/categorie/maison/" not in body  # sans annonce : pas dans le plan
    assert "/ville/kayes/" not in body  # seulement une annonce retirée


def test_les_annonces_vendues_sortent_du_plan(client, catalogue):
    services.mark_sold(catalogue["samsung"])

    body = client.get("/sitemap.xml").content.decode()

    assert catalogue["samsung"].get_absolute_url() not in body


# --- Pages catégorie et ville (#9) -----------------------------------------------------------


def test_page_categorie_principale_avec_ses_sous_categories(client, catalogue):
    response = client.get("/categorie/telephones/")

    html = response.content.decode()
    assert "<title>Téléphones : petites annonces au Mali · Sugu</title>" in html
    assert '<h1 id="browse-title"' in html and ">Téléphones</h1>" in html
    assert "Samsung Galaxy A15" in html and "Tecno Spark 20" in html
    assert "2 annonces en ligne" in html
    assert _meta(html, "description")[0].startswith("2 annonces « Téléphones » au Mali")
    assert _meta(html, "robots") == []
    assert '<link rel="canonical" href="http://testserver/categorie/telephones/">' in html
    assert 'href="/categorie/smartphones/"' in html  # sous-catégorie avec annonces
    assert 'href="/categorie/telephones/bamako/"' in html  # autres villes
    assert 'href="/categorie/telephones/kayes/"' not in html  # rien en ligne à Kayes


def test_page_categorie_et_ville(client, catalogue):
    html = client.get("/categorie/telephones/bamako/").content.decode()

    assert "<title>Téléphones à Bamako : petites annonces · Sugu</title>" in html
    assert "Samsung Galaxy A15" in html
    assert "Tecno Spark 20" not in html
    assert 'href="/categorie/telephones/kati/"' in html


def test_page_ville(client, catalogue):
    html = client.get("/ville/kati/").content.decode()

    assert "<title>Petites annonces à Kati · Sugu</title>" in html
    assert "Tecno Spark 20" in html and "Samsung" not in html
    assert 'href="/categorie/telephones/kati/"' in html  # catégories de la ville


def test_page_sans_annonce_non_indexee(client, catalogue):
    html = client.get("/categorie/maison/").content.decode()

    assert _meta(html, "robots") == ["noindex, follow"]
    assert "Pas encore d&#x27;annonce ici" in html or "Pas encore d'annonce ici" in html


@pytest.mark.parametrize(
    "url", ["/categorie/inconnue/", "/ville/nulle-part/", "/categorie/telephones/x/"]
)
def test_adresse_inconnue_404(client, catalogue, url):
    assert client.get(url).status_code == 404


def test_voir_plus_en_htmx(client, catalogue):
    response = client.get("/categorie/telephones/", headers={"HX-Request": "true"})

    html = response.content.decode()
    assert "<html" not in html
    assert "Samsung Galaxy A15" in html


def test_les_tuiles_de_laccueil_menent_aux_pages_categorie(client, catalogue):
    html = client.get(reverse("core:home")).content.decode()

    assert 'href="/categorie/telephones/"' in html
    assert "?category=" not in html


def test_recherche_libre_non_indexee(client, catalogue):
    html = client.get(reverse("listings:search"), {"q": "samsung"}).content.decode()

    assert _meta(html, "robots") == ["noindex, follow"]


# --- Balises communes ------------------------------------------------------------------------


def test_une_seule_description_et_adresse_canonique(client, catalogue):
    for url in ("/", catalogue["samsung"].get_absolute_url(), "/categorie/telephones/"):
        html = client.get(url).content.decode()
        assert len(_meta(html, "description")) == 1, url
        assert html.count('<link rel="canonical"') == 1, url


@pytest.mark.parametrize(("query", "canonical"), [("?page=2", "/?page=2"), ("?page=abc&x=1", "/")])
def test_adresse_canonique_garde_seulement_la_page(client, catalogue, query, canonical):
    html = client.get("/" + query).content.decode()

    assert f'<link rel="canonical" href="http://testserver{canonical}">' in html


def test_apercu_par_defaut(client):
    html = client.get(reverse("core:home")).content.decode()

    assert _meta(html, "og:site_name") == ["Sugu"]
    assert _meta(html, "og:image") == ["http://testserver/static/img/icons/icon-512.png"]
    assert _meta(html, "og:url") == ["http://testserver/"]


def test_balise_de_verification_google(client, settings):
    settings.GOOGLE_SITE_VERIFICATION = "jeton-de-verification"

    html = client.get(reverse("core:home")).content.decode()

    assert _meta(html, "google-site-verification") == ["jeton-de-verification"]


# --- Page annonce (#8) -----------------------------------------------------------------------


def _structured(html):
    match = re.search(
        r'<script type="application/ld\+json" nonce="[^"]+">(.*?)</script>', html, re.S
    )
    assert match, "pas de données structurées"
    return json.loads(match.group(1))


def test_page_annonce_description_apercu_et_produit(client, catalogue):
    listing = catalogue["samsung"]
    Photo.objects.create(
        listing=listing, order=0, width=1200, height=900,
        large=f"listings/{listing.pk}/p-1200.webp", thumb=f"listings/{listing.pk}/p-400.webp",
    )  # fmt: skip

    html = client.get(listing.get_absolute_url()).content.decode()

    price = fcfa(85000)  # espaces insécables de la charte
    assert _meta(html, "description")[0].startswith(f"{price} · Bamako — ")
    assert _meta(html, "og:title") == [f"Samsung Galaxy A15 · {price}"]
    assert _meta(html, "og:image") == [f"http://testserver/media/listings/{listing.pk}/p-1200.webp"]
    assert _meta(html, "og:image:width") == ["1200"]
    product = _structured(html)
    assert product["@type"] == "Product"
    assert product["name"] == "Samsung Galaxy A15"
    assert product["offers"]["price"] == "85000"
    assert product["offers"]["priceCurrency"] == "XOF"
    assert product["offers"]["availability"] == "https://schema.org/InStock"
    assert _meta(html, "robots") == []


def test_annonce_vendue_non_indexee(client, catalogue):
    services.mark_sold(catalogue["samsung"])

    html = client.get(catalogue["samsung"].get_absolute_url()).content.decode()

    assert _meta(html, "robots") == ["noindex, follow"]
    assert _structured(html)["offers"]["availability"] == "https://schema.org/SoldOut"


def test_prix_a_debattre_sans_offre_chiffree(client, catalogue):
    listing = ListingFactory(published=True, price=None)

    product = _structured(client.get(listing.get_absolute_url()).content.decode())

    assert "offers" not in product


def test_un_titre_ne_peut_pas_fermer_la_balise(client):
    listing = ListingFactory(published=True, title="Vélo </script><script>alert(1)")

    html = client.get(listing.get_absolute_url()).content.decode()

    assert "</script><script>alert(1)" not in html
    assert _structured(html)["name"] == "Vélo </script><script>alert(1)"


def test_liens_vers_les_pages_categorie_et_ville(client, catalogue):
    html = client.get(catalogue["samsung"].get_absolute_url()).content.decode()

    for url in ("/categorie/smartphones/bamako/", "/categorie/smartphones/", "/ville/bamako/"):
        assert f'href="{url}"' in html
