import factory

from apps.accounts.models import User

MOT_DE_PASSE = "Baobab-2026-solide"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"vendeur{n}@example.ml")
    display_name = factory.Sequence(lambda n: f"Vendeur {n}")
    password = factory.PostGenerationMethodCall("set_password", MOT_DE_PASSE)

    @factory.post_generation
    def _enregistre(obj, create, extracted, **kwargs):
        if create:
            obj.save()
