# tests/test_accounts/test_managers.py

import pytest
from django.utils import timezone
from apps.accounts.models import CustomUser, UserAPIKey
from apps.accounts.managers import UserAPIKeyManager
from datetime import timedelta

pytestmark = pytest.mark.django_db

class TestAccountManagers:
    """
    Test suite for the custom managers in accounts app.
    """

    def test_user_api_key_manager_active(self, UserAPIKeyFactory, CustomUserFactory):
        """Test the active() method of UserAPIKeyManager."""
        user = CustomUserFactory()
        active_key = UserAPIKeyFactory(user=user, is_active=True)
        inactive_key = UserAPIKeyFactory(user=user, is_active=False)

        active_keys = UserAPIKey.objects.active()

        assert active_key in active_keys
        assert inactive_key not in active_keys

    def test_user_api_key_manager_expired(self, UserAPIKeyFactory, CustomUserFactory):
        """Test the expired() method of UserAPIKeyManager."""
        user = CustomUserFactory()
        expired_key = UserAPIKeyFactory(
            user=user,
            is_active=True,
            expires_at=timezone.now() - timedelta(days=1)
        )
        active_key = UserAPIKeyFactory(
            user=user,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=1)
        )
        inactive_expired_key = UserAPIKeyFactory(
            user=user,
            is_active=False,
            expires_at=timezone.now() - timedelta(days=1)
        )

        expired_keys = UserAPIKey.objects.expired()

        assert expired_key in expired_keys
        assert active_key not in expired_keys
        assert inactive_expired_key not in expired_keys # Only active and expired

    def test_user_api_key_manager_for_user(self, UserAPIKeyFactory, CustomUserFactory):
        """Test the for_user() method of UserAPIKeyManager."""
        user1 = CustomUserFactory()
        user2 = CustomUserFactory()
        key_user1 = UserAPIKeyFactory(user=user1)
        key_user2 = UserAPIKeyFactory(user=user2)

        keys_user1 = UserAPIKey.objects.for_user(user1)

        assert key_user1 in keys_user1
        assert key_user2 not in keys_user1

    def test_user_api_key_manager_valid_for_user(self, UserAPIKeyFactory, CustomUserFactory):
        """Test the valid_for_user() method of UserAPIKeyManager."""
        user = CustomUserFactory()
        valid_key_no_expiry = UserAPIKeyFactory(user=user, is_active=True, expires_at=None)
        valid_key_future_expiry = UserAPIKeyFactory(
            user=user,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=1)
        )
        expired_key = UserAPIKeyFactory(
            user=user,
            is_active=True,
            expires_at=timezone.now() - timedelta(days=1)
        )
        inactive_key = UserAPIKeyFactory(user=user, is_active=False)

        valid_keys = UserAPIKey.objects.valid_for_user(user)

        assert valid_key_no_expiry in valid_keys
        assert valid_key_future_expiry in valid_keys
        assert expired_key not in valid_keys
        assert inactive_key not in valid_keys
