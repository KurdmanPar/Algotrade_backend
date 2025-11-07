import pytest
from rest_framework.test import APIClient
from trading.models import User
from django.urls import reverse

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_user_list(api_client):
    url = reverse('user-list')
    response = api_client.get(url)
    assert response.status_code == 200
