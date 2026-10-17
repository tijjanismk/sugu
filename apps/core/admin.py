from django import forms
from django.contrib import admin
from django.utils.html import format_html

from . import banners
from .models import Banner


class BannerForm(forms.ModelForm):
    """L'image passe par banners.process_banner (vérifiée, réencodée en WebP, format 2:1)."""

    upload = forms.FileField(
        label="image",
        required=False,
        help_text="JPEG, PNG ou WebP, deux fois plus large que haute : 1200 × 600 px conseillés.",
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

    class Meta:
        model = Banner
        fields = ("upload", "alt", "link", "is_active", "starts_at", "ends_at", "order")

    def clean_upload(self):
        uploaded = self.cleaned_data.get("upload")
        if not uploaded:
            if not self.instance.pk:
                raise forms.ValidationError("Ajoutez une image.", code="required")
            return None
        self.processed = banners.process_banner(uploaded)
        return uploaded

    def save(self, commit=True):
        banner = super().save(commit=False)
        processed = getattr(self, "processed", None)
        if processed:
            banners.set_image(banner, processed)
        if commit:
            banner.save()
        return banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerForm
    list_display = ("preview", "alt", "is_active", "starts_at", "ends_at", "order")
    list_display_links = ("preview", "alt")
    list_editable = ("is_active", "order")
    list_filter = ("is_active",)
    readonly_fields = ("current_image",)
    fieldsets = (
        (None, {"fields": ("current_image", "upload", "alt", "link")}),
        ("Affichage", {"fields": ("is_active", "starts_at", "ends_at", "order")}),
    )

    @admin.display(description="aperçu")
    def preview(self, banner: Banner):
        return format_html(
            '<img src="{}" alt="" width="150" height="75">',
            banner.image_small.url,
        )

    @admin.display(description="image actuelle")
    def current_image(self, banner: Banner):
        if not banner.pk:
            return "—"
        return format_html(
            '<img src="{}" alt="" width="300" height="150"><br>{} × {} px',
            banner.image_small.url,
            banner.width,
            banner.height,
        )
