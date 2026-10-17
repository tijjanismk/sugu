"""Signalements et modération (ticket #49, décisions du 2026-10-17).

- Un membre signale une annonce visible, une seule fois, jamais la sienne.
- Au premier signalement d'une annonce, les administrateurs sont prévenus par email.
- Quand REPORTS_TO_SUSPEND membres différents l'ont signalée, l'annonce passe « en examen » :
  masquée de tous, le vendeur est prévenu. La modération la retire ou la remet en ligne.
- Retirer l'annonce prévient le vendeur avec le motif ; classer sans suite remet en ligne une
  annonce masquée.

Les emails partent après validation de la transaction ; une panne d'envoi est journalisée et
n'annule jamais la décision (même règle que apps/messaging/notifications.py).
"""

import logging
from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.listings import services as listings
from apps.listings.models import Listing, ListingStatus

from .models import Report, ReportReason, ReportStatus

logger = logging.getLogger(__name__)

# Une annonce vendue ou déjà masquée ne peut plus être masquée par les signalements.
SUSPENDABLE_STATUSES = (ListingStatus.PUBLISHED, ListingStatus.RESERVED)


class AlreadyReported(ValidationError):
    pass


def has_reported(user, listing: Listing) -> bool:
    return user.is_authenticated and Report.objects.filter(listing=listing, reporter=user).exists()


def open_reporter_count(listing: Listing) -> int:
    return listing.reports.filter(status=ReportStatus.OPEN).values("reporter").distinct().count()


@transaction.atomic
def report_listing(user, listing: Listing, *, reason: str, details: str, base_url: str) -> Report:
    """Enregistre le signalement. Lève PermissionDenied sur sa propre annonce et
    AlreadyReported si le membre l'a déjà signalée."""
    if listing.user_id == user.pk:
        raise PermissionDenied("On ne signale pas sa propre annonce.")
    locked = Listing.objects.select_for_update().get(pk=listing.pk)
    try:
        with transaction.atomic():
            report = Report.objects.create(
                listing=locked, reporter=user, reason=reason, details=details.strip()
            )
    except IntegrityError as exc:
        raise AlreadyReported("Vous avez déjà signalé cette annonce.", code="already") from exc

    count = open_reporter_count(locked)
    if count == 1:
        _on_commit_mail(_staff_new_report, locked, report, base_url)
    if count >= settings.REPORTS_TO_SUSPEND and locked.status in SUSPENDABLE_STATUSES:
        listings.suspend(locked)
        _on_commit_mail(_seller_suspended, locked, base_url)
        _on_commit_mail(_staff_suspended, locked, base_url)
    listing.status = locked.status
    return report


def _close_reports(listing: Listing, status: str, staff) -> int:
    return listing.reports.filter(status=ReportStatus.OPEN).update(
        status=status, handled_at=timezone.now(), handled_by=staff
    )


def main_reason(listing: Listing) -> str:
    """Le motif le plus cité parmi les signalements à examiner (« Autre » en dernier recours)."""
    reasons = Counter(
        listing.reports.filter(status=ReportStatus.OPEN).values_list("reason", flat=True)
    )
    if not reasons:
        return ReportReason.OTHER.label
    return ReportReason(reasons.most_common(1)[0][0]).label


@transaction.atomic
def uphold(listing: Listing, staff, *, base_url: str) -> None:
    """Retire l'annonce (définitif) et prévient le vendeur du motif."""
    reason = main_reason(listing)
    if listing.status != ListingStatus.REMOVED:
        listings.remove(listing)
    _close_reports(listing, ReportStatus.UPHELD, staff)
    _on_commit_mail(_seller_removed, listing, reason, base_url)


@transaction.atomic
def dismiss(listing: Listing, staff) -> None:
    """Classe les signalements sans suite ; une annonce masquée revient en ligne."""
    if listing.status == ListingStatus.SUSPENDED:
        listings.reinstate(listing)
    _close_reports(listing, ReportStatus.DISMISSED, staff)


# --- Emails ------------------------------------------------------------------------------


def _on_commit_mail(build, *args) -> None:
    def _send():
        try:
            subject, body, recipients = build(*args)
            if recipients:
                send_mail(
                    f"{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}{subject}", body, None, recipients
                )
        except Exception:
            # Ni adresse ni contenu dans le journal (docs/security.md).
            logger.exception("Email de modération non envoyé (%s)", build.__name__)

    transaction.on_commit(_send)


def _staff_emails() -> list[str]:
    users = get_user_model().objects.filter(is_staff=True, is_active=True).exclude(email="")
    return list(users.values_list("email", flat=True))


def _seller_email(listing: Listing) -> list[str]:
    seller = listing.user
    if not seller.is_active or seller.is_deleted or not seller.email:
        return []
    return [seller.email]


def _context(listing: Listing, base_url: str, **extra) -> dict:
    return {
        "listing_title": listing.title,
        "listing_url": base_url + listing.get_absolute_url(),
        "seller": listing.user.display_name,
        "contact_url": base_url + reverse("core:legal_notice") + "#contact",
        **extra,
    }


def _staff_new_report(listing: Listing, report: Report, base_url: str):
    context = _context(listing, base_url, reason=report.get_reason_display())
    body = render_to_string("moderation/email/staff_new_report.txt", context)
    return "Annonce signalée", body, _staff_emails()


def _staff_suspended(listing: Listing, base_url: str):
    context = _context(listing, base_url, count=open_reporter_count(listing))
    body = render_to_string("moderation/email/staff_suspended.txt", context)
    return "Annonce masquée après plusieurs signalements", body, _staff_emails()


def _seller_suspended(listing: Listing, base_url: str):
    body = render_to_string("moderation/email/seller_suspended.txt", _context(listing, base_url))
    return "Votre annonce est en cours de vérification", body, _seller_email(listing)


def _seller_removed(listing: Listing, reason: str, base_url: str):
    context = _context(listing, base_url, reason=reason)
    body = render_to_string("moderation/email/seller_removed.txt", context)
    return "Votre annonce a été retirée", body, _seller_email(listing)
