# tests/test_accounts/test_services.py

import pytest
from django.utils import timezone
from apps.accounts.models import CustomUser, UserProfile, UserSession, UserAPIKey
from apps.accounts.services import AccountService
from apps.accounts.helpers import validate_ip_list, is_ip_in_allowed_list
from unittest.mock import patch

pytestmark = pytest.mark.django_db

class TestAccountService:
    """
    Test suite for the AccountService class.
    """

    def test_create_user_with_profile(self, CustomUserFactory):
        """Test creating a user and profile using the service."""
        validated_data = {
            'email': 'newservice@example.com',
            'password': 'password123',
            'first_name': 'Service',
            'last_name': 'User',
            'username': 'serviceuser'
        }
        user = AccountService.create_user_with_profile(validated_data)
        assert user.email == 'newservice@example.com'
        assert hasattr(user, 'profile')
        assert user.profile.first_name == 'Service'

    def test_update_user_profile(self, UserProfileFactory):
        """Test updating a user profile using the service."""
        profile = UserProfileFactory(first_name='Old', display_name='OldUser')
        user = profile.user
        profile_data = {'first_name': 'New', 'display_name': 'NewUser'}

        updated_profile = AccountService.update_user_profile(user, profile_data)

        assert updated_profile.first_name == 'New'
        assert updated_profile.display_name == 'NewUser'

    def test_update_user_profile_validates_ips(self, UserProfileFactory):
        """Test updating profile validates allowed_ips using helper."""
        profile = UserProfileFactory()
        user = profile.user
        # This should succeed
        profile_data_valid = {'allowed_ips': '192.168.1.1,10.0.0.0/8'}
        updated_profile = AccountService.update_user_profile(user, profile_data_valid)
        assert updated_profile.allowed_ips == '192.168.1.1,10.0.0.0/8'

        # This should raise ValidationError
        profile_data_invalid = {'allowed_ips': 'invalid_ip,10.0.0.0/8'}
        with pytest.raises(Exception): # ValidationError
            AccountService.update_user_profile(user, profile_data_invalid)

    def test_create_or_update_session(self, api_client, CustomUserFactory):
        """Test creating or updating a session using the service."""
        user = CustomUserFactory()
        request = api_client.get('/').wsgi_request # Mock request object
        request.session.session_key = 'test-session-key'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'

        session = AccountService.create_or_update_session(user, request)

        assert session.user == user
        assert session.session_key == 'test-session-key'
        assert session.is_active is True

    def test_deactivate_session(self, UserSessionFactory):
        """Test deactivating a session using the service."""
        session = UserSessionFactory(is_active=True)
        user = session.user
        session_key = session.session_key

        success = AccountService.deactivate_session(user, session_key)

        assert success is True
        session.refresh_from_db()
        assert session.is_active is False

    def test_update_user_login_info(self, CustomUserFactory):
        """Test updating user login info using the service."""
        user = CustomUserFactory()
        request = type('MockRequest', (), {'META': {'REMOTE_ADDR': '127.0.0.1'}})()

        AccountService.update_user_login_info(user, request)

        user.refresh_from_db()
        assert user.last_login_at is not None
        assert user.last_login_ip == '127.0.0.1'

    def test_create_api_key(self, CustomUserFactory):
        """Test creating an API key using the service."""
        user = CustomUserFactory()
        name = 'Test Key'
        permissions = {'read': True, 'trade': False}

        api_key = AccountService.create_api_key(user, name, permissions)

        assert api_key.user == user
        assert api_key.name == name
        assert api_key.permissions == permissions

    def test_revoke_api_key(self, UserAPIKeyFactory):
        """Test revoking an API key using the service."""
        api_key = UserAPIKeyFactory()
        user = api_key.user
        api_key_id = api_key.id

        success = AccountService.revoke_api_key(user, api_key_id)

        assert success is True
        assert not UserAPIKey.objects.filter(id=api_key_id).exists()

    def test_verify_api_key(self, UserAPIKeyFactory):
        """Test verifying an API key using the service."""
        api_key_obj = UserAPIKeyFactory(is_active=True)
        key_string = str(api_key_obj.key)

        is_valid, user, key_obj = AccountService.verify_api_key(key_string)

        assert is_valid is True
        assert user == api_key_obj.user
        assert key_obj == api_key_obj

    def test_verify_api_key_inactive(self, UserAPIKeyFactory):
        """Test verifying an inactive API key."""
        api_key_obj = UserAPIKeyFactory(is_active=False)
        key_string = str(api_key_obj.key)

        is_valid, user, key_obj = AccountService.verify_api_key(key_string)

        assert is_valid is False
        assert user is None
        assert key_obj is None

    def test_update_user_kyc_status(self, UserProfileFactory):
        """Test updating KYC status using the service."""
        profile = UserProfileFactory()
        user = profile.user

        updated_profile = AccountService.update_user_kyc_status(user, submitted=True)

        assert updated_profile.kyc_submitted_at is not None

    def test_enable_2fa(self, UserProfileFactory):
        """Test enabling 2FA using the service."""
        profile = UserProfileFactory(backup_codes=['CODE1234', 'CODE5678'])
        user = profile.user

        success = AccountService.enable_2fa(user, 'CODE1234')

        assert success is True
        profile.refresh_from_db()
        assert profile.two_factor_enabled is True
        assert profile.backup_codes == []

    def test_disable_2fa(self, UserProfileFactory):
        """Test disabling 2FA using the service."""
        profile = UserProfileFactory(two_factor_enabled=True)
        user = profile.user

        success = AccountService.disable_2fa(user)

        assert success is True
        profile.refresh_from_db()
        assert profile.two_factor_enabled is False

    def test_check_user_ip_access(self, UserProfileFactory):
        """Test checking user IP access using the service and helper."""
        profile = UserProfileFactory(allowed_ips='192.168.1.1,10.0.0.0/8')
        user = profile.user

        # Test allowed IP
        is_allowed = AccountService.check_user_ip_access(user, '192.168.1.1')
        assert is_allowed is True

        # Test non-allowed IP
        is_allowed = AccountService.check_user_ip_access(user, '1.1.1.1')
        assert is_allowed is False

        # Test IP in CIDR block
        is_allowed = AccountService.check_user_ip_access(user, '10.0.0.100')
        assert is_allowed is True
