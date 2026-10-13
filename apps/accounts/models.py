from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Utilisateur Sugu.

    Créé dès la première migration pour ne jamais avoir à changer AUTH_USER_MODEL plus tard.
    Le ticket #3 ajoute display_name, phone, phone_verified et city, et la connexion par email.
    """

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
