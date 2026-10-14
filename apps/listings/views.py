from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from apps.core import ratelimit
from apps.core.templatetags.sugu_format import fcfa

from . import services
from .forms import ListingForm, SearchForm
from .models import Category, City


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


def _search_url(filters: dict, **changes) -> str:
    """URL de recherche bâtie uniquement à partir des filtres validés (jamais du GET brut)."""
    params = {**filters, **changes}
    query = {
        name: getattr(value, "slug", value)
        for name, value in params.items()
        if value not in (None, "")
    }
    base = reverse("listings:search")
    return f"{base}?{urlencode(query)}" if query else base


def search(request: HttpRequest) -> HttpResponse:
    """Recherche et filtres (ticket #9). Formulaire GET : l'URL contient toute la recherche et se
    partage. « Voir plus » (htmx) renvoie seulement le partial de la page suivante."""
    filters = SearchForm(request.GET).valid_filters()
    page_obj = Paginator(services.search_listings(**filters), services.PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    next_url = (
        _search_url(filters, page=page_obj.next_page_number()) if page_obj.has_next() else None
    )
    context = {"filters": filters, "page_obj": page_obj, "next_url": next_url}
    if request.htmx:
        return render(request, "listings/search.html#results_page", context)

    labels = {
        "q": lambda v: f"« {v} »",
        "category": lambda v: v.name,
        "city": lambda v: v.name,
        "price_min": lambda v: f"Dès {fcfa(v)}",
        "price_max": lambda v: f"Jusqu'à {fcfa(v)}",
    }
    chips = [
        {"label": labels[name](value), "remove_url": _search_url(filters, **{name: None})}
        for name, value in filters.items()
    ]
    context.update(
        chips=chips,
        filter_count=sum(1 for name in filters if name != "q"),
        categories=Category.objects.filter(parent__isnull=True).prefetch_related("children"),
        cities=City.objects.all(),
    )
    return render(request, "listings/search.html", context)
