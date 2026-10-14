from django.contrib import admin

from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "listing", "created_at"]
    list_select_related = ["user", "listing"]
    raw_id_fields = ["user", "listing"]
