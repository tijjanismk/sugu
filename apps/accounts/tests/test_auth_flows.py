"""Parcours de compte côté serveur : inscription, connexion, déconnexion, mot de passe
oublié, et limitation de débit (docs/security.md)."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from .factories import MOT_DE_PASSE, UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


def _est_connecte(client):
    return "_auth_user_id" in client.session


def _inscription(client, email, **extra):
    data = {
        "display_name": "Awa Traoré",
        "email": email,
        "phone": "",
        "password1": MOT_DE_PASSE,
        **extra,
    }
    return client.post(reverse("account_signup"), data)


def _connexion(client, email, password=MOT_DE_PASSE, **extra):
    return client.post(reverse("account_login"), {"login": email, "password": password}, **extra)


# --- Inscription -------------------------------------------------------------------------


def test_les_pages_de_compte_sont_en_francais(client):
    assert reverse("account_signup") == "/comptes/inscription/"
    assert reverse("account_login") == "/comptes/connexion/"
    response = client.get(reverse("account_signup"))
    assert response.status_code == 200
    assert "Nom affiché" in response.content.decode()


def test_inscription_cree_le_compte_et_connecte(client):
    response = _inscription(client, "awa@example.ml", phone="+223 70 00 00 00")

    assert response.status_code == 302
    assert response.url == "/"
    user = User.objects.get(email="awa@example.ml")
    assert user.display_name == "Awa Traoré"
    assert user.phone == "+22370000000"  # normalisé (ticket #13), affiché groupé
    assert user.check_password(MOT_DE_PASSE)
    assert _est_connecte(client)
    # Vérification « optionnelle » : un email de confirmation part quand même.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["awa@example.ml"]


def test_inscription_sans_nom_affiche_refusee(client):
    response = _inscription(client, "awa@example.ml", display_name="")

    assert response.status_code == 200
    assert not User.objects.filter(email="awa@example.ml").exists()
    assert response.context["form"].errors["display_name"]


def test_inscription_avec_un_email_deja_pris_refusee(client):
    UserFactory(email="awa@example.ml")

    response = _inscription(client, "awa@example.ml")

    assert response.status_code == 200
    assert User.objects.filter(email="awa@example.ml").count() == 1
    assert not _est_connecte(client)


def test_inscription_avec_un_mot_de_passe_trop_courant_refusee(client):
    response = _inscription(client, "awa@example.ml", password1="password")

    assert response.status_code == 200
    assert not User.objects.filter(email="awa@example.ml").exists()


# --- Connexion et déconnexion ------------------------------------------------------------


def test_connexion_avec_le_bon_mot_de_passe(client):
    UserFactory(email="awa@example.ml")

    response = _connexion(client, "awa@example.ml")

    assert response.status_code == 302
    assert response.url == "/"
    assert _est_connecte(client)


def test_connexion_avec_un_mauvais_mot_de_passe_refusee(client):
    UserFactory(email="awa@example.ml")

    response = _connexion(client, "awa@example.ml", password="mauvais")

    assert response.status_code == 200
    assert not _est_connecte(client)
    assert response.context["form"].non_field_errors()


def test_connexion_insensible_a_la_casse_de_l_email(client):
    UserFactory(email="awa@example.ml")

    _connexion(client, "AWA@Example.ML")

    assert _est_connecte(client)


def test_deconnexion(client):
    user = UserFactory()
    client.force_login(user)

    response = client.post(reverse("account_logout"))

    assert response.status_code == 302
    assert not _est_connecte(client)


def test_la_deconnexion_par_get_ne_deconnecte_pas(client):
    # Un lien piégé (<img src=".../deconnexion/">) ne doit pas déconnecter.
    user = UserFactory()
    client.force_login(user)

    client.get(reverse("account_logout"))

    assert _est_connecte(client)


def test_changer_de_mot_de_passe_exige_d_etre_connecte(client):
    response = client.get(reverse("account_change_password"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


# --- Mot de passe oublié -----------------------------------------------------------------


def test_mot_de_passe_oublie_jusqu_au_nouveau_mot_de_passe(client):
    user = UserFactory(email="awa@example.ml")

    response = client.post(reverse("account_reset_password"), {"email": "awa@example.ml"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1

    lien = re.search(r"https?://[^/\s]+(/comptes/mot-de-passe/oublie/\S+/)", mail.outbox[0].body)
    assert lien, mail.outbox[0].body
    # allauth retire la clé de l'URL (gardée en session) puis affiche le formulaire.
    response = client.get(lien.group(1), follow=True)
    assert response.status_code == 200
    assert "password1" in response.content.decode()
    form_url = response.redirect_chain[-1][0] if response.redirect_chain else lien.group(1)

    nouveau = "Karite-2027-nouveau"
    response = client.post(form_url, {"password1": nouveau, "password2": nouveau})
    assert response.status_code == 302

    user.refresh_from_db()
    assert user.check_password(nouveau)
    client.logout()
    _connexion(client, "awa@example.ml", password=nouveau)
    assert _est_connecte(client)


def test_mot_de_passe_oublie_ne_revele_pas_si_le_compte_existe(client):
    response = client.post(reverse("account_reset_password"), {"email": "inconnu@example.ml"})

    # Même réponse qu'avec un compte existant, et aucun lien de réinitialisation envoyé.
    assert response.status_code == 302
    assert response.url == reverse("account_reset_password_done")
    assert not any("/mot-de-passe/oublie/" in m.body for m in mail.outbox)


def test_un_lien_de_reinitialisation_invalide_est_refuse(client):
    user = UserFactory()

    response = client.get(
        reverse("account_reset_password_from_key", kwargs={"uidb36": "1", "key": "faux-jeton"}),
        follow=True,
    )

    assert response.status_code == 200
    assert "password1" not in response.content.decode()
    user.refresh_from_db()
    assert user.check_password(MOT_DE_PASSE)


# --- Limitation de débit -----------------------------------------------------------------


def test_connexion_bloquee_apres_5_echecs_sur_le_meme_compte(client):
    UserFactory(email="awa@example.ml")
    for i in range(5):
        # Chaque échec vient d'une IP différente : seul le compteur par compte joue.
        _connexion(client, "awa@example.ml", password="mauvais", REMOTE_ADDR=f"10.0.0.{i + 1}")

    # Même avec le bon mot de passe, la 6ᵉ tentative est refusée.
    response = _connexion(client, "awa@example.ml", REMOTE_ADDR="10.0.0.99")

    assert response.status_code == 200
    assert not _est_connecte(client)
    assert response.context["form"].non_field_errors()


def test_connexion_bloquee_apres_5_echecs_depuis_la_meme_ip(client):
    UserFactory(email="cible@example.ml")
    for i in range(5):
        _connexion(client, f"essai{i}@example.ml", password="mauvais")

    response = _connexion(client, "cible@example.ml")

    assert not _est_connecte(client)
    assert response.context["form"].non_field_errors()


def test_les_echecs_d_une_autre_ip_ne_bloquent_pas(client):
    UserFactory(email="awa@example.ml")
    for i in range(5):
        _connexion(client, f"essai{i}@example.ml", password="mauvais", REMOTE_ADDR="10.0.0.9")

    _connexion(client, "awa@example.ml")

    assert _est_connecte(client)


def test_inscription_limitee_a_3_par_ip_et_par_heure(client):
    for i in range(3):
        response = _inscription(client, f"compte{i}@example.ml")
        assert response.status_code == 302
        client.logout()

    response = _inscription(client, "compte4@example.ml")

    assert response.status_code == 429
    assert not User.objects.filter(email="compte4@example.ml").exists()
