"""Recherche et filtres (ticket #9)."""

import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.listings import services
from apps.listings.models import ListingStatus

from .factories import CategoryFactory, CityFactory, ListingFactory

pytestmark = pytest.mark.django_db

URL = reverse("listings:search")
HTMX = {"HX-Request": "true"}


def _titles(client, **params):
    html = client.get(URL, params).content.decode()
    return re.findall(r'<p class="sg-card__title">([^<]+)</p>', html)


def _pub(title, **kwargs):
    kwargs.setdefault("published_at", timezone.now())
    return ListingFactory(status=ListingStatus.PUBLISHED, title=title, **kwargs)


@pytest.fixture
def catalogue():
    """Petit catalogue : deux villes, une catégorie principale avec deux sous-catégories."""
    bamako, segou = CityFactory(name="Bamako"), CityFactory(name="Ségou")
    vehicles = CategoryFactory(name="Véhicules et vélos")
    bikes = CategoryFactory(name="Vélos", parent=vehicles)
    motos = CategoryFactory(name="Motos", parent=vehicles)
    phones = CategoryFactory(name="Téléphones")
    return {
        "bamako": bamako,
        "segou": segou,
        "vehicles": vehicles,
        "velo": _pub("Vélo de course Peugeot", category=bikes, city=bamako, price=45000),
        "moto": _pub("Moto Jakarta 125", category=motos, city=segou, price=350000),
        "samsung": _pub(
            "Samsung Galaxy A15",
            category=phones,
            city=bamako,
            price=85000,
            neighborhood="Sabalibougou",
        ),  # fmt: skip
        "debattre": _pub("Vélo enfant", category=bikes, city=segou, price=None),
    }


# --- Mots-clés ---------------------------------------------------------------------------


def test_velo_trouve_velo_de_course(client, catalogue):
    # Même pertinence : l'ordre entre les deux n'est pas garanti.
    assert set(_titles(client, q="velo")) == {"Vélo de course Peugeot", "Vélo enfant"}


def test_majuscules_accents_et_pluriels_ne_comptent_pas(client, catalogue):
    assert "Vélo de course Peugeot" in _titles(client, q="VÉLOS")
    assert "Moto Jakarta 125" in _titles(client, q="motos")


def test_le_quartier_fait_partie_de_la_recherche(client, catalogue):
    assert _titles(client, q="sabalibougou") == ["Samsung Galaxy A15"]


def test_un_debut_de_mot_suffit(client, catalogue):
    assert _titles(client, q="sams") == ["Samsung Galaxy A15"]


def test_tous_les_mots_doivent_etre_presents(client, catalogue):
    assert _titles(client, q="velo peugeot") == ["Vélo de course Peugeot"]
    assert _titles(client, q="velo samsung") == []


def test_le_titre_passe_avant_la_description(client, catalogue):
    _pub("Casque de moto", description="Idéal pour le vélo aussi", published_at=timezone.now())
    old = _pub("Vélo de ville", published_at=timezone.now() - timedelta(days=5))

    titles = _titles(client, q="velo")

    assert titles.index(old.title) < titles.index("Casque de moto")


def test_la_syntaxe_de_recherche_saisie_est_neutralisee(client, catalogue):
    for q in ["velo & !moto", "velo:* | moto", "') OR 1=1 --", "<script>", "***", "&&&"]:
        response = client.get(URL, {"q": q})
        assert response.status_code == 200
    html = client.get(URL, {"q": "<script>alert(1)</script>"}).content.decode()
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html  # le texte saisi revient échappé


# --- Filtres -----------------------------------------------------------------------------


def test_une_categorie_principale_inclut_ses_sous_categories(client, catalogue):
    titles = _titles(client, category=catalogue["vehicles"].slug)

    assert set(titles) == {"Vélo de course Peugeot", "Moto Jakarta 125", "Vélo enfant"}


def test_les_filtres_se_combinent(client, catalogue):
    titles = _titles(
        client, q="velo", category=catalogue["vehicles"].slug, city=catalogue["bamako"].slug,
        price_min=10000, price_max=100000,
    )  # fmt: skip

    assert titles == ["Vélo de course Peugeot"]


def test_un_filtre_de_prix_ecarte_les_annonces_a_debattre(client, catalogue):
    assert "Vélo enfant" not in _titles(client, price_max=1_000_000)


def test_prix_min_et_max_inverses_sont_remis_dans_l_ordre(client, catalogue):
    assert _titles(client, price_min=100000, price_max=10000) == [
        "Samsung Galaxy A15",
        "Vélo de course Peugeot",
    ]


def test_une_valeur_invalide_est_ignoree_et_pas_reaffichee(client, catalogue):
    response = client.get(URL, {"q": "velo", "price_min": "abc<b>", "city": "nulle-part"})

    html = response.content.decode()
    assert response.status_code == 200
    assert set(re.findall(r'<p class="sg-card__title">([^<]+)</p>', html)) == {
        "Vélo de course Peugeot",
        "Vélo enfant",
    }
    assert "abc" not in html
    assert "nulle-part" not in html


def test_les_annonces_vendues_retirees_et_brouillons_sont_absentes(client, catalogue):
    services.mark_sold(catalogue["moto"])
    services.remove(catalogue["velo"])
    ListingFactory(title="Vélo brouillon")

    assert _titles(client, q="velo") == ["Vélo enfant"]
    assert "Moto Jakarta 125" not in _titles(client)


# --- URL partageable, pagination et htmx -------------------------------------------------


def test_l_url_est_partageable_et_le_formulaire_garde_les_parametres(client, catalogue):
    params = {"q": "velo", "category": catalogue["vehicles"].slug, "price_max": "100000"}

    html = client.get(URL, params).content.decode()

    assert 'name="q" value="velo"' in html
    assert f'name="category" value="{catalogue["vehicles"].slug}"' in html  # champ caché
    assert f'value="{catalogue["vehicles"].slug}" selected' in html  # liste des filtres
    assert 'value="100000"' in html
    assert "« velo »" in html  # chip de filtre actif


def test_retirer_un_filtre_garde_les_autres(client, catalogue):
    html = client.get(URL, {"q": "velo", "city": catalogue["segou"].slug}).content.decode()

    links = re.findall(r'<a class="sg-chip sg-chip--on" href="([^"]+)"', html)
    without_city = next(link for link in links if "city" not in link)
    assert parse_qs(urlparse(without_city.replace("&amp;", "&")).query) == {"q": ["velo"]}


def test_voir_plus_garde_les_filtres_et_renvoie_le_partial(client, catalogue):
    city = catalogue["bamako"]
    for i in range(22):
        _pub(f"Vélo {i}", city=city, published_at=timezone.now() - timedelta(minutes=i))

    page1 = client.get(URL, {"q": "velo", "city": city.slug}).content.decode()
    next_url = re.search(r'hx-get="([^"]+)"', page1).group(1).replace("&amp;", "&")
    page2 = client.get(next_url, headers=HTMX)

    assert parse_qs(urlparse(next_url).query) == {"q": ["velo"], "city": [city.slug], "page": ["2"]}
    html = page2.content.decode()
    assert "<html" not in html
    assert len(re.findall(r'class="sg-card__title"', html)) == 3  # 23 vélos à Bamako - 20


def test_aucun_resultat(client, catalogue):
    html = client.get(URL, {"q": "frigo"}).content.decode()

    assert "Aucune annonce ne correspond" in html
    assert "0 annonce" in html


def test_le_lien_recherche_et_les_tuiles_menent_a_la_recherche(client):
    html = client.get(reverse("core:home")).content.decode()

    assert f'class="sg-bottomnav__item" href="{URL}"' in html
    assert 'action="/recherche/"' in html  # barre de recherche de l'accueil
