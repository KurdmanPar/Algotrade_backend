# apps/instruments/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

class InstrumentException(APIException):
    """
    Base exception class for all instrument-related errors.
    Inherits from DRF's APIException for consistent API error responses.
    """
    status_code = 500
    default_detail = _('An error occurred within the instruments application.')
    default_code = 'instrument_error'

class InstrumentValidationError(InstrumentException):
    """
    Raised when an instrument's data fails validation (e.g., invalid symbol format, missing precision).
    """
    status_code = 400
    default_detail = _('Instrument data validation failed.')
    default_code = 'instrument_validation_error'

class InstrumentNotFound(InstrumentException):
    """
    Raised when an instrument is requested but does not exist.
    """
    status_code = 404
    default_detail = _('The requested instrument was not found.')
    default_code = 'instrument_not_found'

class InstrumentInactiveError(InstrumentException):
    """
    Raised when an action is attempted on an instrument that is not active.
    """
    status_code = 400
    default_detail = _('The instrument is not active.')
    default_code = 'instrument_inactive'

class InstrumentDelistedError(InstrumentException):
    """
    Raised when an action is attempted on an instrument that has been delisted.
    """
    status_code = 400
    default_detail = _('The instrument has been delisted.')
    default_code = 'instrument_delisted'

# --- Instrument Exchange Mapping Exceptions ---
class InstrumentExchangeMappingError(InstrumentException):
    """
    Raised for errors related to mapping instruments to exchanges (e.g., duplicate mapping).
    """
    status_code = 400
    default_detail = _('Error in instrument-exchange mapping.')
    default_code = 'instrument_exchange_mapping_error'

class ExchangeSpecificDataMismatchError(InstrumentException):
    """
    Raised when data retrieved from an exchange mismatches the stored mapping details.
    For example, if the tick size received from the API differs from the one stored in the map.
    """
    status_code = 422 # Unprocessable Entity
    default_detail = _('Exchange-specific data mismatch detected.')
    default_code = 'exchange_data_mismatch'

# --- Indicator Model Exceptions ---
class IndicatorError(InstrumentException):
    """
    Base exception for indicator-related errors.
    """
    status_code = 500
    default_detail = _('An error occurred with an indicator.')
    default_code = 'indicator_error'

class IndicatorValidationError(IndicatorError):
    """
    Raised when an indicator's definition or parameters are invalid.
    """
    status_code = 400
    default_detail = _('Indicator definition or parameters are invalid.')
    default_code = 'indicator_validation_error'

class IndicatorParameterValidationError(IndicatorError):
    """
    Raised when a specific parameter value for an indicator is invalid.
    """
    status_code = 400
    default_detail = _('Indicator parameter value is invalid.')
    default_code = 'indicator_parameter_validation_error'

class IndicatorCalculationError(IndicatorError):
    """
    Raised when an error occurs during the calculation of an indicator's value.
    """
    status_code = 500
    default_detail = _('An error occurred while calculating the indicator.')
    default_code = 'indicator_calculation_error'

# --- Price Action & SMC Exceptions ---
class PriceActionPatternError(InstrumentException):
    """
    Raised for errors related to price action patterns.
    """
    status_code = 400
    default_detail = _('Error related to a price action pattern.')
    default_code = 'price_action_pattern_error'

class SmartMoneyConceptError(InstrumentException):
    """
    Raised for errors related to smart money concepts.
    """
    status_code = 400
    default_detail = _('Error related to a smart money concept.')
    default_code = 'smart_money_concept_error'

# --- AI Metric Exceptions ---
class AIMetricError(InstrumentException):
    """
    Raised for errors related to AI metrics.
    """
    status_code = 400
    default_detail = _('Error related to an AI metric.')
    default_code = 'ai_metric_error'

# --- Watchlist Exceptions ---
class WatchlistError(InstrumentException):
    """
    Base exception for watchlist-related errors.
    """
    status_code = 400
    default_detail = _('An error occurred with a watchlist.')
    default_code = 'watchlist_error'

class WatchlistOwnershipError(WatchlistError):
    """
    Raised when a user tries to access a watchlist they do not own.
    """
    status_code = 403 # Forbidden
    default_detail = _('You do not have permission to access this watchlist.')
    default_code = 'watchlist_ownership_error'

class WatchlistItemError(WatchlistError):
    """
    Raised for errors related to items (instruments) within a watchlist.
    """
    status_code = 400
    default_detail = _('An error occurred with an item in the watchlist.')
    default_code = 'watchlist_item_error'

# --- General Utility Exceptions ---
class DataIntegrityError(InstrumentException):
    """
    Raised when a violation of data integrity rules is detected within the instruments app.
    """
    status_code = 500
    default_detail = _('Data integrity violation detected.')
    default_code = 'data_integrity_error'

class ConfigurationError(InstrumentException):
    """
    Raised when a configuration setting for the instruments app is invalid or missing.
    """
    status_code = 500
    default_detail = _('Configuration error in instruments app.')
    default_code = 'configuration_error'

# --- API/Permission Exceptions (می‌تواند در permissions.py نیز استفاده شود) ---
class InsufficientPermissionsError(InstrumentException):
    """
    Raised when a user does not have sufficient permissions for an action.
    """
    status_code = 403
    default_detail = _('Insufficient permissions to perform this action.')
    default_code = 'insufficient_permissions'

class APIKeyError(InstrumentException):
    """
    Base exception for errors related to API key usage.
    """
    status_code = 401 # Unauthorized
    default_detail = _('API key error.')
    default_code = 'api_key_error'

class InvalidAPIKeyError(APIKeyError):
    """
    Raised when an invalid or non-existent API key is provided.
    """
    status_code = 401
    default_detail = _('Provided API key is invalid or does not exist.')
    default_code = 'invalid_api_key'

class ExpiredAPIKeyError(APIKeyError):
    """
    Raised when an API key has expired.
    """
    status_code = 401
    default_detail = _('Provided API key has expired.')
    default_code = 'expired_api_key'

class APIKeyInactiveError(APIKeyError):
    """
    Raised when an API key is inactive/disabled.
    """
    status_code = 401
    default_detail = _('Provided API key is inactive.')
    default_code = 'api_key_inactive'

# --- Risk Management Related Exceptions (اگر در این اپلیکیشن مدیریت ریسک نباشد، می‌تواند در اپلیکیشن جداگانه‌ای قرار گیرد) ---
# ولی چون نمادها ممکن است محدودیت‌هایی داشته باشند، چند مورد مرتبط اینجا قرار می‌گیرد.
class InstrumentLimitExceededError(InstrumentException):
    """
    Raised when an operation exceeds a predefined limit for an instrument (e.g., max position size).
    """
    status_code = 422
    default_detail = _('Operation exceeds the defined limit for this instrument.')
    default_code = 'instrument_limit_exceeded'

class InstrumentNotAvailableForTradingError(InstrumentException):
    """
    Raised when an instrument is not available for trading at the moment (e.g., halted, outside trading hours - if applicable).
    """
    status_code = 423 # Locked
    default_detail = _('This instrument is not available for trading at the moment.')
    default_code = 'instrument_not_available_for_trading'

# --- موارد جدید مرتبط با تغییرات احتمالی ---
# مثلاً اگر نیاز به یک استثنا برای زمانی که یک نماد پشتیبانی از نوع خاصی از معامله نمی‌کند
class UnsupportedInstrumentFeatureError(InstrumentException):
    """
    Raised when an action requiring a specific instrument feature (e.g., margin, futures) is attempted
    on an instrument that does not support it.
    """
    status_code = 400
    default_detail = _('The requested feature is not supported by this instrument.')
    default_code = 'unsupported_instrument_feature'

# مثلاً اگر نیاز به یک استثنا برای زمانی که داده‌های یک نماد در یک بازه زمانی خاص وجود ندارد
class InstrumentDataNotAvailableError(InstrumentException):
    """
    Raised when historical or real-time data for an instrument is not available for a requested period or type.
    """
    status_code = 404
    default_detail = _('Requested data for the instrument is not available.')
    default_code = 'instrument_data_not_available'

# --- استثناهای مرتبط با کش ---
class CacheError(InstrumentException):
    """
    Base exception for caching errors within the instruments app.
    """
    status_code = 500
    default_detail = _('An error occurred with the instruments cache.')
    default_code = 'cache_error'

class CacheMissError(CacheError):
    """
    Raised when requested data is not found in the cache.
    """
    status_code = 404
    default_detail = _('Requested data not found in cache.')
    default_code = 'cache_miss'

class CacheSyncError(CacheError):
    """
    Raised when an error occurs during cache synchronization.
    """
    status_code = 500
    default_detail = _('Error occurred while synchronizing the cache.')
    default_code = 'cache_sync_error'

# --- استثناهای مرتبط با سیگنال‌ها ---
class SignalError(InstrumentException):
    """
    Base exception for errors occurring within instrument-related signals.
    """
    status_code = 500
    default_detail = _('An error occurred in an instrument-related signal.')
    default_code = 'signal_error'

class PostSaveSignalError(SignalError):
    """
    Raised for errors in post_save signals for instrument models.
    """
    status_code = 500
    default_detail = _('An error occurred in a post_save signal for an instrument model.')
    default_code = 'post_save_signal_error'

# --- استثناهای مرتبط با تاسک‌های Celery ---
class TaskError(InstrumentException):
    """
    Base exception for errors occurring within instrument-related Celery tasks.
    """
    status_code = 500
    default_detail = _('An error occurred in an instrument-related Celery task.')
    default_code = 'task_error'

class DataSyncTaskError(TaskError):
    """
    Raised for errors in instrument data synchronization tasks.
    """
    status_code = 500
    default_detail = _('An error occurred during instrument data synchronization task.')
    default_code = 'data_sync_task_error'

# --- استثناهای مرتبط با سرویس‌ها ---
class ServiceError(InstrumentException):
    """
    Base exception for errors occurring within instrument-related services.
    """
    status_code = 500
    default_detail = _('An error occurred in an instrument-related service.')
    default_code = 'service_error'

class DataFetchServiceError(ServiceError):
    """
    Raised for errors in fetching data within instrument services.
    """
    status_code = 500
    default_detail = _('An error occurred while fetching data in an instrument service.')
    default_code = 'data_fetch_service_error'

# --- استثناهای مرتبط با کانکتورها (اگر مستقیماً در این اپلیکیشن استفاده شود) ---
class ConnectorError(InstrumentException):
    """
    Base exception for errors related to data connectors (e.g., Binance, Coinbase API).
    """
    status_code = 502 # Bad Gateway (اگر مشکل از صرافی باشد)
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

# --- مثال استفاده ---
# try:
#     # ... کدی که ممکن است خطا دهد ...
# except SomeCondition:
#     raise InstrumentValidationError("The provided symbol format is invalid.")
