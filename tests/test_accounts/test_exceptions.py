# tests/test_accounts/test_exceptions.py

import pytest
from rest_framework.exceptions import APIException
from apps.accounts.exceptions import (
    AccountLockedError,
    RateLimitExceededError,
    TwoFactorRequiredError,
    KYCRequiredError,
    InsufficientPermissionsError,
    InvalidAPIKeyError,
    SessionExpiredError,
)

pytestmark = pytest.mark.django_db # Not strictly needed for exceptions, but included for consistency

class TestAccountExceptions:
    """
    Test suite for the custom exceptions in accounts app.
    """

    def test_account_locked_error(self):
        """Test the AccountLockedError exception."""
        exc = AccountLockedError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 423
        assert exc.default_detail == 'This account is currently locked.'

    def test_rate_limit_exceeded_error(self):
        """Test the RateLimitExceededError exception."""
        exc = RateLimitExceededError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 429
        assert exc.default_detail == 'Rate limit exceeded. Please try again later.'

    def test_two_factor_required_error(self):
        """Test the TwoFactorRequiredError exception."""
        exc = TwoFactorRequiredError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 401
        assert exc.default_detail == 'Two-factor authentication is required for this action.'

    def test_kyc_required_error(self):
        """Test the KYCRequiredError exception."""
        exc = KYCRequiredError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 403
        assert exc.default_detail == 'KYC verification is required for this action.'

    def test_insufficient_permissions_error(self):
        """Test the InsufficientPermissionsError exception."""
        exc = InsufficientPermissionsError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 403
        assert exc.default_detail == 'You do not have sufficient permissions to perform this action.'

    def test_invalid_api_key_error(self):
        """Test the InvalidAPIKeyError exception."""
        exc = InvalidAPIKeyError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 401
        assert exc.default_detail == 'The provided API key is invalid or inactive.'

    def test_session_expired_error(self):
        """Test the SessionExpiredError exception."""
        exc = SessionExpiredError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 401
        assert exc.default_detail == 'Your session has expired. Please log in again.'
