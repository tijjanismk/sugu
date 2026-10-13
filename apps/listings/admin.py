from django.contrib import admin

from .models import Category, City


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
