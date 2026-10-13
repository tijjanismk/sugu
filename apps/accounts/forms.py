from django import forms


class SignupForm(forms.Form):
    """Champs ajoutés au formulaire d'inscription d'allauth (ACCOUNT_SIGNUP_FORM_CLASS)."""

    display_name = forms.CharField(
        label="Nom affiché",
        max_length=50,
        help_text="Visible sur vos annonces.",
        widget=forms.TextInput(attrs={"autocomplete": "nickname"}),
    )
    phone = forms.CharField(
        label="Téléphone",
        max_length=20,
        required=False,
        help_text="Les acheteurs ne le voient qu'une fois connectés.",
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )

    field_order = ["display_name", "email", "phone", "password1"]

    def signup(self, request, user):
        user.display_name = self.cleaned_data["display_name"]
        user.phone = self.cleaned_data["phone"]
        user.save(update_fields=["display_name", "phone"])
