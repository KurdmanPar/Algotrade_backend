# tests/test_accounts/test_urls.py

import pytest
from django.urls import reverse, resolve
from apps.accounts import views

pytestmark = pytest.mark.django_db # Not strictly needed for URLs, but included for consistency

class TestAccountURLs:
    """
    Test suite for the URL patterns in accounts app.
    """

    def test_register_url_resolves(self):
        """Test that the register URL resolves to the correct view."""
        url = reverse('accounts:register')
        assert resolve(url).func.view_class == views.RegistrationView

    def test_login_url_resolves(self):
        """Test that the login URL resolves to the correct view."""
        url = reverse('accounts:login')
        assert resolve(url).func.view_class == views.LoginView

    def test_logout_url_resolves(self):
        """Test that the logout URL resolves to the correct view."""
        url = reverse('accounts:logout')
        assert resolve(url).func.view_class == views.LogoutView

    def test_profile_url_resolves(self):
        """Test that the profile URL resolves to the correct view."""
        url = reverse('accounts:user_profile')
        assert resolve(url).func.view_class == views.ProfileView

    def test_api_keys_url_resolves(self):
        """Test that the API keys list/create URL resolves to the correct view."""
        url = reverse('accounts:api_keys')
        assert resolve(url).func.view_class == views.UserAPIKeysView

    def test_api_key_detail_url_resolves(self):
        """Test that the API key detail URL resolves to the correct view."""
        url = reverse('accounts:api_key_detail', kwargs={'api_key_id': '12345678-1234-5678-9012-123456789012'})
        assert resolve(url).func.view_class == views.UserAPIKeyDetailView

    def test_sessions_url_resolves(self):
        """Test that the sessions list URL resolves to the correct view."""
        url = reverse('accounts:sessions')
        assert resolve(url).func.view_class == views.UserSessionsView

    def test_session_detail_url_resolves(self):
        """Test that the session detail URL resolves to the correct view."""
        url = reverse('accounts:session_detail', kwargs={'session_id': '12345678-1234-5678-9012-123456789012'})
        assert resolve(url).func.view_class == views.UserSessionDetailView

    # Add more URL resolution tests for other endpoints like 2FA, KYC, etc.
