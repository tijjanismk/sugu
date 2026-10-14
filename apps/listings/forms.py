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


class ListingForm(forms.Form):
    """Dépôt d'une annonce (ticket #7). Le traitement des photos est fait par le service."""

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
    photos = MultipleFileField(
        label="Photos",
        help_text="La première photo est la couverture. Prenez-la en plein jour, sur fond simple.",
        widget=MultipleFileInput(attrs={"accept": "image/*", "data-photo-input": ""}),
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

    def clean_photos(self):
        photos = self.cleaned_data["photos"]
        if len(photos) > MAX_PHOTOS:
            raise forms.ValidationError(f"{MAX_PHOTOS} photos au plus.")
        for photo in photos:
            if photo.size > MAX_UPLOAD_BYTES:
                raise forms.ValidationError(
                    f"Photo trop lourde ({photo.size // (1024 * 1024)} Mo). 8 Mo au plus."
                )
        return photos


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
