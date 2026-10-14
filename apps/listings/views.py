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
                listing = services.create_listing(
                    request.user, data=form.cleaned_data, photos=form.cleaned_data["photos"]
                )
            except ValidationError as exc:
                form.add_error("photos", exc)
            else:
                ratelimit.consume(request, "listing_create")
                messages.success(request, "Annonce publiée. Elle est visible de tous.")
                return redirect(listing)
    else:
        form = ListingForm()
    return render(request, "listings/create.html", {"form": form})


def listing_detail(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    """Page d'une annonce (ticket #8). Le slug n'est que décoratif : s'il ne correspond plus au
    titre (annonce renommée, lien tronqué), on redirige vers l'adresse exacte."""
    listing = services.get_visible_listing(pk)
    if slug != listing.slug:
        return redirect(listing, permanent=True)
    return render(request, "listings/detail.html", {"listing": listing})
