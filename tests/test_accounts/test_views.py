# tests/test_accounts/test_views.py

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import CustomUser, UserProfile, UserSession, UserAPIKey

pytestmark = pytest.mark.django_db

class TestRegistrationView:
    """
    Test suite for the user registration endpoint.
    """
    url = reverse('accounts:register')

    def test_user_registration_success(self, api_client):
        """Test successful user registration."""
        data = {
            'email': 'newuser@example.com',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'username_display': 'newuser',
            'profile': {
                'first_name': 'New',
                'last_name': 'User'
            }
        }
        response = api_client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert CustomUser.objects.filter(email='newuser@example.com').exists()
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_user_registration_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            'email': 'newuser@example.com',
            'password': 'strongpass123',
            'password_confirm': 'differentpass',
        }
        response = api_client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CustomUser.objects.filter(email='newuser@example.com').exists()

class TestLoginView:
    """
    Test suite for the user login endpoint.
    """
    url = reverse('accounts:login')

    def test_user_login_success(self, api_client, CustomUserFactory):
        """Test successful user login."""
        user = CustomUserFactory(password='testpass123')
        data = {
            'email': user.email,
            'password': 'testpass123'
        }
        response = api_client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

        # Check if last login info is updated (now handled by service, but model should reflect)
        user.refresh_from_db()
        assert user.last_login_at is not None

    def test_user_login_invalid_credentials(self, api_client, CustomUserFactory):
        """Test login with invalid credentials."""
        user = CustomUserFactory(password='testpass123')
        data = {
            'email': user.email,
            'password': 'wrongpass'
        }
        response = api_client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.data

    def test_user_login_locked_account(self, api_client, CustomUserFactory):
        """Test login with a locked account."""
        user = CustomUserFactory(locked=True, password='testpass123')
        data = {
            'email': user.email,
            'password': 'testpass123'
        }
        response = api_client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Assuming error message is handled in serializer or view
        # assert 'locked' in response.data['non_field_errors'][0].lower()

class TestProfileView:
    """
    Test suite for the user profile endpoint.
    """
    url = reverse('accounts:profile')

    def test_get_profile_unauthorized(self, api_client):
        """Test getting profile without authentication."""
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_success(self, authenticated_api_client):
        """Test getting profile for an authenticated user."""
        client, user = authenticated_api_client
        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert 'profile' in response.data
        # Check for backup_codes in response
        assert 'backup_codes' in response.data['profile']

    def test_patch_profile_success(self, authenticated_api_client):
        """Test updating user and profile data."""
        client, user = authenticated_api_client
        data = {
            'first_name': 'Updated',
            'profile': {
                'display_name': 'UpdatedUser',
                'preferred_base_currency': 'USD',
                'allowed_ips': '192.168.1.1,10.0.0.0/8' # Valid IPs
            }
        }
        response = client.patch(self.url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        user.profile.refresh_from_db()

        assert user.first_name == 'Updated'
        assert user.profile.display_name == 'UpdatedUser'
        assert user.profile.preferred_base_currency == 'USD'
        assert user.profile.allowed_ips == '192.168.1.1,10.0.0.0/8'

    def test_patch_profile_invalid_allowed_ips(self, authenticated_api_client):
        """Test updating profile with invalid allowed_ips."""
        client, user = authenticated_api_client
        data = {
            'profile': {
                'allowed_ips': 'invalid_ip,10.0.0.0/8' # Invalid IP
            }
        }
        response = client.patch(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Check for validation error related to allowed_ips
        assert 'profile' in response.data
        assert 'allowed_ips' in response.data['profile']

class TestUserAPIKeysView:
    """
    Test suite for the user API keys management endpoint.
    """
    url = reverse('accounts:api_keys')

    def test_create_api_key_success(self, authenticated_api_client):
        """Test creating a new API key."""
        client, user = authenticated_api_client
        data = {
            'name': 'My Test Key',
            'permissions': {'read': True, 'trade': True}
        }
        response = client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert UserAPIKey.objects.filter(user=user, name='My Test Key').exists()
        assert 'key_preview' in response.data  # Should return preview, not full key

    def test_list_api_keys_success(self, authenticated_api_client, UserAPIKeyFactory):
        """Test listing user's API keys."""
        client, user = authenticated_api_client
        # Create a few API keys for the user
        UserAPIKeyFactory.create_batch(3, user=user)

        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_delete_api_key_success(self, authenticated_api_client, UserAPIKeyFactory):
        """Test deleting an API key."""
        client, user = authenticated_api_client
        api_key = UserAPIKeyFactory(user=user)
        url = reverse('accounts:api_key_detail', kwargs={'api_key_id': api_key.id})

        response = client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserAPIKey.objects.filter(id=api_key.id).exists()

# --- تست‌های جدید ---
class TestUserSessionsView:
    """
    Test suite for the user sessions management endpoint.
    """
    url = reverse('accounts:sessions')

    def test_list_sessions_unauthorized(self, api_client):
        """Test listing sessions without authentication."""
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_sessions_success(self, authenticated_api_client, UserSessionFactory):
        """Test listing user's sessions."""
        client, user = authenticated_api_client
        # Create a few sessions for the user
        UserSessionFactory.create_batch(2, user=user)

        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        # Check for is_current field in response
        assert 'is_current' in response.data[0]

# Add more view tests as needed for other endpoints like 2FA, KYC, etc.