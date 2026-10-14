"""URL des comptes en français ; les noms restent ceux d'allauth, qui s'en sert pour rediriger.

Seuls les parcours activés dans les réglages sont exposés : pas de connexion par code, pas
de téléphone, confirmation d'email et réinitialisation par lien.
"""

from allauth.account import views
from django.urls import path, re_path

from . import views as account_views

urlpatterns = [
    # Profil (ticket #13). Noms sans espace de noms, comme ceux d'allauth qui partagent ce module.
    path("profil/", account_views.profile, name="account_profile"),
    path(
        "profil/deconnecter-partout/",
        account_views.sign_out_others,
        name="account_sign_out_others",
    ),
    path("supprimer/", account_views.delete_account, name="account_delete"),
    path("connexion/", views.login, name="account_login"),
    path("deconnexion/", views.logout, name="account_logout"),
    path("inscription/", views.signup, name="account_signup"),
    path("inactif/", views.account_inactive, name="account_inactive"),
    path("reauthentification/", views.reauthenticate, name="account_reauthenticate"),
    path("email/", views.email, name="account_email"),
    path(
        "email/confirmation/",
        views.email_verification_sent,
        name="account_email_verification_sent",
    ),
    re_path(
        r"^email/confirmation/(?P<key>[-:\w]+)/$",
        views.confirm_email,
        name="account_confirm_email",
    ),
    path("mot-de-passe/modifier/", views.password_change, name="account_change_password"),
    path("mot-de-passe/definir/", views.password_set, name="account_set_password"),
    path("mot-de-passe/oublie/", views.password_reset, name="account_reset_password"),
    path(
        "mot-de-passe/oublie/envoye/",
        views.password_reset_done,
        name="account_reset_password_done",
    ),
    re_path(
        r"^mot-de-passe/oublie/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        views.password_reset_from_key,
        name="account_reset_password_from_key",
    ),
    path(
        "mot-de-passe/oublie/termine/",
        views.password_reset_from_key_done,
        name="account_reset_password_from_key_done",
    ),
]
