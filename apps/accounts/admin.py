from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class SuguUserCreationForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")


class SuguUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = SuguUserChangeForm
    add_form = SuguUserCreationForm
    ordering = ("email",)
    list_display = (
        "email",
        "display_name",
        "phone",
        "city",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_select_related = ("city",)
    search_fields = ("email", "display_name", "phone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("display_name", "phone", "phone_verified", "city")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )
