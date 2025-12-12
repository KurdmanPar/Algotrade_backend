# tests/test_core/test_exceptions.py

import pytest
from rest_framework.exceptions import APIException
from apps.core.exceptions import (
    CoreSystemException,
    DataIntegrityException,
    ConfigurationError,
    SecurityException,
    AuditLogError,
    CacheError,
    CacheMissError,
    CacheSyncError,
    MessagingError,
    MessageSendError,
    MessageReceiveError,
    MessageParseError,
    RateLimitExceededError,
    InvalidCredentialsError,
    InsufficientPermissionsError,
    # سایر استثناهای سفارشی core
)

#pytestmark = pytest.mark.django_db # Exceptions تست نیازی به پایگاه داده ندارد


class TestCoreSystemException:
    """
    Tests for the CoreSystemException base class.
    """
    def test_core_system_exception_inherits_from_api_exception(self):
        """Test that CoreSystemException inherits from DRF's APIException."""
        exc = CoreSystemException()
        assert isinstance(exc, APIException)

    def test_core_system_exception_default_status_code(self):
        """Test the default status code."""
        exc = CoreSystemException()
        assert exc.status_code == 500

    def test_core_system_exception_default_detail(self):
        """Test the default detail message."""
        exc = CoreSystemException()
        assert exc.default_detail == 'An error occurred within the core system.'

    def test_core_system_exception_default_code(self):
        """Test the default error code."""
        exc = CoreSystemException()
        assert exc.default_code == 'core_system_error'

    def test_core_system_exception_custom_detail(self):
        """Test creating an exception with a custom detail."""
        custom_detail = "A specific error occurred."
        exc = CoreSystemException(detail=custom_detail)
        assert exc.detail == custom_detail


class TestDataIntegrityException:
    """
    Tests for the DataIntegrityException.
    """
    def test_data_integrity_exception_inherits_from_core_system_exception(self):
        exc = DataIntegrityException()
        assert isinstance(exc, CoreSystemException)

    def test_data_integrity_exception_status_code(self):
        exc = DataIntegrityException()
        assert exc.status_code == 500

    def test_data_integrity_exception_detail(self):
        exc = DataIntegrityException()
        assert exc.default_detail == 'Data integrity violation detected.'


class TestConfigurationError:
    """
    Tests for the ConfigurationError.
    """
    def test_configuration_error_inherits_from_core_system_exception(self):
        exc = ConfigurationError()
        assert isinstance(exc, CoreSystemException)

    def test_configuration_error_status_code(self):
        exc = ConfigurationError()
        assert exc.status_code == 500

    def test_configuration_error_detail(self):
        exc = ConfigurationError()
        assert exc.default_detail == 'A configuration error occurred in the core system.'


class TestSecurityException:
    """
    Tests for the SecurityException.
    """
    def test_security_exception_inherits_from_core_system_exception(self):
        exc = SecurityException()
        assert isinstance(exc, CoreSystemException)

    def test_security_exception_status_code(self):
        exc = SecurityException()
        assert exc.status_code == 403 # Forbidden

    def test_security_exception_detail(self):
        exc = SecurityException()
        assert exc.default_detail == 'A security error occurred.'


class TestAuditLogError:
    """
    Tests for the AuditLogError.
    """
    def test_audit_log_error_inherits_from_core_system_exception(self):
        exc = AuditLogError()
        assert isinstance(exc, CoreSystemException)

    def test_audit_log_error_status_code(self):
        exc = AuditLogError()
        assert exc.status_code == 500

    def test_audit_log_error_detail(self):
        exc = AuditLogError()
        assert exc.default_detail == 'An error occurred while logging an audit event.'


class TestCacheError:
    """
    Tests for the CacheError.
    """
    def test_cache_error_inherits_from_core_system_exception(self):
        exc = CacheError()
        assert isinstance(exc, CoreSystemException)

    def test_cache_error_status_code(self):
        exc = CacheError()
        assert exc.status_code == 500

    def test_cache_error_detail(self):
        exc = CacheError()
        assert exc.default_detail == 'An error occurred with the caching system.'


class TestCacheMissError:
    """
    Tests for the CacheMissError.
    """
    def test_cache_miss_error_inherits_from_cache_error(self):
        exc = CacheMissError()
        assert isinstance(exc, CacheError)

    def test_cache_miss_error_status_code(self):
        exc = CacheMissError()
        assert exc.status_code == 404 # Not Found

    def test_cache_miss_error_detail(self):
        exc = CacheMissError()
        assert exc.default_detail == 'The requested item was not found in the cache.'


class TestCacheSyncError:
    """
    Tests for the CacheSyncError.
    """
    def test_cache_sync_error_inherits_from_cache_error(self):
        exc = CacheSyncError()
        assert isinstance(exc, CacheError)

    def test_cache_sync_error_status_code(self):
        exc = CacheSyncError()
        assert exc.status_code == 500

    def test_cache_sync_error_detail(self):
        exc = CacheSyncError()
        assert exc.default_detail == 'An error occurred while synchronizing the cache.'


class TestMessagingError:
    """
    Tests for the MessagingError.
    """
    def test_messaging_error_inherits_from_core_system_exception(self):
        exc = MessagingError()
        assert isinstance(exc, CoreSystemException)

    def test_messaging_error_status_code(self):
        exc = MessagingError()
        assert exc.status_code == 500

    def test_messaging_error_detail(self):
        exc = MessagingError()
        assert exc.default_detail == 'An error occurred in the messaging system.'


class TestMessageSendError:
    """
    Tests for the MessageSendError.
    """
    def test_message_send_error_inherits_from_messaging_error(self):
        exc = MessageSendError()
        assert isinstance(exc, MessagingError)

    def test_message_send_error_status_code(self):
        exc = MessageSendError()
        assert exc.status_code == 500

    def test_message_send_error_detail(self):
        exc = MessageSendError()
        assert exc.default_detail == 'Failed to send message.'


class TestMessageReceiveError:
    """
    Tests for the MessageReceiveError.
    """
    def test_message_receive_error_inherits_from_messaging_error(self):
        exc = MessageReceiveError()
        assert isinstance(exc, MessagingError)

    def test_message_receive_error_status_code(self):
        exc = MessageReceiveError()
        assert exc.status_code == 500

    def test_message_receive_error_detail(self):
        exc = MessageReceiveError()
        assert exc.default_detail == 'Failed to receive message.'


class TestMessageParseError:
    """
    Tests for the MessageParseError.
    """
    def test_message_parse_error_inherits_from_messaging_error(self):
        exc = MessageParseError()
        assert isinstance(exc, MessagingError)

    def test_message_parse_error_status_code(self):
        exc = MessageParseError()
        assert exc.status_code == 400 # Bad Request

    def test_message_parse_error_detail(self):
        exc = MessageParseError()
        assert exc.default_detail == 'Failed to parse received message.'


class TestRateLimitExceededError:
    """
    Tests for the RateLimitExceededError.
    """
    def test_rate_limit_exceeded_error_inherits_from_api_exception(self):
        exc = RateLimitExceededError()
        assert isinstance(exc, APIException)

    def test_rate_limit_exceeded_error_status_code(self):
        exc = RateLimitExceededError()
        assert exc.status_code == 429 # Too Many Requests

    def test_rate_limit_exceeded_error_detail(self):
        exc = RateLimitExceededError()
        assert exc.default_detail == 'Rate limit exceeded.'


class TestInvalidCredentialsError:
    """
    Tests for the InvalidCredentialsError.
    """
    def test_invalid_credentials_error_inherits_from_api_exception(self):
        exc = InvalidCredentialsError()
        assert isinstance(exc, APIException)

    def test_invalid_credentials_error_status_code(self):
        exc = InvalidCredentialsError()
        assert exc.status_code == 401 # Unauthorized

    def test_invalid_credentials_error_detail(self):
        exc = InvalidCredentialsError()
        assert exc.default_detail == 'Invalid API credentials provided.'


class TestInsufficientPermissionsError:
    """
    Tests for the InsufficientPermissionsError.
    """
    def test_insufficient_permissions_error_inherits_from_api_exception(self):
        exc = InsufficientPermissionsError()
        assert isinstance(exc, APIException)

    def test_insufficient_permissions_error_status_code(self):
        exc = InsufficientPermissionsError()
        assert exc.status_code == 403 # Forbidden

    def test_insufficient_permissions_error_detail(self):
        exc = InsufficientPermissionsError()
        assert exc.default_detail == 'You do not have sufficient permissions to perform this action.'

# --- تست سایر استثناهای سفارشی ---
# می‌توانید تست‌هایی برای سایر استثناهایی که در apps/core/exceptions.py تعریف می‌کنید بنویسید
# مثلاً اگر InstrumentValidationError وجود داشت:
# class TestInstrumentValidationError:
#     def test_logic(self):
#         with pytest.raises(InstrumentValidationError):
#             raise InstrumentValidationError("Test error")

logger.info("Core exception tests loaded successfully.")
