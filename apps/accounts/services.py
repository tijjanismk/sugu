from allauth.account.models import EmailAddress
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.favorites.models import Favorite
from apps.listings import services as listing_services
from apps.listings.models import ListingStatus

from .models import User

DELETED_NAME = "Compte supprimé"


def sign_out_everywhere(user: User) -> None:
    """Invalide toutes les sessions ouvertes de l'utilisateur (voir User._get_session_auth_hash).
    La vue garde ensuite la session courante avec update_session_auth_hash."""
    User.objects.filter(pk=user.pk).update(session_version=F("session_version") + 1)
    user.refresh_from_db(fields=["session_version"])


@transaction.atomic
def delete_account(user: User) -> None:
    """Suppression demandée par le titulaire (ticket #13) : anonymisation, pas destruction.

    - ses annonces sont retirées du site (statut `removed`) mais gardées ;
    - ses messages restent dans les conversations, signés « Compte supprimé » : l'autre
      personne garde son historique, utile en cas de litige ;
    - email, nom, téléphone et ville sont effacés ; l'adresse email est libérée ;
    - le compte ne peut plus se connecter et toutes ses sessions tombent ;
    - ses favoris, sans intérêt pour personne d'autre, sont supprimés.
    """
    for listing in user.listings.exclude(status=ListingStatus.REMOVED):
        listing_services.remove(listing)
    Favorite.objects.filter(user=user).delete()
    EmailAddress.objects.filter(user=user).delete()

    user.email = f"supprime-{user.pk}@sugu.invalid"
    user.display_name = DELETED_NAME
    user.phone = ""
    user.phone_verified = False
    user.city = None
    user.is_active = False
    user.set_unusable_password()
    user.session_version = F("session_version") + 1
    user.deleted_at = timezone.now()
    user.save()
    user.refresh_from_db()
