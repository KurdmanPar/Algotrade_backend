# tests/unit/test_views/test_instruments_views.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from tests.factories.instruments_factories import InstrumentFactory

@pytest.mark.django_db
def test_get_instruments_list():
    InstrumentFactory.create_batch(3)  # ایجاد 3 نمونه
    client = APIClient()
    response = client.get(reverse('instrument-list'))  # باید در urls.py نامگذاری شده باشد
    assert response.status_code == 200
    assert len(response.data) == 3