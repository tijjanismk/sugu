from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import verified_email_required
from apps.core import ratelimit
from apps.listings.services import get_visible_listing

from . import services
from .forms import ReportForm


def _site_url(request: HttpRequest) -> str:
    return request.build_absolute_uri("/").rstrip("/")


@verified_email_required
@require_http_methods(["GET", "POST"])
def report_listing(request: HttpRequest, pk: int) -> HttpResponse:
    """« Signaler cette annonce » (ticket #49) : membre connecté à l'email confirmé, comme pour
    écrire à un vendeur ; une fois par annonce, jamais la sienne."""
    listing = get_visible_listing(pk)
    if listing.user_id == request.user.pk:
        raise PermissionDenied
    if services.has_reported(request.user, listing):
        messages.info(request, "Vous avez déjà signalé cette annonce. Merci, nous la regardons.")
        return redirect(listing)

    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not ratelimit.consume(request, "listing_report"):
            return ratelimit.too_many_requests(request)
        try:
            services.report_listing(
                request.user,
                listing,
                reason=form.cleaned_data["reason"],
                details=form.cleaned_data["details"],
                base_url=_site_url(request),
            )
        except services.AlreadyReported:
            pass  # deux envois rapprochés : le premier a suffi
        messages.success(request, "Merci. Nous allons regarder cette annonce.")
        return redirect(listing)
    context = {"listing": listing, "form": form, "seo": {"noindex": True}}
    return render(request, "moderation/report.html", context)
