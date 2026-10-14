"""Formats d'affichage de la charte (design/README.md, « Contenu ») : prix et dates."""

from datetime import datetime

from django import template
from django.utils import timezone

register = template.Library()

# Espace fine insécable (séparateur de milliers) et espace insécable (avant l'unité).
THIN_NBSP = " "
NBSP = "\xa0"
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
          "nov.", "déc."]  # fmt: skip


@register.filter
def thousands(value) -> str:
    """45000 → « 45 000 » ; pas de décimales."""
    if value is None or value == "":
        return ""
    return f"{int(value):,}".replace(",", THIN_NBSP)


@register.filter
def fcfa(value) -> str:
    """45000 → « 45 000 FCFA » ; None → « À débattre »."""
    if value is None or value == "":
        return "À débattre"
    return f"{thousands(value)}{NBSP}FCFA"


@register.filter
def relative_date(value: datetime | None, now: datetime | None = None) -> str:
    """Date relative jusqu'à sept jours (« il y a 2 h », « hier », « il y a 3 j »), puis la date
    courte (« 12 oct. », avec l'année si ce n'est pas l'année en cours)."""
    if value is None:
        return ""
    now = timezone.localtime(now or timezone.now())
    value = timezone.localtime(value)
    seconds = (now - value).total_seconds()
    days = (now.date() - value.date()).days
    if seconds < 60:
        return "à l'instant"
    if seconds < 3600:
        return f"il y a {int(seconds // 60)} min"
    if days == 0:
        return f"il y a {int(seconds // 3600)} h"
    if days == 1:
        return "hier"
    if days < 7:
        return f"il y a {days} j"
    label = f"{value.day} {MONTHS[value.month - 1]}"
    return label if value.year == now.year else f"{label} {value.year}"
