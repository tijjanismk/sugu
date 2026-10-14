from django.contrib import admin, messages

from . import services
from .models import Category, City, Listing, Photo
from .services import InvalidStatusTransition


class SubcategoryInline(admin.TabularInline):
    model = Category
    fk_name = "parent"
    fields = ("name", "slug", "order")
    extra = 0
    verbose_name = "sous-catégorie"
    verbose_name_plural = "sous-catégories"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "icon", "order")
    list_filter = (("parent", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("name", "slug")
    ordering = ("parent__order", "order", "name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubcategoryInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Seules les catégories principales peuvent être parentes (deux niveaux au plus).
        if db_field.name == "parent":
            kwargs["queryset"] = Category.objects.filter(parent__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "slug")
    list_filter = ("region",)
    search_fields = ("name", "region")
    prepopulated_fields = {"slug": ("name",)}


class PhotoInline(admin.TabularInline):
    model = Photo
    fields = ("order", "thumb", "width", "height")
    readonly_fields = ("thumb", "width", "height")
    extra = 0
    can_delete = True


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    """Modération des annonces. Le statut et le prix ne se modifient pas à la main : les actions
    passent par services.py pour respecter les transitions et la règle de baisse de prix."""

    list_display = ("title", "user", "category", "city", "price", "status", "published_at")
    list_filter = ("status", "city", ("category", admin.RelatedOnlyFieldListFilter))
    search_fields = ("title", "description", "user__email", "user__display_name")
    list_select_related = ("user", "category", "city")
    autocomplete_fields = ("user",)
    date_hierarchy = "published_at"
    readonly_fields = (
        "status",
        "published_at",
        "price",
        "previous_price",
        "price_dropped_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("user", "title", "description", "category", "city")}),
        (
            "Prix et règlement",
            {"fields": ("price", "previous_price", "price_dropped_at", "payment_methods")},
        ),
        ("Statut", {"fields": ("status", "published_at", "created_at", "updated_at")}),
    )
    inlines = [PhotoInline]
    actions = ["action_remove", "action_mark_sold"]

    def _apply(self, request, queryset, transition, label):
        done, refused = 0, 0
        for listing in queryset:
            try:
                transition(listing)
                done += 1
            except InvalidStatusTransition:
                refused += 1
        if done:
            self.message_user(request, f"{done} annonce(s) {label}.", messages.SUCCESS)
        if refused:
            self.message_user(
                request,
                f"{refused} annonce(s) ignorée(s) : transition impossible.",
                messages.WARNING,
            )

    @admin.action(description="Retirer les annonces sélectionnées")
    def action_remove(self, request, queryset):
        self._apply(request, queryset, services.remove, "retirée(s)")

    @admin.action(description="Marquer comme vendues")
    def action_mark_sold(self, request, queryset):
        self._apply(request, queryset, services.mark_sold, "marquée(s) vendue(s)")
