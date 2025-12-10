# apps/accounts/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

class AccountLockedError(APIException):
    status_code = 423  # Locked
    default_detail = _('This account is currently locked.')
    default_code = 'account_locked'

class RateLimitExceededError(APIException):
    status_code = 429  # Too Many Requests
    default_detail = _('Rate limit exceeded. Please try again later.')
    default_code = 'rate_limit_exceeded'

class TwoFactorRequiredError(APIException):
    status_code = 401  # Unauthorized
    default_detail = _('Two-factor authentication is required for this action.')
    default_code = 'two_factor_required'

class KYCRequiredError(APIException):
    status_code = 403  # Forbidden
    default_detail = _('KYC verification is required for this action.')
    default_code = 'kyc_required'

class InsufficientPermissionsError(APIException):
    status_code = 403  # Forbidden
    default_detail = _('You do not have sufficient permissions to perform this action.')
    default_code = 'insufficient_permissions'

class InvalidAPIKeyError(APIException):
    status_code = 401  # Unauthorized
    default_detail = _('The provided API key is invalid or inactive.')
    default_code = 'invalid_api_key'

class SessionExpiredError(APIException):
    status_code = 401  # Unauthorized
    default_detail = _('Your session has expired. Please log in again.')
    default_code = 'session_expired'
