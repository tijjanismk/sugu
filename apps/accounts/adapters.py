from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import User


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Connexion avec Google (ticket #3, ADR 0002)."""

    def populate_user(self, request, sociallogin, data) -> User:
        """Nom affiché obligatoire chez Sugu : le nom du compte Google, sinon le début de
        l'adresse email. Modifiable ensuite au profil."""
        user = super().populate_user(request, sociallogin, data)
        names = [data.get("first_name"), data.get("last_name")]
        name = " ".join(part for part in names if part) or (user.email or "").split("@")[0]
        user.display_name = " ".join(name.split())[
            : User._meta.get_field("display_name").max_length
        ]
        return user
