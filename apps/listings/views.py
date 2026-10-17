from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from apps.accounts.decorators import verified_email_required
from apps.core import ratelimit
from apps.core.templatetags.sugu_format import fcfa

from . import services
from .forms import ListingEditForm, ListingForm, PhotoAddForm, SearchForm
from .models import Category, City, Listing, ListingStatus, Photo
from .seo import listing_seo


@verified_email_required
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
            except services.DailyLimitReached as exc:
                form.add_error(None, exc)
            except ValidationError as exc:
                form.add_error("photos", exc)
            else:
                ratelimit.consume(request, "listing_create")
                messages.success(request, "Annonce publiée. Elle est visible de tous.")
                return redirect(listing)
    else:
        form = ListingForm()
    # Limite quotidienne déjà atteinte (#49) : on le dit avant que le formulaire soit rempli.
    limit = None if form.is_bound else services.daily_limit_error(request.user)
    return render(request, "listings/create.html", {"form": form, "daily_limit": limit})


def listing_detail(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    """Page d'une annonce (ticket #8). Le slug n'est que décoratif : s'il ne correspond plus au
    titre (annonce renommée, lien tronqué), on redirige vers l'adresse exacte."""
    listing = services.get_visible_listing(pk)
    if slug != listing.slug:
        return redirect(listing, permanent=True)
    # Ligne vendeur (ticket #13) : ses annonces en ligne.
    count = listing.user.listings.filter(status=ListingStatus.PUBLISHED).count()
    context = {"listing": listing, "seller_listing_count": count, **listing_seo(request, listing)}
    return render(request, "listings/detail.html", context)


def browse(request: HttpRequest, category: str | None = None, city: str | None = None):
    """Pages catégorie et ville à adresse lisible (référencement, ticket #9, 2026-10-15) :
    /categorie/telephones/, /categorie/telephones/bamako/, /ville/bamako/. Ce sont elles que
    Google indexe (la recherche libre ne l'est pas) ; une page sans annonce ne l'est pas."""
    category = (
        get_object_or_404(Category.objects.select_related("parent"), slug=category)
        if category
        else None
    )
    city = get_object_or_404(City, slug=city) if city else None
    page_obj = Paginator(
        services.search_listings(category=category, city=city), services.PAGE_SIZE
    ).get_page(request.GET.get("page"))
    context = {"page_obj": page_obj, "category": category, "city": city}
    if request.htmx:
        return render(request, "listings/browse.html#browse_page", context)

    counts = services.published_counts()
    count = page_obj.paginator.count
    text = services.browse_text(category, city, count)
    # Liens internes : d'autres villes pour cette catégorie, les sous-catégories, ou les
    # catégories de cette ville. Seulement vers des pages qui ont des annonces.
    links = {}
    if category:
        cities = City.objects.order_by("name")
        links["cities"] = [c for c in cities if c != city and counts[(category.pk, c.pk)]]
        children = category.children.order_by("order", "name")
        links["children"] = [c for c in children if counts[(c.pk, city.pk if city else None)]]
    else:
        parents = Category.objects.filter(parent__isnull=True).order_by("order", "name")
        links["categories"] = [c for c in parents if counts[(c.pk, city.pk)]]
    context.update(
        text=text,
        links=links,
        seo={"description": text["description"], "og_title": text["heading"], "noindex": not count},
    )
    return render(request, "listings/browse.html", context)


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
    # Retour après un clic sur un cœur sans JavaScript : la recherche nettoyée, jamais les
    # valeurs invalides de l'adresse (docs/security.md, « Entrées utilisateur »).
    context = {
        "filters": filters,
        "page_obj": page_obj,
        "next_url": next_url,
        "return_url": _search_url(filters),
    }
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
    # Recherche libre : utile aux visiteurs, pas aux moteurs (contenu en double, combinaisons
    # infinies). Les liens restent suivis ; les pages catégorie et ville sont indexées.
    context["seo"] = {"noindex": True}
    return render(request, "listings/search.html", context)


# --- Gestion par le vendeur (ticket #10) --------------------------------------------------


def _own_listing(request: HttpRequest, pk: int) -> Listing:
    """L'annonce du vendeur connecté. Supprimée ou inexistante : 404 ; d'un autre : 403."""
    listing = get_object_or_404(
        Listing.objects.select_related("city", "category").exclude(status=ListingStatus.REMOVED),
        pk=pk,
    )
    if listing.user_id != request.user.pk:
        raise PermissionDenied("Cette annonce ne vous appartient pas.")
    return listing


@login_required
def my_listings(request: HttpRequest) -> HttpResponse:
    listings = services.with_cover(
        Listing.objects.filter(user=request.user).exclude(status=ListingStatus.REMOVED)
    ).order_by("-created_at")
    return render(request, "listings/mine.html", {"listings": listings})


@login_required
def listing_edit(request: HttpRequest, pk: int) -> HttpResponse:
    listing = _own_listing(request, pk)
    editable = listing.status in services.EDITABLE_STATUSES
    form = ListingEditForm.for_listing(listing, request.POST if request.method == "POST" else None)
    if request.method == "POST" and editable and form.is_valid():
        try:
            services.update_listing(request.user, listing, form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Annonce modifiée.")
            return redirect(listing)
    photos = list(listing.photos.all())
    return render(
        request,
        "listings/edit.html",
        {
            "listing": listing,
            "form": form,
            "editable": editable,
            "photos": photos,
            "photo_form": PhotoAddForm(),
            "photos_left": services.MAX_PHOTOS - len(photos),
        },
    )


def _confirm(request, listing, *, action, title, body, button, danger, done):
    """Page de confirmation (GET) puis action (POST) : une action définitive n'est jamais
    déclenchée par un simple lien (design/components/Button, « Toujours suivi d'une
    confirmation »)."""
    if request.method == "POST":
        try:
            action(request.user, listing)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, done)
        return redirect("listings:mine")
    context = {"listing": listing, "title": title, "body": body, "button": button}
    return render(request, "listings/confirm.html", {**context, "danger": danger})


@login_required
def listing_mark_sold(request: HttpRequest, pk: int) -> HttpResponse:
    listing = _own_listing(request, pk)
    return _confirm(
        request,
        listing,
        action=services.seller_mark_sold,
        title="Marquer comme vendue ?",
        body="L'annonce reste visible avec la mention « Vendu », mais ne sort plus dans la "
        "recherche. Vous ne pourrez plus la remettre en vente.",
        button="Marquer comme vendue",
        danger=False,
        done="Annonce marquée comme vendue.",
    )


@login_required
def listing_delete(request: HttpRequest, pk: int) -> HttpResponse:
    listing = _own_listing(request, pk)
    return _confirm(
        request,
        listing,
        action=services.seller_remove,
        title="Supprimer l'annonce ?",
        body="Elle disparaît de Sugu : accueil, recherche et page de l'annonce. "
        "Cette action est définitive.",
        button="Supprimer l'annonce",
        danger=True,
        done="Annonce supprimée.",
    )


@login_required
def photo_add(request: HttpRequest, pk: int) -> HttpResponse:
    listing = _own_listing(request, pk)
    if request.method == "POST":
        form = PhotoAddForm(request.POST, request.FILES)
        try:
            if not form.is_valid():
                raise ValidationError(form.errors["photos"])
            services.add_photos(request.user, listing, form.cleaned_data["photos"])
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Photos ajoutées.")
    return redirect("listings:edit", pk=listing.pk)


@login_required
def photo_remove(request: HttpRequest, pk: int, photo_pk: int) -> HttpResponse:
    listing = _own_listing(request, pk)
    if request.method == "POST":
        photo = get_object_or_404(Photo, pk=photo_pk, listing=listing)
        try:
            services.remove_photo(request.user, photo)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Photo retirée.")
    return redirect("listings:edit", pk=listing.pk)
