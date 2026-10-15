from functools import wraps

from allauth.account.decorators import verified_email_required as allauth_verified_email
from django.conf import settings
from django.contrib.auth.decorators import login_required


def verified_email_required(view):
    """Email confirmé obligatoire pour déposer et pour écrire à un vendeur (ticket #3, ajout du
    2026-10-15) : contre les faux comptes et le spam. Sinon, allauth renvoie le lien de
    confirmation (avec un délai entre deux envois) et affiche
    templates/account/verified_email_required.html. Réglage VERIFIED_EMAIL_REQUIRED : désactivé
    pour les parcours de bout en bout, qui ne lisent pas les emails."""
    checked = allauth_verified_email(view)
    logged_in = login_required(view)

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        guarded = checked if settings.VERIFIED_EMAIL_REQUIRED else logged_in
        return guarded(request, *args, **kwargs)

    return wrapper
