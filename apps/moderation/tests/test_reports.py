"""Signalements et modération (ticket #49)."""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.listings.models import ListingStatus
from apps.listings.tests.factories import ListingFactory
from apps.moderation import services
from apps.moderation.models import Report, ReportStatus

pytestmark = pytest.mark.django_db

BASE = "https://sugu.test"


@pytest.fixture
def listing():
    return ListingFactory(published=True, title="Téléphone Tecno neuf")


@pytest.fixture
def staff():
    return UserFactory(is_staff=True, is_superuser=True, email="admin@example.ml")


def member_client(client, user=None):
    user = user or UserFactory()
    client.force_login(user)
    return client, user


def report(user, listing, reason="scam", details=""):
    return services.report_listing(user, listing, reason=reason, details=details, base_url=BASE)


# Page « Signaler »


def test_lien_signaler_sur_la_page_annonce_mais_pas_pour_le_vendeur(client, listing):
    html = client.get(listing.get_absolute_url()).content.decode()
    assert reverse("moderation:report", args=[listing.pk]) in html
    assert 'rel="nofollow"' in html

    client.force_login(listing.user)
    html = client.get(listing.get_absolute_url()).content.decode()
    assert reverse("moderation:report", args=[listing.pk]) not in html


def test_un_visiteur_est_invite_a_se_connecter(client, listing):
    response = client.get(reverse("moderation:report", args=[listing.pk]))

    assert response.status_code == 302
    assert reverse("account_login") in response["Location"]


def test_email_confirme_exige_quand_le_reglage_est_actif(client, listing, settings):
    settings.VERIFIED_EMAIL_REQUIRED = True
    client, user = member_client(client)
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=False)

    response = client.post(reverse("moderation:report", args=[listing.pk]), {"reason": "scam"})

    assert response.status_code == 200
    assert "Confirmez" in response.content.decode()
    assert not Report.objects.exists()


def test_un_membre_signale_une_annonce(client, listing, staff, django_capture_on_commit_callbacks):
    client, user = member_client(client)
    url = reverse("moderation:report", args=[listing.pk])

    page = client.get(url).content.decode()
    assert 'type="radio"' in page and "Arnaque ou fausse annonce" in page
    assert '<meta name="robots" content="noindex' in page

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(url, {"reason": "scam", "details": "  Prix trop beau  "})

    assert response.status_code == 302 and response["Location"] == listing.get_absolute_url()
    saved = Report.objects.get()
    assert (saved.reporter, saved.reason, saved.details, saved.status) == (
        user,
        "scam",
        "Prix trop beau",
        ReportStatus.OPEN,
    )
    # Premier signalement : les administrateurs sont prévenus, pas le vendeur.
    assert [m.to for m in mail.outbox] == [[staff.email]]
    assert "Téléphone Tecno neuf" in mail.outbox[0].body
    assert "Arnaque ou fausse annonce" in mail.outbox[0].body
    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED


def test_un_motif_est_obligatoire(client, listing):
    client, _ = member_client(client)

    response = client.post(reverse("moderation:report", args=[listing.pk]), {"details": "x"})

    assert response.status_code == 200
    assert "Choisissez un motif." in response.content.decode()
    assert not Report.objects.exists()


def test_un_seul_signalement_par_membre(client, listing):
    client, user = member_client(client)
    report(user, listing)

    response = client.get(reverse("moderation:report", args=[listing.pk]), follow=True)

    assert "Vous avez déjà signalé cette annonce" in response.content.decode()
    with pytest.raises(services.AlreadyReported):
        report(user, listing)
    assert Report.objects.count() == 1


def test_un_autre_utilisateur_essaie_le_vendeur_ne_signale_pas_sa_propre_annonce(client, listing):
    client.force_login(listing.user)

    response = client.post(reverse("moderation:report", args=[listing.pk]), {"reason": "scam"})

    assert response.status_code == 403
    assert not Report.objects.exists()


def test_une_annonce_non_visible_ne_se_signale_pas(client):
    draft = ListingFactory()
    client, _ = member_client(client)

    response = client.get(reverse("moderation:report", args=[draft.pk]))

    assert response.status_code == 404


def test_limite_de_debit_des_signalements(client, settings):
    settings.ACCOUNT_RATE_LIMITS = {**settings.ACCOUNT_RATE_LIMITS, "listing_report": "2/h/user"}
    client, _ = member_client(client)
    listings = [ListingFactory(published=True) for _ in range(3)]

    codes = [
        client.post(reverse("moderation:report", args=[item.pk]), {"reason": "other"}).status_code
        for item in listings
    ]

    assert codes == [302, 302, 429]
    assert Report.objects.count() == 2


# Masquage automatique


def test_masquee_au_troisieme_membre_et_vendeur_prevenu(
    client, listing, staff, django_capture_on_commit_callbacks
):
    for _ in range(2):
        report(UserFactory(), listing)
    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED

    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        report(UserFactory(), listing, reason="prohibited")

    listing.refresh_from_db()
    assert listing.status == ListingStatus.SUSPENDED
    recipients = sorted(m.to[0] for m in mail.outbox)
    assert recipients == sorted([staff.email, listing.user.email])
    seller_mail = next(m for m in mail.outbox if m.to == [listing.user.email])
    assert "vérifions" in seller_mail.body
    # Masquée de tous : plus de page publique, plus dans les dernières annonces.
    assert client.get(listing.get_absolute_url()).status_code == 404
    home = client.get(reverse("core:home")).content.decode()
    assert "Téléphone Tecno neuf" not in home


def test_le_vendeur_voit_son_annonce_en_examen(client, listing):
    for _ in range(3):
        report(UserFactory(), listing)
    client.force_login(listing.user)

    html = client.get(reverse("listings:mine")).content.decode()

    assert "Téléphone Tecno neuf" in html and "En examen" in html


def test_une_annonce_vendue_nest_pas_masquee(listing):
    listing.status = ListingStatus.SOLD
    listing.save()

    for _ in range(3):
        report(UserFactory(), listing)

    listing.refresh_from_db()
    assert listing.status == ListingStatus.SOLD


# Décisions de la modération


def test_retirer_lannonce_previent_le_vendeur(listing, staff, django_capture_on_commit_callbacks):
    for reason in ["scam", "scam", "other"]:
        report(UserFactory(), listing, reason=reason)
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        services.uphold(listing, staff, base_url=BASE)

    listing.refresh_from_db()
    assert listing.status == ListingStatus.REMOVED
    assert set(Report.objects.values_list("status", flat=True)) == {ReportStatus.UPHELD}
    assert Report.objects.filter(handled_by=staff, handled_at__isnull=False).count() == 3
    [seller_mail] = mail.outbox
    assert seller_mail.to == [listing.user.email]
    assert "Motif : Arnaque ou fausse annonce" in seller_mail.body  # le motif le plus cité
    assert f"{BASE}/mentions-legales/#contact" in seller_mail.body


def test_classer_sans_suite_remet_en_ligne(listing, staff):
    for _ in range(3):
        report(UserFactory(), listing)

    services.dismiss(listing, staff)

    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED
    assert set(Report.objects.values_list("status", flat=True)) == {ReportStatus.DISMISSED}


def test_apres_un_classement_les_nouveaux_signalements_repartent_de_zero(listing, staff):
    for _ in range(3):
        report(UserFactory(), listing)
    services.dismiss(listing, staff)

    report(UserFactory(), listing)

    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED
    assert services.open_reporter_count(listing) == 1


def test_un_email_en_panne_nannule_pas_le_signalement(
    listing, staff, monkeypatch, django_capture_on_commit_callbacks
):
    def broken(*args, **kwargs):
        raise OSError("SMTP indisponible")

    monkeypatch.setattr(services, "send_mail", broken)

    with django_capture_on_commit_callbacks(execute=True):
        report(UserFactory(), listing)

    assert Report.objects.count() == 1


# Admin


@pytest.fixture
def admin_client(client, staff):
    client.force_login(staff)
    return client


def test_file_des_annonces_signalees(admin_client, listing):
    calm = ListingFactory(published=True, title="Annonce sans signalement")
    other = ListingFactory(published=True, title="Annonce signalée une fois")
    for _ in range(2):
        report(UserFactory(), listing)
    report(UserFactory(), other)

    html = admin_client.get(reverse("admin:moderation_reportedlisting_changelist")).content.decode()

    assert "Téléphone Tecno neuf" in html and "Annonce signalée une fois" in html
    assert calm.title not in html
    assert html.index("Téléphone Tecno neuf") < html.index("Annonce signalée une fois")
    page = admin_client.get(reverse("admin:moderation_reportedlisting_change", args=[listing.pk]))
    assert page.status_code == 200
    assert admin_client.get(reverse("admin:moderation_report_changelist")).status_code == 200


def test_action_retirer_depuis_ladmin(admin_client, listing):
    report(UserFactory(), listing)

    response = admin_client.post(
        reverse("admin:moderation_reportedlisting_changelist"),
        {"action": "action_uphold", "_selected_action": [listing.pk]},
        follow=True,
    )

    assert "1 annonce(s) retirée(s)" in response.content.decode()
    listing.refresh_from_db()
    assert listing.status == ListingStatus.REMOVED


def test_action_classer_depuis_ladmin(admin_client, listing):
    for _ in range(3):
        report(UserFactory(), listing)

    admin_client.post(
        reverse("admin:moderation_reportedlisting_changelist"),
        {"action": "action_dismiss", "_selected_action": [listing.pk]},
    )

    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED


def test_un_membre_ordinaire_na_pas_acces_a_la_file(client, listing):
    client, _ = member_client(client)

    response = client.get(reverse("admin:moderation_reportedlisting_changelist"))

    assert response.status_code == 302
