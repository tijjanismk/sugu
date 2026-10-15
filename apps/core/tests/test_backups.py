"""Sauvegardes de la base (ticket #17) : rangement dans le bucket, envoi, liste, téléchargement.
Le bucket est simulé par le Stubber de botocore ; la vraie chaîne pg_dump → R2 → pg_restore
est essayée à la répétition générale (docs/runbook.md, « Sauvegardes »)."""

import io
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.core import backups
from apps.core.checks import check_backups

ROOT = Path(__file__).resolve().parents[3]
DUMP = b"PGDMP" + b"\0" * 2048


@pytest.fixture
def configured(settings):
    settings.BACKUP_STORAGE = {
        "bucket": "sugu-backups",
        "endpoint_url": "https://compte.r2.cloudflarestorage.com",
        "access_key": "cle",
        "secret_key": "secret",
    }


@pytest.fixture
def s3(configured, monkeypatch):
    client = boto3.client(
        "s3",
        endpoint_url="https://compte.r2.cloudflarestorage.com",
        aws_access_key_id="cle",
        aws_secret_access_key="secret",
        region_name="auto",
    )
    monkeypatch.setattr(backups, "client", lambda: client)
    with Stubber(client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def _stdin(monkeypatch, data):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))


def _today(monkeypatch, day):
    monkeypatch.setattr(timezone, "localdate", lambda: day)


@pytest.mark.parametrize(
    ("day", "keys"),
    [
        (date(2026, 10, 15), ["quotidien/sugu-2026-10-15.dump"]),
        (date(2026, 11, 1), ["quotidien/sugu-2026-11-01.dump", "mensuel/sugu-2026-11.dump"]),
    ],
)
def test_rangement_quotidien_et_mensuel(day, keys):
    assert backups.keys_for(day) == keys


def test_envoi_dans_le_bucket(s3, monkeypatch):
    _stdin(monkeypatch, DUMP)
    _today(monkeypatch, date(2026, 11, 1))
    for key in ("quotidien/sugu-2026-11-01.dump", "mensuel/sugu-2026-11.dump"):
        s3.add_response("put_object", {}, {"Bucket": "sugu-backups", "Key": key, "Body": DUMP})
    out = io.StringIO()

    call_command("sauvegarde_envoyer", stdout=out)

    assert "mensuel/sugu-2026-11.dump" in out.getvalue()


def test_une_sauvegarde_vide_nest_pas_envoyee(s3, monkeypatch):
    _stdin(monkeypatch, b"")

    with pytest.raises(CommandError, match="vide ou incomplète"):
        call_command("sauvegarde_envoyer")


def test_sans_bucket_la_copie_du_serveur_suffit(settings, monkeypatch):
    settings.BACKUP_STORAGE = {**settings.BACKUP_STORAGE, "endpoint_url": ""}
    _stdin(monkeypatch, DUMP)
    out = io.StringIO()

    call_command("sauvegarde_envoyer", stdout=out)

    assert "non configurée" in out.getvalue()


def test_liste_les_plus_recentes_dabord(s3):
    def objects(*items):
        return {"Contents": [{"Key": k, "Size": 4096, "LastModified": d} for k, d in items]}

    s3.add_response(
        "list_objects_v2",
        objects(
            ("quotidien/sugu-2026-10-14.dump", datetime(2026, 10, 14, 3, tzinfo=UTC)),
            ("quotidien/sugu-2026-10-15.dump", datetime(2026, 10, 15, 3, tzinfo=UTC)),
        ),
        {"Bucket": "sugu-backups", "Prefix": "quotidien/"},
    )
    s3.add_response(
        "list_objects_v2",
        objects(("mensuel/sugu-2026-10.dump", datetime(2026, 10, 1, 3, tzinfo=UTC))),
        {"Bucket": "sugu-backups", "Prefix": "mensuel/"},
    )
    out = io.StringIO()

    call_command("sauvegarde_lister", stdout=out)

    lines = out.getvalue().splitlines()
    assert [line.split()[0] for line in lines] == [
        "quotidien/sugu-2026-10-15.dump",
        "quotidien/sugu-2026-10-14.dump",
        "mensuel/sugu-2026-10.dump",
    ]


def test_telechargement_sur_la_sortie_standard(s3, monkeypatch):
    key = "quotidien/sugu-2026-10-15.dump"
    s3.add_response(
        "get_object",
        {"Body": StreamingBody(io.BytesIO(DUMP), len(DUMP))},
        {"Bucket": "sugu-backups", "Key": key},
    )
    stdout = io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, "stdout", stdout)

    call_command("sauvegarde_telecharger", key)

    assert stdout.buffer.getvalue() == DUMP


def test_check_deploy_signale_les_sauvegardes_non_configurees(settings, configured):
    assert check_backups(None) == []

    settings.BACKUP_STORAGE = {**settings.BACKUP_STORAGE, "secret_key": ""}

    assert [message.id for message in check_backups(None)] == ["sugu.W004"]


@pytest.mark.skipif(not shutil.which("bash"), reason="bash absent")
@pytest.mark.parametrize("script", ["backup.sh", "restore.sh"])
def test_scripts_sans_erreur_de_syntaxe(script):
    result = subprocess.run(
        ["bash", "-n", f"scripts/{script}"], cwd=ROOT, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
