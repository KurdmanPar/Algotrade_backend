# apps/core/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

# --- Base Exceptions for the Core App ---

class CoreSystemException(APIException):
    """
    Base exception class for all errors originating from the core system.
    Inherits from DRF's APIException for consistent API error responses.
    """
    status_code = 500
    default_detail = _('An error occurred within the core system.')
    default_code = 'core_system_error'

class ConfigurationError(CoreSystemException):
    """
    Raised when a configuration setting for the core system is invalid or missing.
    """
    status_code = 500
    default_detail = _('A configuration error occurred in the core system.')
    default_code = 'configuration_error'

class SecurityException(CoreSystemException):
    """
    Base exception for security-related errors within the core system.
    """
    status_code = 403 # Forbidden
    default_detail = _('A security error occurred.')
    default_code = 'security_error'

class DataIntegrityException(CoreSystemException):
    """
    Raised when a violation of data integrity rules is detected within the core system.
    """
    status_code = 500
    default_detail = _('Data integrity violation detected in the core system.')
    default_code = 'data_integrity_error'

class AuditLogError(CoreSystemException):
    """
    Raised when an error occurs during audit logging operations.
    """
    status_code = 500
    default_detail = _('An error occurred while logging an audit event.')
    default_code = 'audit_log_error'

class CacheError(CoreSystemException):
    """
    Base exception for errors related to the caching system.
    """
    status_code = 500
    default_detail = _('An error occurred with the caching system.')
    default_code = 'cache_error'

class CacheMissError(CacheError):
    """
    Raised when a requested key is not found in the cache.
    """
    status_code = 404
    default_detail = _('The requested item was not found in the cache.')
    default_code = 'cache_miss'

class CacheSyncError(CacheError):
    """
    Raised when an error occurs while synchronizing cache entries with the database.
    """
    status_code = 500
    default_detail = _('An error occurred while synchronizing the cache.')
    default_code = 'cache_sync_error'

# --- Exceptions related to specific core models (if applicable) ---

class SystemSettingError(CoreSystemException):
    """
    Base exception for errors related to SystemSetting model.
    """
    status_code = 500
    default_detail = _('An error occurred with a system setting.')
    default_code = 'system_setting_error'

class InvalidSettingValueError(SystemSettingError):
    """
    Raised when a value assigned to a SystemSetting is invalid for its data type.
    """
    status_code = 400 # Bad Request
    default_detail = _('The provided value is invalid for this setting.')
    default_code = 'invalid_setting_value'

class SensitiveDataAccessError(SecurityException):
    """
    Raised when an unauthorized attempt is made to access sensitive data.
    """
    status_code = 403
    default_detail = _('Access to sensitive data is forbidden.')
    default_code = 'sensitive_data_access_error'

# --- Exceptions related to core services ---

class CoreServiceError(CoreSystemException):
    """
    Base exception for errors occurring within core services.
    """
    status_code = 500
    default_detail = _('An error occurred in a core service.')
    default_code = 'core_service_error'

class DataValidationError(CoreServiceError):
    """
    Raised when data validation fails within a core service.
    """
    status_code = 400
    default_detail = _('Data validation failed in a core service.')
    default_code = 'data_validation_error'

class DataProcessingError(CoreServiceError):
    """
    Raised when an error occurs during data processing within a core service.
    """
    status_code = 500
    default_detail = _('An error occurred while processing data in a core service.')
    default_code = 'data_processing_error'

# --- Exceptions related to core tasks (Celery) ---

class CoreTaskError(CoreSystemException):
    """
    Base exception for errors occurring within core Celery tasks.
    """
    status_code = 500
    default_detail = _('An error occurred in a core Celery task.')
    default_code = 'core_task_error'

class TaskRetryableError(CoreTaskError):
    """
    Raised within a task to indicate that the error is likely temporary and the task should be retried.
    """
    status_code = 500
    default_detail = _('A temporary error occurred in the task, marked for retry.')
    default_code = 'task_retryable_error'

class TaskNonRetryableError(CoreTaskError):
    """
    Raised within a task to indicate that the error is permanent and the task should not be retried.
    """
    status_code = 500
    default_detail = _('A permanent error occurred in the task, will not retry.')
    default_code = 'task_non_retryable_error'

# --- Exceptions related to core helpers/utils ---

class CoreHelperError(CoreSystemException):
    """
    Base exception for errors occurring within core utility functions.
    """
    status_code = 500
    default_detail = _('An error occurred in a core utility function.')
    default_code = 'core_helper_error'

class IPValidationError(CoreHelperError):
    """
    Raised when an IP address or CIDR block is invalid.
    """
    status_code = 400
    default_detail = _('Invalid IP address or CIDR block provided.')
    default_code = 'ip_validation_error'

class DataNormalizationError(CoreHelperError):
    """
    Raised when data normalization from an external source fails.
    """
    status_code = 502 # Bad Gateway (if source is faulty)
    default_detail = _('Failed to normalize data received from an external source.')
    default_code = 'data_normalization_error'

# --- Exceptions related to core permissions ---

class CorePermissionError(CoreSystemException):
    """
    Base exception for errors related to core permissions.
    """
    status_code = 403
    default_detail = _('A permission error occurred in the core system.')
    default_code = 'core_permission_error'

class OwnershipVerificationError(CorePermissionError):
    """
    Raised when ownership of an object cannot be verified.
    """
    status_code = 403
    default_detail = _('Ownership of the requested object could not be verified.')
    default_code = 'ownership_verification_error'

# --- Exceptions related to core mixins ---

class CoreMixinError(CoreSystemException):
    """
    Base exception for errors related to core mixins.
    """
    status_code = 500
    default_detail = _('An error occurred in a core mixin.')
    default_code = 'core_mixin_error'

# --- Exceptions related to core managers ---

class CoreManagerError(CoreSystemException):
    """
    Base exception for errors related to core managers.
    """
    status_code = 500
    default_detail = _('An error occurred in a core manager.')
    default_code = 'core_manager_error'

# --- Exceptions related to core signals ---

class CoreSignalError(CoreSystemException):
    """
    Base exception for errors related to core signals.
    """
    status_code = 500
    default_detail = _('An error occurred in a core signal handler.')
    default_code = 'core_signal_error'

# --- Exceptions related to core admin ---

class CoreAdminError(CoreSystemException):
    """
    Base exception for errors related to core admin interface.
    """
    status_code = 500
    default_detail = _('An error occurred in the core admin interface.')
    default_code = 'core_admin_error'

# --- مثال: یک استثنا مبتنی بر MAS ---
class AgentCommunicationError(CoreSystemException):
    """
    Raised when an error occurs in communication between agents within the MAS.
    """
    status_code = 502 # Bad Gateway یا 500 بسته به نوع خطا
    default_detail = _('An error occurred in communication with another agent.')
    default_code = 'agent_communication_error'

# --- مثال: یک استثنا مبتنی بر امنیت داده ---
class DataTamperingDetectedError(SecurityException):
    """
    Raised when tampering is detected in data integrity checks (e.g., checksum mismatch).
    """
    status_code = 400 # Bad Request یا 422 Unprocessable Entity
    default_detail = _('Data integrity check failed, possible tampering detected.')
    default_code = 'data_tampering_detected'

# --- مثال: یک استثنا مبتنی بر کارایی ---
class RateLimitExceededError(APIException):
    """
    Raised when a rate limit is exceeded. This can be used globally or within core services.
    Inherits directly from APIException as it's a common HTTP error.
    """
    status_code = 429  # Too Many Requests
    default_detail = _('Request rate limit exceeded.')
    default_code = 'rate_limit_exceeded'

# --- مثال: یک استثنا مبتنی بر اعتبارسنجی ورودی ---
class InputValidationError(CoreSystemException):
    """
    Raised for general input validation errors.
    """
    status_code = 400
    default_detail = _('Input validation failed.')
    default_code = 'input_validation_error'

class InvalidSymbolError(InputValidationError):
    """
    Raised when a trading symbol is invalid.
    """
    status_code = 400
    default_detail = _('Invalid trading symbol provided.')
    default_code = 'invalid_symbol'

class InvalidAmountError(InputValidationError):
    """
    Raised when an amount is invalid (e.g., negative).
    """
    status_code = 400
    default_detail = _('Invalid amount provided.')
    default_code = 'invalid_amount'

class InvalidPriceError(InputValidationError):
    """
    Raised when a price is invalid (e.g., negative).
    """
    status_code = 400
    default_detail = _('Invalid price provided.')
    default_code = 'invalid_price'

# --- مثال: استثناهای مرتبط با کش ---
class CacheKeyCollisionError(CacheError):
    """
    Raised when a cache key collision is detected (e.g., different data types using the same key).
    """
    status_code = 500
    default_detail = _('A cache key collision was detected.')
    default_code = 'cache_key_collision'

# --- مثال: استثناهای مرتبط با تنظیمات ---
class SettingLockedException(CoreSystemException):
    """
    Raised when an attempt is made to modify a locked system setting.
    """
    status_code = 403
    default_detail = _('This system setting is locked and cannot be modified.')
    default_code = 'setting_locked'

# --- مثال: استثناهای مرتبط با مدل‌های BaseOwnedModel ---
class CannotChangeOwnerError(CoreSystemException):
    """
    Raised when an attempt is made to change the owner of an object after creation.
    """
    status_code = 400
    default_detail = _('The owner of this object cannot be changed after creation.')
    default_code = 'cannot_change_owner'

# --- مثال: استثناهای مرتبط با فعال/غیرفعال کردن ---
class ResourceDeactivatedError(CoreSystemException):
    """
    Raised when an action is attempted on a resource that is not active.
    """
    status_code = 400
    default_detail = _('This resource is currently deactivated.')
    default_code = 'resource_deactivated'

# --- مثال: استثناهای مرتبط با دسترسی API ---
class APIAccessDeniedError(SecurityException):
    """
    Raised when access to an API endpoint is denied based on core rules (e.g., IP whitelist).
    """
    status_code = 403
    default_detail = _('Access to this API endpoint is denied.')
    default_code = 'api_access_denied'

# --- مثال: استثناهای مرتبط با کاربر ---
class UserVerificationRequiredError(CoreSystemException):
    """
    Raised when an action requires the user to be verified.
    """
    status_code = 403
    default_detail = _('User verification is required to perform this action.')
    default_code = 'user_verification_required'

class UserAccountLockedError(CoreSystemException):
    """
    Raised when an action is attempted on a locked user account.
    """
    status_code = 423 # Locked
    default_detail = _('Your account is currently locked.')
    default_code = 'user_account_locked'

# --- مثال: استثناهای مرتبط با کاربر و دسترسی ---
class UserNotInWhitelistedIPError(SecurityException):
    """
    Raised when a user attempts to access a feature from an IP not in their whitelisted IPs.
    """
    status_code = 403
    default_detail = _('Access denied from this IP address.')
    default_code = 'ip_not_whitelisted'

# --- مثال: استثناهای مرتبط با نماد ---
class InstrumentNotSupportedByExchangeError(CoreSystemException):
    """
    Raised when an instrument is requested on an exchange where it's not mapped or supported.
    """
    status_code = 400
    default_detail = _('This instrument is not supported or mapped on the requested exchange.')
    default_code = 'instrument_not_supported_on_exchange'

# --- مثال: استثناهای مرتبط با اندیکاتور ---
class IndicatorParameterValidationError(InputValidationError):
    """
    Raised when parameters provided for an indicator are invalid.
    """
    status_code = 400
    default_detail = _('Indicator parameters are invalid.')
    default_code = 'indicator_parameter_validation_error'

# --- مثال: استثناهای مرتبط با الگوی قیمت ---
class PriceActionPatternError(CoreSystemException):
    """
    Base exception for errors related to price action patterns.
    """
    status_code = 500
    default_detail = _('An error occurred with a price action pattern.')
    default_code = 'price_action_pattern_error'

# --- مثال: استثناهای مرتبط با مفاهیم اسمارت مانی ---
class SmartMoneyConceptError(CoreSystemException):
    """
    Base exception for errors related to smart money concepts.
    """
    status_code = 500
    default_detail = _('An error occurred with a smart money concept.')
    default_code = 'smart_money_concept_error'

# --- مثال: استثناهای مرتبط با متریک AI ---
class AIMetricError(CoreSystemException):
    """
    Base exception for errors related to AI metrics.
    """
    status_code = 500
    default_detail = _('An error occurred with an AI metric.')
    default_code = 'ai_metric_error'

# --- مثال: استثناهای مرتبط با لیست نظارت ---
class WatchlistError(CoreSystemException):
    """
    Base exception for errors related to watchlists.
    """
    status_code = 500
    default_detail = _('An error occurred with a watchlist.')
    default_code = 'watchlist_error'

class WatchlistOwnershipError(WatchlistError):
    """
    Raised when a user tries to access a watchlist they do not own.
    """
    status_code = 403
    default_detail = _('You do not have permission to access this watchlist.')
    default_code = 'watchlist_ownership_error'

# --- استثناهای مرتبط با سیگنال‌ها ---
class SignalError(CoreSystemException):
    """
    Base exception for errors occurring within core signal handlers.
    """
    status_code = 500
    default_detail = _('An error occurred in a core signal handler.')
    default_code = 'core_signal_error'

class PostSaveSignalError(SignalError):
    """
    Raised for errors in post_save signal handlers.
    """
    status_code = 500
    default_detail = _('An error occurred in a post_save signal handler.')
    default_code = 'post_save_signal_error'

# --- استثناهای مرتبط با تاسک‌های Celery ---
class TaskError(CoreSystemException):
    """
    Base exception for errors occurring within core Celery tasks.
    """
    status_code = 500
    default_detail = _('An error occurred in a core Celery task.')
    default_code = 'core_task_error'

class DataSyncTaskError(TaskError):
    """
    Raised for errors in data synchronization tasks.
    """
    status_code = 500
    default_detail = _('An error occurred during data synchronization task.')
    default_code = 'data_sync_task_error'

class AgentEventTaskError(TaskError):
    """
    Raised for errors in agent event processing tasks.
    """
    status_code = 500
    default_detail = _('An error occurred during agent event processing task.')
    default_code = 'agent_event_task_error'

# --- استثناهای مرتبط با سرویس‌ها ---
class ServiceError(CoreSystemException):
    """
    Base exception for errors occurring within core services.
    """
    status_code = 500
    default_detail = _('An error occurred in a core service.')
    default_code = 'core_service_error'

class DataFetchServiceError(ServiceError):
    """
    Raised for errors in fetching data within core services.
    """
    status_code = 500
    default_detail = _('An error occurred while fetching data in a core service.')
    default_code = 'data_fetch_service_error'

class AuditServiceError(ServiceError):
    """
    Raised for errors in audit logging within core services.
    """
    status_code = 500
    default_detail = _('An error occurred in the audit logging service.')
    default_code = 'audit_service_error'

# --- استثناهای مرتبط با کانکتورها (اگر مستقیماً در این اپلیکیشن استفاده شود) ---
class ConnectorError(CoreSystemException):
    """
    Base exception for errors related to data connectors (e.g., Binance, Coinbase API).
    """
    status_code = 502 # Bad Gateway (اگر مشکل از سمت صرافی باشد)
    default_detail = _('An error occurred with the data connector.')
    default_code = 'connector_error'

class ConnectorAuthenticationError(ConnectorError):
    """
    Raised when the connector fails to authenticate with the data source.
    """
    status_code = 401
    default_detail = _('Authentication failed with the data connector.')
    default_code = 'connector_auth_error'

class ConnectorRateLimitError(ConnectorError):
    """
    Raised when the connector hits the rate limit of the data source.
    """
    status_code = 429
    default_detail = _('Rate limit exceeded on the data connector.')
    default_code = 'connector_rate_limit_error'

class ConnectorDataError(ConnectorError):
    """
    Raised when the connector receives invalid or unexpected data from the source.
    """
    status_code = 502
    default_detail = _('Received invalid or unexpected data from the data connector.')
    default_code = 'connector_data_error'

# --- مثال: استثناهای مرتبط با کش ---
class CacheError(CoreSystemException):
    """
    Base exception for errors related to the caching system.
    """
    status_code = 500
    default_detail = _('An error occurred with the caching system.')
    default_code = 'cache_error'

class CacheMissError(CacheError):
    """
    Raised when a requested key is not found in the cache.
    """
    status_code = 404
    default_detail = _('The requested item was not found in the cache.')
    default_code = 'cache_miss'

class CacheSyncError(CacheError):
    """
    Raised when an error occurs while synchronizing cache entries with the database.
    """
    status_code = 500
    default_detail = _('An error occurred while synchronizing the cache.')
    default_code = 'cache_sync_error'

class CacheKeyCollisionError(CacheError):
    """
    Raised when a cache key collision is detected (e.g., different data types using the same key).
    """
    status_code = 500
    default_detail = _('A cache key collision was detected.')
    default_code = 'cache_key_collision'

# --- استثناهای مرتبط با مدیریت کاربر ---
class UserVerificationRequiredError(CoreSystemException):
    """
    Raised when an action requires the user to be verified.
    """
    status_code = 403
    default_detail = _('User verification is required to perform this action.')
    default_code = 'user_verification_required'

class UserAccountLockedError(CoreSystemException):
    """
    Raised when an action is attempted on a locked user account.
    """
    status_code = 423 # Locked
    default_detail = _('Your account is currently locked.')
    default_code = 'user_account_locked'

class UserNotInWhitelistedIPError(SecurityException):
    """
    Raised when a user attempts to access a feature from an IP not in their whitelisted IPs.
    """
    status_code = 403
    default_detail = _('Access denied from this IP address.')
    default_code = 'ip_not_whitelisted'

# --- استثناهای مرتبط با ابزار ---
class InstrumentError(CoreSystemException):
    """
    Base exception for errors related to instruments.
    """
    status_code = 500
    default_detail = _('An error occurred with an instrument.')
    default_code = 'instrument_error'

class InstrumentNotFoundError(InstrumentError):
    """
    Raised when an instrument is requested but does not exist.
    """
    status_code = 404
    default_detail = _('The requested instrument was not found.')
    default_code = 'instrument_not_found'

class InstrumentInactiveError(InstrumentError):
    """
    Raised when an action is attempted on an instrument that is not active.
    """
    status_code = 400
    default_detail = _('The instrument is not active.')
    default_code = 'instrument_inactive'

class InstrumentDelistedError(InstrumentError):
    """
    Raised when an action is attempted on an instrument that has been delisted.
    """
    status_code = 400
    default_detail = _('The instrument has been delisted.')
    default_code = 'instrument_delisted'

# --- استثناهای مرتبط با کانفیگ داده ابزار ---
class InstrumentConfigError(InstrumentError):
    """
    Base exception for errors related to instrument data configuration.
    """
    status_code = 500
    default_detail = _('An error occurred with an instrument data configuration.')
    default_code = 'instrument_config_error'

class ConfigValidationError(InstrumentConfigError):
    """
    Raised when an instrument data configuration fails validation.
    """
    status_code = 400
    default_detail = _('Instrument data configuration validation failed.')
    default_code = 'config_validation_error'

# --- استثناهای مرتبط با اندیکاتور ---
class IndicatorError(CoreSystemException):
    """
    Base exception for errors related to indicators.
    """
    status_code = 500
    default_detail = _('An error occurred with an indicator.')
    default_code = 'indicator_error'

class IndicatorNotFoundError(IndicatorError):
    """
    Raised when an indicator is requested but does not exist.
    """
    status_code = 404
    default_detail = _('The requested indicator was not found.')
    default_code = 'indicator_not_found'

class IndicatorParameterValidationError(IndicatorError):
    """
    Raised when parameters provided for an indicator are invalid.
    """
    status_code = 400
    default_detail = _('Indicator parameters are invalid.')
    default_code = 'indicator_parameter_validation_error'

# --- استثناهای مرتبط با الگوی قیمت ---
class PriceActionPatternError(CoreSystemException):
    """
    Base exception for errors related to price action patterns.
    """
    status_code = 500
    default_detail = _('An error occurred with a price action pattern.')
    default_code = 'price_action_pattern_error'

# --- استثناهای مرتبط با مفاهیم اسمارت مانی ---
class SmartMoneyConceptError(CoreSystemException):
    """
    Base exception for errors related to smart money concepts.
    """
    status_code = 500
    default_detail = _('An error occurred with a smart money concept.')
    default_code = 'smart_money_concept_error'

# --- استثناهای مرتبط با متریک AI ---
class AIMetricError(CoreSystemException):
    """
    Base exception for errors related to AI metrics.
    """
    status_code = 500
    default_detail = _('An error occurred with an AI metric.')
    default_code = 'ai_metric_error'

# --- استثناهای مرتبط با لیست نظارت ---
class WatchlistError(CoreSystemException):
    """
    Base exception for errors related to watchlists.
    """
    status_code = 500
    default_detail = _('An error occurred with a watchlist.')
    default_code = 'watchlist_error'

class WatchlistOwnershipError(WatchlistError):
    """
    Raised when a user tries to access a watchlist they do not own.
    """
    status_code = 403
    default_detail = _('You do not have permission to access this watchlist.')
    default_code = 'watchlist_ownership_error'

# --- استثناهای مرتبط با سیگنال‌ها ---
class SignalError(CoreSystemException):
    """
    Base exception for errors occurring within core signal handlers.
    """
    status_code = 500
    default_detail = _('An error occurred in a core signal handler.')
    default_code = 'core_signal_error'

class PostSaveSignalError(SignalError):
    """
    Raised for errors in post_save signal handlers.
    """
    status_code = 500
    default_detail = _('An error occurred in a post_save signal handler.')
    default_code = 'post_save_signal_error'

# --- استثناهای مرتبط با تاسک‌های Celery ---
class TaskError(CoreSystemException):
    """
    Base exception for errors occurring within core Celery tasks.
    """
    status_code = 500
    default_detail = _('An error occurred in a core Celery task.')
    default_code = 'core_task_error'

class DataSyncTaskError(TaskError):
    """
    Raised for errors in data synchronization tasks.
    """
    status_code = 500
    default_detail = _('An error occurred during data synchronization task.')
    default_code = 'data_sync_task_error'

class AgentEventTaskError(TaskError):
    """
    Raised for errors in agent event processing tasks.
    """
    status_code = 500
    default_detail = _('An error occurred during agent event processing task.')
    default_code = 'agent_event_task_error'

# --- استثناهای مرتبط با سرویس‌ها ---
class ServiceError(CoreSystemException):
    """
    Base exception for errors occurring within core services.
    """
    status_code = 500
    default_detail = _('An error occurred in a core service.')
    default_code = 'core_service_error'

class DataFetchServiceError(ServiceError):
    """
    Raised for errors in fetching data within core services.
    """
    status_code = 500
    default_detail = _('An error occurred while fetching data in a core service.')
    default_code = 'data_fetch_service_error'

class AuditServiceError(ServiceError):
    """
    Raised for errors in audit logging within core services.
    """
    status_code = 500
    default_detail = _('An error occurred in the audit logging service.')
    default_code = 'audit_service_error'

# --- استثناهای مرتبط با کانکتورها ---
class ConnectorError(CoreSystemException):
    """
    Base exception for errors related to data connectors (e.g., Binance, Coinbase API).
    """
    status_code = 502 # Bad Gateway (اگر مشکل از سمت صرافی باشد)
    default_detail = _('An error occurred with the data connector.')
    default_code = 'connector_error'

class ConnectorAuthenticationError(ConnectorError):
    """
    Raised when the connector fails to authenticate with the data source.
    """
    status_code = 401
    default_detail = _('Authentication failed with the data connector.')
    default_code = 'connector_auth_error'

class ConnectorRateLimitError(ConnectorError):
    """
    Raised when the connector hits the rate limit of the data source.
    """
    status_code = 429
    default_detail = _('Rate limit exceeded on the data connector.')
    default_code = 'connector_rate_limit_error'

class ConnectorDataError(ConnectorError):
    """
    Raised when the connector receives invalid or unexpected data from the source.
    """
    status_code = 502
    default_detail = _('Received invalid or unexpected data from the data connector.')
    default_code = 'connector_data_error'

# --- استثناهای مرتبط با مدیریت کاربر ---
class UserVerificationRequiredError(CoreSystemException):
    """
    Raised when an action requires the user to be verified.
    """
    status_code = 403
    default_detail = _('User verification is required to perform this action.')
    default_code = 'user_verification_required'

class UserAccountLockedError(CoreSystemException):
    """
    Raised when an action is attempted on a locked user account.
    """
    status_code = 423 # Locked
    default_detail = _('Your account is currently locked.')
    default_code = 'user_account_locked'

class UserNotInWhitelistedIPError(SecurityException):
    """
    Raised when a user attempts to access a feature from an IP not in their whitelisted IPs.
    """
    status_code = 403
    default_detail = _('Access denied from this IP address.')
    default_code = 'ip_not_whitelisted'

# --- استثناهای مرتبط با دسترسی API ---
class APIAccessDeniedError(SecurityException):
    """
    Raised when access to an API endpoint is denied based on core rules (e.g., IP whitelist).
    """
    status_code = 403
    default_detail = _('Access to this API endpoint is denied.')
    default_code = 'api_access_denied'

# --- استثناهای مرتبط با مدل‌های BaseOwnedModel ---
class CannotChangeOwnerError(CoreSystemException):
    """
    Raised when an attempt is made to change the owner of an object after creation.
    """
    status_code = 400
    default_detail = _('The owner of this object cannot be changed after creation.')
    default_code = 'cannot_change_owner'

# --- استثناهای مرتبط با فعال/غیرفعال کردن ---
class ResourceDeactivatedError(CoreSystemException):
    """
    Raised when an action is attempted on a resource that is not active.
    """
    status_code = 400
    default_detail = _('This resource is currently deactivated.')
    default_code = 'resource_deactivated'

# --- مثال استفاده ---
# try:
#     # ... کدی که ممکن است خطا دهد ...
# except SomeCondition:
#     raise InstrumentValidationError("The provided symbol format is invalid.")
