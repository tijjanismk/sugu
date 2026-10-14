import re

from django import forms

from .images import MAX_UPLOAD_BYTES
from .models import (
    DESCRIPTION_MAX_LENGTH,
    MAX_DISTANCE_KM,
    MAX_PHOTOS,
    Category,
    City,
    Listing,
    PaymentMethod,
)

MAX_PRICE = 1_000_000_000

# Liens, adresses web et emails : refusés dans une annonce (ajout du 2026-10-14). D'autres sites
# d'annonces ne doivent pas détourner les acheteurs ; le contact passe par Sugu (ticket #12).
LINK_PATTERN = re.compile(
    r"(https?://|www\.|[\w.+-]+@[\w-]+\.[a-z]{2,}"
    r"|\b[a-z0-9-]+\.(com|net|org|info|biz|io|co|me|app|shop|store|site|online|africa"
    r"|ml|sn|ci|bf|gn|ne|tg|bj|cm|fr)\b)",
    re.IGNORECASE,
)
LINK_ERROR = "Les liens vers d'autres sites, les adresses web et les emails ne sont pas acceptés."


def reject_links(value: str) -> str:
    if value and LINK_PATTERN.search(value):
        raise forms.ValidationError(LINK_ERROR, code="link")
    return value


def validate_photo_files(photos: list) -> list:
    if len(photos) > MAX_PHOTOS:
        raise forms.ValidationError(f"{MAX_PHOTOS} photos au plus.")
    for photo in photos:
        if photo.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                f"Photo trop lourde ({photo.size // (1024 * 1024)} Mo). 8 Mo au plus."
            )
    return photos


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Plusieurs fichiers dans un seul champ (doc Django « Uploading multiple files »)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, list | tuple):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)] if data else single_clean(data, initial)


class ListingContentForm(forms.Form):
    """Contenu d'une annonce, commun au dépôt (#7) et à la modification (#10)."""

    title = forms.CharField(
        label="Titre",
        max_length=Listing._meta.get_field("title").max_length,
        help_text="Dites ce que c'est, pas « à vendre ».",
        widget=forms.TextInput(attrs={"placeholder": "Ex. : Vélo de course Peugeot"}),
    )
    category = forms.ModelChoiceField(
        label="Catégorie",
        queryset=Category.objects.filter(parent__isnull=False),
        empty_label="Choisir une catégorie",
    )
    city = forms.ModelChoiceField(
        label="Ville", queryset=City.objects.all(), empty_label="Choisir une ville"
    )
    neighborhood = forms.CharField(
        label="Quartier ou commune",
        required=False,
        max_length=Listing._meta.get_field("neighborhood").max_length,
        widget=forms.TextInput(attrs={"placeholder": "Ex. : Sabalibougou, Commune V"}),
    )
    distance_km = forms.IntegerField(
        label="Distance de la ville",
        required=False,
        min_value=1,
        max_value=MAX_DISTANCE_KM,
        help_text="Si l'objet est hors de la ville : 20 pour « à 20 km de Bamako ».",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    price = forms.CharField(
        label="Prix",
        required=False,
        help_text="Laissez vide pour « À débattre ».",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    payment_methods = forms.MultipleChoiceField(
        label="Modes de règlement acceptés",
        required=False,
        choices=PaymentMethod.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    description = forms.CharField(
        label="Description",
        max_length=DESCRIPTION_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={"rows": 5, "placeholder": "État, âge, accessoires, lieu de remise…"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sous-catégories regroupées sous leur catégorie principale (<optgroup>).
        groups = {}
        for category in Category.objects.filter(parent__isnull=False).select_related("parent"):
            groups.setdefault(category.parent, []).append((category.pk, category.name))
        self.fields["category"].choices = [("", "Choisir une catégorie")] + [
            (parent.name, children)
            for parent, children in sorted(groups.items(), key=lambda kv: kv[0].order)
        ]

    def clean_price(self):
        raw = self.cleaned_data["price"]
        digits = raw.replace(" ", "").replace(" ", "").replace("\xa0", "").replace(".", "")
        if not digits:
            return None
        if not digits.isdigit():
            raise forms.ValidationError("Indiquez un prix en chiffres, sans décimales.")
        price = int(digits)
        if price > MAX_PRICE:
            raise forms.ValidationError("Ce prix paraît trop élevé.")
        return price

    def clean_title(self):
        return reject_links(self.cleaned_data["title"])

    def clean_neighborhood(self):
        return reject_links(self.cleaned_data["neighborhood"])

    def clean_description(self):
        return reject_links(self.cleaned_data["description"])


class ListingForm(ListingContentForm):
    """Dépôt d'une annonce (ticket #7). Le traitement des photos est fait par le service."""

    photos = MultipleFileField(
        label="Photos",
        help_text="La première photo est la couverture. Prenez-la en plein jour, sur fond simple.",
        widget=MultipleFileInput(attrs={"accept": "image/*", "data-photo-input": ""}),
    )

    field_order = [
        "photos", "title", "category", "city", "neighborhood", "distance_km", "price",
        "payment_methods", "description",
    ]  # fmt: skip

    def clean_photos(self):
        return validate_photo_files(self.cleaned_data["photos"])


class ListingEditForm(ListingContentForm):
    """Modification du contenu (ticket #10) ; les photos ont leur propre formulaire."""

    @classmethod
    def for_listing(cls, listing, data=None):
        initial = {
            "title": listing.title,
            "category": listing.category_id,
            "city": listing.city_id,
            "neighborhood": listing.neighborhood,
            "distance_km": listing.distance_km,
            "price": "" if listing.price is None else str(listing.price),
            "payment_methods": listing.payment_methods,
            "description": listing.description,
        }
        return cls(data, initial=initial)


class PhotoAddForm(forms.Form):
    photos = MultipleFileField(
        label="Ajouter des photos",
        widget=MultipleFileInput(attrs={"accept": "image/*", "data-photo-input": ""}),
    )

    def clean_photos(self):
        return validate_photo_files(self.cleaned_data["photos"])


class SearchForm(forms.Form):
    """Paramètres GET de la recherche (ticket #9). Une valeur invalide n'est jamais une erreur :
    elle est ignorée et n'est pas réaffichée (docs/security.md, « Entrées utilisateur »)."""

    q = forms.CharField(required=False, max_length=100)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(), to_field_name="slug", required=False
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), to_field_name="slug", required=False)
    price_min = forms.IntegerField(required=False, min_value=0, max_value=MAX_PRICE)
    price_max = forms.IntegerField(required=False, min_value=0, max_value=MAX_PRICE)

    def valid_filters(self) -> dict:
        """Les seuls paramètres valides et renseignés ; le reste est ignoré."""
        self.is_valid()
        values = {
            name: value
            for name, value in self.cleaned_data.items()
            if value not in (None, "") and name not in self.errors
        }
        if "q" in values:
            values["q"] = values["q"].strip()
            if not values["q"]:
                del values["q"]
        low, high = values.get("price_min"), values.get("price_max")
        if low is not None and high is not None and low > high:
            values["price_min"], values["price_max"] = high, low
        return values
