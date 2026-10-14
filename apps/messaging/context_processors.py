from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

from .services import unread_count

MAX_SHOWN = 99


def _label(user) -> str:
    count = unread_count(user)
    if not count:
        return ""
    return f"{MAX_SHOWN}+" if count > MAX_SHOWN else str(count)


def unread_messages(request: HttpRequest) -> dict:
    """`unread_messages` : pastille de la barre de navigation (« 3 », « 99+ », ou vide).
    Paresseux : compté seulement si la page affiche la barre."""
    user = request.user
    if not user.is_authenticated:
        return {"unread_messages": ""}
    return {"unread_messages": SimpleLazyObject(lambda: _label(user))}
