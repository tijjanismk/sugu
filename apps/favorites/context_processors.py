from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

from .services import favorite_ids


def favorites(request: HttpRequest) -> dict:
    """`favorite_ids` pour les cœurs des cartes. Paresseux : la requête n'est faite que si la
    page affiche un cœur, et une seule fois."""
    user = request.user
    if not user.is_authenticated:
        return {"favorite_ids": frozenset()}
    return {"favorite_ids": SimpleLazyObject(lambda: favorite_ids(user))}
