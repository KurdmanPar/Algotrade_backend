# tests/test_accounts/test_models.py

import pytest
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import CustomUser, UserProfile, UserAPIKey
from apps.accounts.helpers import validate_ip_list
import logging

# We use the factories defined in conftest.py
# from tests.factories import CustomUserFactory, UserProfileFactory, UserAPIKeyFactory

pytestmark = pytest.mark.django_db

class TestCustomUserModel:
    """
    Test suite for the CustomUser model.
    """

    def test_create_user(self, CustomUserFactory):
        """Test creating a standard user via factory."""
        user = CustomUserFactory()
        assert user.email is not None
        assert user.username_display is not None
        assert user.is_active is True
        assert user.is_demo is True
        assert user.check_password('password123')  # Default password from factory

    def test_user_str_representation(self, CustomUserFactory):
        """Test the __str__ method of CustomUser."""
        user = CustomUserFactory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_check_account_lock_when_locked(self, CustomUserFactory):
        """Test check_account_lock returns True for a locked account."""
        user = CustomUserFactory(locked=True)
        assert user.check_account_lock() is True

    def test_check_account_lock_when_expired(self, CustomUserFactory):
        """Test check_account_lock returns False for an expired lock."""
        user = CustomUserFactory(
            is_locked=True,
            locked_until=timezone.now() - timedelta(minutes=1)
        )
        assert user.check_account_lock() is False

    def test_increment_failed_login_attempts(self, CustomUserFactory):
        """Test incrementing failed login attempts."""
        user = CustomUserFactory()
        initial_attempts = user.failed_login_attempts
        user.increment_failed_login_attempts()
        user.refresh_from_db()
        assert user.failed_login_attempts == initial_attempts + 1

    def test_lock_after_max_failed_attempts(self, CustomUserFactory):
        """Test that account locks after 5 failed attempts."""
        user = CustomUserFactory()
        for _ in range(5):
            user.increment_failed_login_attempts()

        user.refresh_from_db()
        assert user.is_locked is True
        assert user.locked_until is not None

    def test_reset_failed_login_attempts(self, CustomUserFactory):
        """Test resetting failed login attempts unlocks the account."""
        user = CustomUserFactory(locked=True)
        user.reset_failed_login_attempts()

        user.refresh_from_db()
        assert user.failed_login_attempts == 0
        assert user.is_locked is False
        assert user.locked_until is None

class TestUserProfileModel:
    """
    Test suite for the UserProfile model.
    """

    def test_create_profile(self, UserProfileFactory):
        """Test creating a user profile via factory."""
        profile = UserProfileFactory()
        assert profile.user is not None
        assert profile.first_name is not None
        assert profile.preferred_base_currency == "IRT"
        # تست فیلد جدید backup_codes
        assert profile.backup_codes == []

    def test_profile_str_representation(self, UserProfileFactory):
        """Test the __str__ method of UserProfile."""
        profile = UserProfileFactory(user__email="test@example.com")
        assert str(profile) == "test@example.com Profile"

    def test_get_full_name(self, UserProfileFactory):
        """Test the get_full_name method."""
        profile = UserProfileFactory(first_name="John", last_name="Doe")
        assert profile.get_full_name() == "John Doe"

    def test_is_kyc_pending(self, UserProfileFactory):
        """Test is_kyc_pending status."""
        profile = UserProfileFactory(
            kyc_submitted_at=timezone.now()
        )
        assert profile.is_kyc_pending() is True
        assert profile.is_kyc_rejected() is False

        # After verification
        profile.kyc_verified_at = timezone.now()
        profile.save()
        assert profile.is_kyc_pending() is False

    def test_clean_validates_allowed_ips(self, UserProfileFactory):
        """Test the clean method validates allowed_ips."""
        profile = UserProfileFactory(allowed_ips="192.168.1.1,10.0.0.0/8")
        profile.full_clean() # Should not raise ValidationError
        assert profile.allowed_ips == "192.168.1.1,10.0.0.0/8"

    def test_clean_rejects_invalid_allowed_ips(self, UserProfileFactory):
        """Test the clean method rejects invalid allowed_ips."""
        profile = UserProfileFactory(allowed_ips="invalid_ip,10.0.0.0/8")
        with pytest.raises(Exception): # ValidationError یا ValueError
            profile.full_clean() # Should raise ValidationError

class TestUserAPIKeyModel:
    """
    Test suite for the UserAPIKey model.
    """

    def test_create_api_key(self, UserAPIKeyFactory):
        """Test creating an API key via factory."""
        api_key = UserAPIKeyFactory()
        assert api_key.user is not None
        assert api_key.name is not None
        assert api_key.is_active is True

    def test_api_key_is_expired(self, UserAPIKeyFactory):
        """Test the is_expired method for an expired key."""
        api_key = UserAPIKeyFactory(
            expires_at=timezone.now() - timedelta(days=1)
        )
        assert api_key.is_expired() is True

    def test_api_key_is_not_expired(self, UserAPIKeyFactory):
        """Test the is_expired method for a valid key."""
        api_key = UserAPIKeyFactory(expires_at=None)
        assert api_key.is_expired() is False

    def test_is_rate_limited_simple_check(self, UserAPIKeyFactory):
        """Test the is_rate_limited method based on last used time."""
        api_key = UserAPIKeyFactory(last_used_at=timezone.now())
        # If used less than 1 sec ago, it should be limited (based on our updated logic)
        assert api_key.is_rate_limited() is True

        api_key.last_used_at = timezone.now() - timedelta(seconds=2)
        assert api_key.is_rate_limited() is False