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
def day_label(value: datetime | None, now: datetime | None = None) -> str:
    """Séparateur de jour d'une conversation : « Aujourd'hui », « Hier », puis « 12 oct. »
    (avec l'année si ce n'est pas l'année en cours)."""
    if value is None:
        return ""
    today = timezone.localtime(now or timezone.now()).date()
    day = timezone.localtime(value).date()
    if day == today:
        return "Aujourd'hui"
    if (today - day).days == 1:
        return "Hier"
    label = f"{day.day} {MONTHS[day.month - 1]}"
    return label if day.year == today.year else f"{label} {day.year}"


@register.filter
def month_year(value: datetime | None) -> str:
    """« Membre depuis oct. 2026 »."""
    if value is None:
        return ""
    value = timezone.localtime(value)
    return f"{MONTHS[value.month - 1]} {value.year}"


@register.filter
def phone(value: str | None) -> str:
    """Numéro enregistré en chiffres (« +22376123456 ») → lisible, par paires après
    l'indicatif : « +223 76 12 34 56 », « 76 12 34 56 ». Autre longueur : tel quel."""
    value = value or ""
    prefix, digits = ("", value) if not value.startswith("+") else (value[:4] + " ", value[4:])
    if len(digits) != 8 or not digits.isdigit():
        return value
    return prefix + " ".join(digits[i : i + 2] for i in range(0, 8, 2))


@register.filter
def initials(name: str | None) -> str:
    """Avatar (design/components/Avatar) : « Aminata Koné » → « AK », « Moussa » → « M »."""
    words = (name or "").split()
    return "".join(word[0] for word in words[:2]).upper()


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
