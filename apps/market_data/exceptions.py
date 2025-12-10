# apps/market_data/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

class MarketDataBaseError(APIException):
    """
    Base exception class for all market data related errors.
    All custom exceptions in this app should inherit from this.
    """
    status_code = 500
    default_detail = _('An error occurred within the market data application.')
    default_code = 'market_data_base_error'

class DataSyncError(MarketDataBaseError):
    """
    Raised when an error occurs during data synchronization (historical or real-time).
    """
    status_code = 400  # Bad Request - مشکل در درخواست همگام‌سازی
    default_detail = _('Error occurred while synchronizing market data.')
    default_code = 'data_sync_error'

class DataFetchError(MarketDataBaseError):
    """
    Raised when an error occurs while fetching data from an external source (e.g., API).
    """
    status_code = 502  # Bad Gateway - اگر خطا از سمت صرافی باشد
    default_detail = _('Error occurred while fetching data from the data source.')
    default_code = 'data_fetch_error'

class DataProcessingError(MarketDataBaseError):
    """
    Raised when an error occurs while processing received data (validation, normalization, storage).
    """
    status_code = 400  # Bad Request - داده نامعتبر
    default_detail = _('Error occurred while processing received market data.')
    default_code = 'data_processing_error'

class InvalidDataFormatError(DataProcessingError):
    """
    Raised when the received data does not conform to the expected format for a specific source or type.
    """
    status_code = 400
    default_detail = _('Received data format is invalid for the specified source or type.')
    default_code = 'invalid_data_format'

class InsufficientDataError(MarketDataBaseError):
    """
    Raised when the required amount of data is not available for a specific operation.
    """
    status_code = 404  # Not Found - داده کافی وجود ندارد
    default_detail = _('Insufficient market data available for the requested operation.')
    default_code = 'insufficient_data'

class RateLimitExceededError(MarketDataBaseError):
    """
    Raised when the rate limit for an API call is exceeded.
    """
    status_code = 429  # Too Many Requests
    default_detail = _('Rate limit exceeded for the data source API.')
    default_code = 'rate_limit_exceeded'

class DataSourceNotActiveError(MarketDataBaseError):
    """
    Raised when attempting to use a data source that is marked as inactive.
    """
    status_code = 400  # Bad Request - منبع غیرفعال
    default_detail = _('The requested data source is not active.')
    default_code = 'data_source_not_active'

class ConfigValidationError(MarketDataBaseError):
    """
    Raised when a MarketDataConfig fails validation (e.g., invalid timeframe for data_type).
    """
    status_code = 400  # Bad Request - کانفیگ نامعتبر
    default_detail = _('Market data configuration validation failed.')
    default_code = 'config_validation_error'

class UnsupportedDataSourceError(MarketDataBaseError):
    """
    Raised when an attempt is made to use a data source that is not supported or not registered.
    """
    status_code = 400
    default_detail = _('The specified data source is not supported.')
    default_code = 'unsupported_data_source'

class UnsupportedDataTypeError(MarketDataBaseError):
    """
    Raised when an attempt is made to retrieve or process a data type not supported by the source/config.
    """
    status_code = 400
    default_detail = _('The specified data type is not supported by the source or config.')
    default_code = 'unsupported_data_type'

class OrderBookChecksumError(MarketDataBaseError):
    """
    Raised when the checksum of an order book snapshot does not match the expected value (if provided by source).
    Indicates potential data corruption or missed updates.
    """
    status_code = 422  # Unprocessable Entity - وضعیت نامعتبر کتاب سفارش
    default_detail = _('Order book checksum mismatch detected.')
    default_code = 'order_book_checksum_error'

class CacheMissError(MarketDataBaseError):
    """
    Raised when requested data is not found in the cache and must be fetched from the database/API.
    This is not necessarily an error condition but can be used for logging or control flow.
    """
    status_code = 404  # Not Found - در کش پیدا نشد
    default_detail = _('Requested data not found in cache.')
    default_code = 'cache_miss'

# سایر استثناهای مرتبط می‌توانند اضافه شوند
# مثلاً:
# class HistoricalDataNotAvailableError(MarketDataBaseError):
#     ...
# class RealTimeDataSubscriptionError(MarketDataBaseError):
#     ...
