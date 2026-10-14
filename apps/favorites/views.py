from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect

from apps.listings.models import PUBLISHED_STATUSES, Listing
from apps.listings.services import PAGE_SIZE

from . import services


def _next_url(request: HttpRequest) -> str | None:
    """Page d'où vient le clic : l'adresse affichée par le navigateur en htmx, le champ `next`
    sans JavaScript. Une adresse d'un autre site est ignorée (pas de redirection ouverte)."""
    url = request.htmx.current_url_abs_path if request.htmx else request.POST.get("next")
    allowed = url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return url if allowed else None


@require_POST
def favorite_set(request: HttpRequest, listing_pk: int) -> HttpResponse:
    """Cœur d'une annonce (ticket #11). En htmx, seul le bouton est renvoyé ; sans JavaScript,
    retour à la page d'origine. Non connecté : page de connexion, puis retour à cette page."""
    listing = get_object_or_404(Listing, pk=listing_pk, status__in=PUBLISHED_STATUSES)
    next_url = _next_url(request) or listing.get_absolute_url()
    if not request.user.is_authenticated:
        login_url = redirect_to_login(next_url).url
        return HttpResponseClientRedirect(login_url) if request.htmx else redirect(login_url)
    on = services.set_favorite(request.user, listing, request.POST.get("on") == "1")
    if not request.htmx:
        return redirect(next_url)
    context = {
        "listing": listing,
        "variant": "bar" if request.POST.get("variant") == "bar" else "card",
        "return_url": next_url,
        "favorite_ids": frozenset({listing.pk}) if on else frozenset(),
    }
    return render(request, "favorites/button.html", context)


@login_required
def favorite_list(request: HttpRequest) -> HttpResponse:
    """Mes favoris, 20 par page ; « Voir plus » en htmx comme sur l'accueil."""
    page_obj = Paginator(services.favorite_listings(request.user), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    if request.htmx:
        return render(request, "favorites/list.html#listing_page", {"page_obj": page_obj})
    return render(request, "favorites/list.html", {"page_obj": page_obj})
