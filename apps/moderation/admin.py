from django.contrib import admin, messages
from django.db.models import Count, Max, Q
from django.utils.html import format_html

from . import services
from .models import Report, ReportedListing, ReportStatus

OPEN = Q(reports__status=ReportStatus.OPEN)


class OpenReportInline(admin.TabularInline):
    model = Report
    fk_name = "listing"
    fields = ("created_at", "reporter", "reason", "details", "status")
    readonly_fields = fields
    extra = 0
    can_delete = False
    verbose_name_plural = "signalements"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReportedListing)
class ReportedListingAdmin(admin.ModelAdmin):
    """File de modération : les annonces signalées, les plus signalées d'abord. Les décisions
    passent par services.py (vendeur prévenu par email, annonce masquée remise en ligne)."""

    list_display = ("title", "status", "open_reports", "reasons", "last_report", "seller")
    list_filter = ("status",)
    actions = ["action_uphold", "action_dismiss"]
    inlines = [OpenReportInline]
    fields = ("page", "title", "seller", "status", "category", "city", "description")
    readonly_fields = fields

    def get_queryset(self, request):
        # Pas super() : il trie avant l'annotation, et l'ordre porte sur les comptes annotés.
        return (
            self.model._default_manager.select_related("user", "category", "city")
            .annotate(open_count=Count("reports", filter=OPEN), last_at=Max("reports__created_at"))
            .filter(open_count__gt=0)
        )

    def get_ordering(self, request):
        return ["-open_count", "-last_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="signalements", ordering="open_count")
    def open_reports(self, listing):
        return listing.open_count

    @admin.display(description="motifs")
    def reasons(self, listing):
        labels = sorted(
            {r.get_reason_display() for r in listing.reports.filter(status=ReportStatus.OPEN)}
        )
        return ", ".join(labels)

    @admin.display(description="dernier signalement", ordering="last_at")
    def last_report(self, listing):
        return listing.last_at

    @admin.display(description="vendeur")
    def seller(self, listing):
        return listing.user.display_name

    @admin.display(description="page de l'annonce")
    def page(self, listing):
        # Une annonce en examen n'a plus de page publique : seule l'admin la montre.
        if listing.status in ("published", "reserved", "sold"):
            return format_html('<a href="{}">Voir l\'annonce</a>', listing.get_absolute_url())
        return "Masquée (en examen) : détails ci-dessous"

    @admin.action(description="Retirer l'annonce (signalements fondés, vendeur prévenu)")
    def action_uphold(self, request, queryset):
        base_url = request.build_absolute_uri("/").rstrip("/")
        count = 0
        for listing in queryset:
            services.uphold(listing, request.user, base_url=base_url)
            count += 1
        messages.success(request, f"{count} annonce(s) retirée(s), vendeur(s) prévenu(s).")

    @admin.action(description="Classer sans suite (et remettre en ligne si masquée)")
    def action_dismiss(self, request, queryset):
        count = 0
        for listing in queryset:
            services.dismiss(listing, request.user)
            count += 1
        messages.success(request, f"{count} annonce(s) classée(s) sans suite.")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Historique de tous les signalements, en lecture seule."""

    list_display = ("created_at", "listing", "reason", "reporter", "status", "handled_by")
    list_filter = ("status", "reason")
    search_fields = ("listing__title",)
    readonly_fields = [f.name for f in Report._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
