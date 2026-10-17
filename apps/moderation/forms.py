from django import forms

from .models import Report, ReportReason


class ReportForm(forms.ModelForm):
    reason = forms.ChoiceField(
        label="Pourquoi signalez-vous cette annonce ?",
        choices=ReportReason.choices,
        widget=forms.RadioSelect,
        error_messages={"required": "Choisissez un motif."},
    )

    class Meta:
        model = Report
        fields = ("reason", "details")
        labels = {"details": "Précision"}
        widgets = {
            "details": forms.Textarea(
                attrs={"rows": 3, "maxlength": 500, "placeholder": "Ce qui vous a alerté"}
            )
        }
