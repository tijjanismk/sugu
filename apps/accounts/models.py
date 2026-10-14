from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.utils.crypto import salted_hmac


class UserManager(DjangoUserManager):
    """Gestionnaire sans nom d'utilisateur : l'email est l'identifiant de connexion."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff et is_superuser.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Utilisateur Sugu, identifié par son email."""

    username = None
    first_name = None
    last_name = None
    email = models.EmailField("adresse email", unique=True)
    display_name = models.CharField("nom affiché", max_length=50)
    phone = models.CharField("téléphone", max_length=20, blank=True)
    phone_verified = models.BooleanField("téléphone vérifié", default=False)
    city = models.ForeignKey(
        "listings.City",
        verbose_name="ville",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Email au premier message non lu d'une conversation (ticket #12), désactivable au profil.
    notify_messages = models.BooleanField(
        "me prévenir par email des nouveaux messages", default=True
    )
    # Augmenter ce nombre déconnecte toutes les sessions sans toucher au mot de passe
    # (« Déconnecter mes autres appareils », ticket #13).
    session_version = models.PositiveIntegerField("version de session", default=0)
    # Compte supprimé par son titulaire : anonymisé, pas détruit (docs/security.md).
    deleted_at = models.DateTimeField("supprimé le", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.display_name or self.email

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def _get_session_auth_hash(self, secret=None):
        """Comme Django (HMAC du mot de passe), plus `session_version`. Tant qu'elle vaut 0, le
        résultat est exactement celui de Django : les sessions déjà ouvertes restent valides."""
        value = self.password
        if self.session_version:
            value = f"{value}:{self.session_version}"
        return salted_hmac(
            "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash",
            value,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()
