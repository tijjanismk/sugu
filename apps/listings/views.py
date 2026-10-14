from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.core import ratelimit

from . import services
from .forms import ListingForm


@login_required
def listing_create(request: HttpRequest) -> HttpResponse:
    """Dépôt d'une annonce avec ses photos (ticket #7)."""
    if request.method == "POST":
        # On vérifie la limite avant, mais on ne décompte qu'une annonce réellement publiée :
        # corriger une erreur de formulaire ne doit pas épuiser le quota.
        if not ratelimit.consume(request, "listing_create", dry_run=True):
            return ratelimit.too_many_requests(request)
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                services.create_listing(
                    request.user, data=form.cleaned_data, photos=form.cleaned_data["photos"]
                )
            except ValidationError as exc:
                form.add_error("photos", exc)
            else:
                ratelimit.consume(request, "listing_create")
                messages.success(request, "Annonce publiée. Elle est visible de tous.")
                return redirect("core:home")
    else:
        form = ListingForm()
    return render(request, "listings/create.html", {"form": form})
