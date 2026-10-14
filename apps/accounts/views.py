from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core import ratelimit

from . import services
from .forms import DeleteAccountForm, ProfileForm


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """Mon profil (ticket #13). Pas d'identifiant dans l'adresse : on ne modifie que le sien."""
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil enregistré.")
        return redirect("account_profile")
    return render(request, "account/profile.html", {"form": form})


@require_POST
@login_required
def sign_out_others(request: HttpRequest) -> HttpResponse:
    """Déconnecte tous les autres appareils ; celui-ci reste connecté."""
    services.sign_out_everywhere(request.user)
    update_session_auth_hash(request, request.user)
    messages.success(request, "Vos autres appareils sont déconnectés.")
    return redirect("account_profile")


@login_required
def delete_account(request: HttpRequest) -> HttpResponse:
    """Suppression du compte, confirmée par le mot de passe : un téléphone prêté ou une session
    volée ne suffit pas. Essais limités, comme une connexion."""
    form = DeleteAccountForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if not ratelimit.consume(request, "account_delete"):
            return ratelimit.too_many_requests(request)
        if form.is_valid():
            services.delete_account(request.user)
            logout(request)
            messages.success(request, "Votre compte est supprimé. Merci d'avoir utilisé Sugu.")
            return redirect("core:home")
    return render(request, "account/delete.html", {"form": form})
