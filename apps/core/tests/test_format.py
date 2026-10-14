"""Formats de la charte : prix en FCFA et dates relatives (design/README.md, « Contenu »)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.core.templatetags.sugu_format import fcfa, relative_date, thousands

BAMAKO = ZoneInfo("Africa/Bamako")
NOW = datetime(2026, 10, 14, 15, 0, tzinfo=BAMAKO)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(45000, "45 000\xa0FCFA"), (4500000, "4 500 000\xa0FCFA"), (0, "0\xa0FCFA"),
     (None, "À débattre")],
)  # fmt: skip
def test_fcfa(value, expected):
    assert fcfa(value) == expected


def test_milliers_sans_unite():
    assert thousands(55000) == "55 000"
    assert thousands(None) == ""


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(timedelta(seconds=20), "à l'instant"), (timedelta(minutes=5), "il y a 5 min"),
     (timedelta(hours=2), "il y a 2 h"), (timedelta(hours=20), "hier"),
     (timedelta(days=3), "il y a 3 j"), (timedelta(days=6, hours=1), "il y a 6 j"),
     (timedelta(days=12), "2 oct.")],
)  # fmt: skip
def test_date_relative(delta, expected):
    assert relative_date(NOW - delta, NOW) == expected


def test_date_relative_d_une_autre_annee():
    assert relative_date(datetime(2025, 8, 3, tzinfo=BAMAKO), NOW) == "3 août 2025"


def test_date_absente():
    assert relative_date(None) == ""
