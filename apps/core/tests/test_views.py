import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_affiche_le_nom_du_site(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert "Sugu" in response.content.decode()


@pytest.mark.django_db
def test_health_repond_ok(client):
    response = client.get(reverse("core:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
