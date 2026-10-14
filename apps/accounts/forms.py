import re

from django import forms

from apps.listings.forms import reject_links
from apps.listings.models import City

from .models import User

_PHONE_SEPARATORS = re.compile(r"[\s.\-()]")
_PHONE = re.compile(r"\+?\d{8,15}")
PHONE_ERROR = "Numéro invalide : 8 à 15 chiffres, avec l'indicatif si besoin (+223…)."


def clean_phone(value: str) -> str:
    """« 76 12 34 56 » ou « +223 76-12-34-56 » → chiffres seuls (et le + de l'indicatif),
    pour un lien « Appeler » qui marche."""
    value = _PHONE_SEPARATORS.sub("", value or "")
    if value and not _PHONE.fullmatch(value):
        raise forms.ValidationError(PHONE_ERROR, code="phone")
    return value


def _display_name_field():
    return forms.CharField(
        label="Nom affiché",
        max_length=50,
        help_text="Visible sur vos annonces.",
        widget=forms.TextInput(attrs={"autocomplete": "nickname"}),
    )


def _phone_field():
    return forms.CharField(
        label="Téléphone",
        max_length=20,
        required=False,
        help_text="Les acheteurs ne le voient qu'une fois connectés.",
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )


class SignupForm(forms.Form):
    """Champs ajoutés au formulaire d'inscription d'allauth (ACCOUNT_SIGNUP_FORM_CLASS)."""

    display_name = _display_name_field()
    phone = _phone_field()

    field_order = ["display_name", "email", "phone", "password1"]

    def clean_display_name(self):
        return reject_links(self.cleaned_data["display_name"])

    def clean_phone(self):
        return clean_phone(self.cleaned_data["phone"])

    def signup(self, request, user):
        user.display_name = self.cleaned_data["display_name"]
        user.phone = self.cleaned_data["phone"]
        user.save(update_fields=["display_name", "phone"])


class ProfileForm(forms.ModelForm):
    """Profil (ticket #13) : nom affiché, téléphone, ville ; emails de messages (#12)."""

    display_name = _display_name_field()
    phone = _phone_field()
    city = forms.ModelChoiceField(
        label="Ville",
        queryset=City.objects.all(),
        required=False,
        empty_label="Choisir une ville",
    )

    class Meta:
        model = User
        fields = ["display_name", "phone", "city", "notify_messages"]
        labels = {"notify_messages": "Me prévenir par email des nouveaux messages"}

    def clean_display_name(self):
        return reject_links(self.cleaned_data["display_name"])

    def clean_phone(self):
        return clean_phone(self.cleaned_data["phone"])


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.", code="password")
        return password
