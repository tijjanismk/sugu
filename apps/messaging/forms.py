from django import forms

from .models import MESSAGE_MAX_LENGTH


class MessageForm(forms.Form):
    body = forms.CharField(
        label="Message",
        max_length=MESSAGE_MAX_LENGTH,
        error_messages={
            "required": "Écrivez un message.",
            "max_length": f"{MESSAGE_MAX_LENGTH} caractères au plus.",
        },
        widget=forms.TextInput(attrs={"placeholder": "Écrire un message", "autocomplete": "off"}),
    )
