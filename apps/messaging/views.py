from functools import wraps

from django.contrib import messages as flash
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from django_htmx.http import HttpResponseClientRedirect, retarget

from apps.core import ratelimit
from apps.listings.models import PUBLISHED_STATUSES, Listing
from apps.listings.services import PAGE_SIZE, with_cover

from . import services
from .forms import MessageForm

FIRST_MESSAGE = "Bonjour, l'objet est-il toujours disponible ?"
RATE_LIMITED = "Vous avez envoyé beaucoup de messages. Réessayez dans un moment."


def login_required(view):
    """Comme celui de Django, mais une requête htmx (rafraîchissement, envoi) dont la session a
    expiré recharge toute la page sur la connexion au lieu d'y glisser le formulaire."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        if request.htmx:
            path = request.htmx.current_url_abs_path or request.get_full_path()
            return HttpResponseClientRedirect(redirect_to_login(path).url)
        return redirect_to_login(request.get_full_path())

    return wrapper


@login_required
def inbox(request: HttpRequest) -> HttpResponse:
    """Mes conversations (ticket #12), 20 par page."""
    page_obj = Paginator(services.inbox(request.user), PAGE_SIZE).get_page(request.GET.get("page"))
    for conversation in page_obj:
        conversation.other = conversation.other_party(request.user)
    return render(request, "messaging/inbox.html", {"page_obj": page_obj})


@login_required
def start(request: HttpRequest, listing_pk: int) -> HttpResponse:
    """« Écrire au vendeur » depuis une annonce. La conversation n'existe qu'au premier message ;
    si elle existe déjà, on y va directement."""
    listing = get_object_or_404(
        with_cover(Listing.objects.all()), pk=listing_pk, status__in=PUBLISHED_STATUSES
    )
    if listing.user_id == request.user.pk:
        raise services.CannotContactSelf("Vous ne pouvez pas vous écrire à vous-même.")
    existing = services.find_conversation(listing, request.user)
    if existing:
        return redirect(existing)
    if listing.status not in services.CONTACTABLE_STATUSES:
        flash.info(request, "Cette annonce est vendue : le vendeur ne prend plus de contact.")
        return redirect(listing)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if not ratelimit.consume(request, "conversation_start", dry_run=True):
            return ratelimit.too_many_requests(request)
        if form.is_valid():
            conversation = services.start_conversation(
                request.user, listing, form.cleaned_data["body"]
            )
            ratelimit.consume(request, "conversation_start")
            return redirect(conversation)
    else:
        form = MessageForm(initial={"body": FIRST_MESSAGE})
    context = {"listing": listing, "other": listing.user, "form": form, "items": []}
    return render(request, "messaging/conversation.html", context)


def _after(request: HttpRequest) -> int:
    """Dernier message affiché par la page (champ caché `apres`) ; une valeur invalide vaut 0."""
    value = request.POST.get("apres") if request.method == "POST" else request.GET.get("apres")
    return int(value) if value and value.isdigit() else 0


def _thread_update(request: HttpRequest, conversation, after: int) -> HttpResponse:
    """Les messages arrivés depuis `after`, suivis d'un nouveau rafraîchisseur ; rien de neuf :
    204, htmx ne touche pas à la page."""
    new, previous = services.messages_after(conversation, after)
    if not new:
        return HttpResponse(status=204)
    services.mark_read(conversation, request.user)
    context = {
        "conversation": conversation,
        "new_items": services.thread_items(new, request.user, previous),
        "last_pk": new[-1].pk,
    }
    return render(request, "messaging/conversation.html#thread_update", context)


def _composer_error(request: HttpRequest, error: str) -> HttpResponse:
    response = render(request, "messaging/conversation.html#composer_error", {"error": error})
    return retarget(response, "#composer-error")


@login_required
def conversation(request: HttpRequest, pk: int) -> HttpResponse:
    """Une conversation : l'ouvrir marque lus les messages reçus. L'envoi passe par htmx (le
    message s'ajoute sans recharger) ou, sans JavaScript, par un formulaire classique."""
    conversation = services.get_conversation(request.user, pk)
    form = MessageForm()
    if request.method == "POST":
        if conversation.other_party(request.user).is_deleted:
            raise PermissionDenied("Ce compte a été supprimé.")
        if not ratelimit.consume(request, "message_send", dry_run=True):
            if request.htmx:
                return _composer_error(request, RATE_LIMITED)
            return ratelimit.too_many_requests(request)
        form = MessageForm(request.POST)
        if form.is_valid():
            services.send_message(conversation, request.user, form.cleaned_data["body"])
            ratelimit.consume(request, "message_send")
            if request.htmx:
                return _thread_update(request, conversation, _after(request))
            return redirect(conversation)
        if request.htmx:
            return _composer_error(request, form.errors["body"][0])

    services.mark_read(conversation, request.user)
    thread = list(conversation.messages.all())
    context = {
        "conversation": conversation,
        "listing": with_cover(Listing.objects.filter(pk=conversation.listing_id)).get(),
        "other": conversation.other_party(request.user),
        "form": form,
        "items": services.thread_items(thread, request.user),
        "last_pk": thread[-1].pk if thread else 0,
    }
    return render(request, "messaging/conversation.html", context)


@require_GET
@login_required
def poll(request: HttpRequest, pk: int) -> HttpResponse:
    """Rafraîchissement htmx toutes les 10 s quand la conversation est ouverte."""
    conversation = services.get_conversation(request.user, pk)
    return _thread_update(request, conversation, _after(request))
