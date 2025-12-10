# tests/conftest.py

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Import all factories to make them available to pytest-factoryboy
from tests.factories import CustomUserFactory, UserProfileFactory

# This fixture provides a Django test client for making API requests.
@pytest.fixture
def api_client():
    return APIClient()

# This fixture provides an authenticated API client.
# It creates a user and logs them in, returning the client with auth headers set.
@pytest.fixture
def authenticated_api_client(api_client, CustomUserFactory):
    user = CustomUserFactory()
    refresh = RefreshToken.for_user(user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    return api_client, user

# This fixture provides an authenticated superuser client.
@pytest.fixture
def authenticated_superuser_client(api_client, CustomUserFactory):
    superuser = CustomUserFactory(is_superuser=True, is_staff=True)
    refresh = RefreshToken.for_user(superuser)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
    )
    return api_client, superuser

# A simple fixture to get the custom user model
@pytest.fixture
def User():
    return get_user_model()