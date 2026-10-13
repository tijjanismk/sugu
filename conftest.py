import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _vide_le_cache():
    """Les compteurs de limitation de débit vivent dans le cache : un test ne doit pas
    hériter des tentatives du précédent."""
    cache.clear()
    yield
    cache.clear()
