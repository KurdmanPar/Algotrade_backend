# apps/exchanges/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _
from apps.core.exceptions import CoreSystemException # ایمپورت از core

# --- خطاهای عمومی و سطح بالا (ارتقا یافته: ارث از Core) ---
class ExchangeBaseError(CoreSystemException): # اصلاح: ارث از CoreSystemException
    """
    کلاس پایه برای تمام استثناهای مرتبط با اپلیکیشن exchanges.
    این اکنون از CoreSystemException ارث می‌برد، بنابراین تمام ویژگی‌های آن را نیز دارد.
    """
    # status_code قبلاً در CoreSystemException تعریف شده (500)
    # default_detail قبلاً در CoreSystemException تعریف شده
    # default_code قبلاً در CoreSystemException تعریف شده
    # اگر نیاز به جزئیات بیشتری در این سطح دارید، می‌توانید آن را بازنویسی کنید
    default_detail = _('An error occurred within the exchange application.')
    default_code = 'exchange_base_error'

class ExchangeConfigurationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که تنظیمات مربوط به صرافی یا اتصال به آن نامعتبر باشد.
    مثلاً URL پایه اشتباه یا نسخه API پشتیبانی نشده.
    """
    # status_code قبلاً در CoreSystemException تعریف شده (500)
    default_detail = _('Exchange configuration error.')
    default_code = 'exchange_config_error'

# --- خطاهای مرتبط با احراز هویت و امنیت ---
class InvalidCredentialsError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که کلید/مخفی API ارائه شده نامعتبر باشد.
    """
    status_code = 401  # Unauthorized
    default_detail = _('Invalid API credentials provided for the exchange.')
    default_code = 'invalid_credentials'

class APIKeyRevokedOrDisabledError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که کلید API از سمت صرافی غیرفعال یا لغو شده باشد.
    """
    status_code = 401  # Unauthorized
    default_detail = _('API key has been revoked or disabled by the exchange.')
    default_code = 'api_key_revoked'

class InsufficientAPIPermissionsError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که کلید API دسترسی کافی برای انجام عملیات درخواستی ندارد.
    """
    status_code = 403  # Forbidden
    default_detail = _('Insufficient permissions for the provided API key.')
    default_code = 'insufficient_api_permissions'

class ExchangeAccountSecurityError(ExchangeBaseError):
    """
    خطای عمومی امنیتی مربوط به حساب صرافی (مثلاً IP مجاز نیست).
    """
    status_code = 403
    default_detail = _('Security error related to the exchange account.')
    default_code = 'account_security_error'

# --- خطاهای مرتبط با اتصال و شبکه ---
class ExchangeConnectionError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که امکان اتصال به صرافی وجود نداشته باشد.
    مثلاً به دلیل قطعی شبکه یا مسدود شدن IP.
    """
    status_code = 502  # Bad Gateway
    default_detail = _('Unable to connect to the exchange.')
    default_code = 'connection_error'

class ExchangeTimeoutError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که درخواست به صرافی منجر به تایم‌اوت شود.
    """
    status_code = 504  # Gateway Timeout
    default_detail = _('Request to the exchange timed out.')
    default_code = 'timeout_error'

class ExchangeRateLimitExceededError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که نرخ درخواست‌ها به صرافی بیش از حد مجاز باشد.
    """
    status_code = 429  # Too Many Requests
    default_detail = _('Rate limit exceeded for the exchange API.')
    default_code = 'rate_limit_exceeded'

# --- خطاهای مرتبط با داده و اعتبارسنجی ---
class DataFetchError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که امکان دریافت داده از صرافی وجود نداشته باشد.
    ممکن است به دلیل خطای سمت صرافی یا فرمت غیرمنتظره پاسخ باشد.
    """
    status_code = 502  # Bad Gateway (اگر خطای سمت صرافی باشد)
    default_detail = _('Error occurred while fetching data from the exchange.')
    default_code = 'data_fetch_error'

class DataValidationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که داده دریافتی از صرافی با فرمت یا قوانین تعریف شده مطابقت نداشته باشد.
    """
    # status_code قبلاً در CoreSystemException تعریف شده (500)
    default_detail = _('Fetched data from exchange failed validation.')
    default_code = 'data_validation_error'

class InvalidSymbolError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که نماد ارائه شده برای یک عملیات (مثل دریافت قیمت یا سفارش) نامعتبر باشد.
    """
    status_code = 400  # Bad Request
    default_detail = _('Invalid trading symbol provided.')
    default_code = 'invalid_symbol'

class InvalidAmountError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که مقدار ارائه شده برای یک عملیات (مثل سفارش) نامعتبر باشد.
    """
    status_code = 400  # Bad Request
    default_detail = _('Invalid amount provided.')
    default_code = 'invalid_amount'

# --- خطاهای مرتبط با عملیات معاملاتی ---
class ExchangeSyncError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که همگام‌سازی داده‌های حساب صرافی با سیستم اصلی با خطا مواجه شود.
    """
    status_code = 400  # Bad Request یا 500 بسته به دلیل
    default_detail = _('Error occurred while synchronizing exchange account data.')
    default_code = 'exchange_sync_error'

class OrderExecutionError(ExchangeBaseError):
    """
    خطای عمومی مربوط به اجرای سفارش.
    """
    status_code = 400  # Bad Request
    default_detail = _('Error occurred while executing the order on the exchange.')
    default_code = 'order_execution_error'

class InsufficientBalanceError(OrderExecutionError):
    """
    خطایی که زمانی رخ می‌دهد که موجودی کافی برای اجرای سفارش وجود نداشته باشد.
    """
    status_code = 400
    default_detail = _('Insufficient balance to place the order.')
    default_code = 'insufficient_balance'

class OrderPlacementFailedError(OrderExecutionError):
    """
    خطایی که زمانی رخ می‌دهد که درخواست ایجاد سفارش به صورت کلی در صرافی رد شود.
    """
    status_code = 400
    default_detail = _('Order placement failed at the exchange.')
    default_code = 'order_placement_failed'

class OrderCancellationFailedError(OrderExecutionError):
    """
    خطایی که زمانی رخ می‌دهد که درخواست لغو سفارش به صورت کلی در صرافی رد شود.
    """
    status_code = 400
    default_detail = _('Order cancellation failed at the exchange.')
    default_code = 'order_cancellation_failed'

class OrderNotFoundError(OrderExecutionError):
    """
    خطایی که زمانی رخ می‌دهد که سفارش مورد نظر (برای لغو یا بررسی وضعیت) یافت نشود.
    """
    status_code = 404
    default_detail = _('The specified order was not found on the exchange.')
    default_code = 'order_not_found'

# --- خطاهای مرتبط با مدیریت کیف پول ---
class WalletOperationError(ExchangeBaseError):
    """
    خطای عمومی مربوط به عملیات‌های کیف پول.
    """
    status_code = 400
    default_detail = _('Error occurred during a wallet operation.')
    default_code = 'wallet_operation_error'

class InsufficientWalletBalanceError(WalletOperationError):
    """
    خطایی که زمانی رخ می‌دهد که موجودی کافی در کیف پول خاصی وجود نداشته باشد.
    """
    status_code = 400
    default_detail = _('Insufficient balance in the specified wallet.')
    default_code = 'insufficient_wallet_balance'

# --- خطاهای مرتبط با کانکتور ---
class ConnectorError(ExchangeBaseError):
    """
    خطای عمومی مربوط به کانکتور صرافی.
    """
    status_code = 502
    default_detail = _('Error occurred in the exchange connector.')
    default_code = 'connector_error'

class UnsupportedExchangeFeatureError(ConnectorError):
    """
    خطایی که زمانی رخ می‌دهد که یک ویژگی از صرافی توسط کانکتور پشتیبانی نشود.
    """
    status_code = 501  # Not Implemented
    default_detail = _('The requested exchange feature is not supported by the connector.')
    default_code = 'unsupported_feature'

# --- خطاهای مرتبط با بات ---
class BotExchangeLinkError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که مشکلی در اتصال یا تعامل بات با حساب صرافی رخ دهد.
    """
    status_code = 400
    default_detail = _('Error occurred in the interaction between the bot and the exchange account.')
    default_code = 'bot_exchange_link_error'

# --- خطاهای مرتبط با داده‌های کش ---
class CacheSyncError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که همگام‌سازی کش داده بازار با پایگاه داده با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('Error occurred while synchronizing market data cache.')
    default_code = 'cache_sync_error'

class CacheMissError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که داده در کش یافت نشود.
    """
    status_code = 404
    default_detail = _('Requested market data not found in cache.')
    default_code = 'cache_miss'

# --- خطاهای مرتبط با ارتباط WebSocket ---
class WebSocketConnectionError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که ارتباط WebSocket با صرافی یا کلاینت با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('WebSocket connection error occurred.')
    default_code = 'websocket_connection_error'

class WebSocketAuthenticationError(WebSocketConnectionError):
    """
    خطایی که زمانی رخ می‌دهد که احراز هویت WebSocket ناموفق باشد.
    """
    status_code = 401
    default_detail = _('WebSocket authentication failed.')
    default_code = 'websocket_auth_error'

# --- خطاهای مرتبط با نرمالایز کردن داده ---
class DataNormalizationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که نرمالایز کردن داده از یک صرافی با خطا مواجه شود.
    """
    status_code = 502
    default_detail = _('Failed to normalize data received from the exchange.')
    default_code = 'data_normalization_error'

# --- خطاهای مرتبط با مدیریت IP ---
class IPWhitelistError(ExchangeAccountSecurityError):
    """
    خطایی که زمانی رخ می‌دهد که IP کاربر در لیست مجاز نباشد.
    """
    status_code = 403
    default_detail = _('Your IP address is not allowed for this exchange account.')
    default_code = 'ip_whitelist_error'

# --- خطاهای مرتبط با رمزنگاری ---
class EncryptionError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که عملیات رمزنگاری/رمزگشایی با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('An error occurred during encryption or decryption.')
    default_code = 'encryption_error'

class DecryptionError(EncryptionError):
    """
    خطایی که زمانی رخ می‌دهد که رمزگشایی داده با خطا مواجه شود (مثلاً کلید اشتباه).
    """
    status_code = 500
    default_detail = _('Failed to decrypt data. Check the encryption key and IV.')
    default_code = 'decryption_error'

# --- خطاهای مرتبط با سیگنال‌ها ---
class SignalProcessingError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که پردازش یک سیگنال با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('An error occurred while processing a signal.')
    default_code = 'signal_processing_error'

# --- خطاهای مرتبط با سرویس‌ها ---
class ServiceUnavailableError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک سرویس مورد نیاز (مثل کانکتور یا کش) در دسترس نباشد.
    """
    status_code = 503 # Service Unavailable
    default_detail = _('A required service is currently unavailable.')
    default_code = 'service_unavailable'

# --- خطاهای مرتبط با ارائه داده ---
class DataProviderError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک ارائه‌دهنده داده (مثل کانکتور) با خطا مواجه شود.
    """
    status_code = 502
    default_detail = _('An error occurred with the data provider.')
    default_code = 'data_provider_error'

# --- خطاهای مرتبط با تاسک‌های Celery ---
class TaskRetryableError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک تاسک Celery نیاز به تلاش مجدد داشته باشد (مثلاً خطای موقت شبکه).
    """
    status_code = 500
    default_detail = _('A temporary error occurred in the task, marked for retry.')
    default_code = 'task_retryable_error'

class TaskNonRetryableError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک تاسک Celery نیاز به تلاش مجدد ندارد (مثلاً خطای دائمی).
    """
    status_code = 500
    default_detail = _('A permanent error occurred in the task, will not retry.')
    default_code = 'task_non_retryable_error'

# --- خطاهای مرتبط با MAS (اگر لازم باشد) ---
class AgentCommunicationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که ارتباط بین عامل‌ها با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('Error occurred in communication with another agent.')
    default_code = 'agent_communication_error'

# --- خطاهای مرتبط با امنیت ---
class DataTamperingDetectedError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که تغییر یا دستکاری داده شناسایی شود.
    """
    status_code = 400
    default_detail = _('Data integrity check failed, possible tampering detected.')
    default_code = 'data_tampering_detected'

# --- خطاهای مرتبط با مدل ---
class ModelIntegrityError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک مدل با داده نامعتبر ساخته یا ذخیره شود.
    """
    status_code = 500
    default_detail = _('A model integrity error occurred.')
    default_code = 'model_integrity_error'

# --- خطاهای مرتبط با کاربر ---
class UserVerificationRequiredError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک عملیات نیازمند تأیید حساب کاربر باشد.
    """
    status_code = 403
    default_detail = _('User verification is required to perform this action.')
    default_code = 'user_verification_required'

class UserAccountLockedError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک عملیات بر روی یک حساب قفل شده انجام شود.
    """
    status_code = 423 # Locked
    default_detail = _('Your account is currently locked.')
    default_code = 'user_account_locked'

# --- خطاهای مرتبط با کانفیگ ---
class ConfigValidationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک کانفیگ نامعتبر یا ناقص باشد.
    """
    status_code = 400
    default_detail = _('Configuration validation failed.')
    default_code = 'config_validation_error'

# --- خطاهای مرتبط با کارمزد ---
class FeeCalculationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که محاسبه کارمزد با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('An error occurred while calculating fees.')
    default_code = 'fee_calculation_error'

# --- خطاهای مرتبط با محدودیت‌ها ---
class LimitExceededError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک محدودیت سیستم یا صرافی نقض شود.
    """
    status_code = 400
    default_detail = _('An operation limit has been exceeded.')
    default_code = 'limit_exceeded'

class OrderSizeLimitError(LimitExceededError):
    """
    خطایی که زمانی رخ می‌دهد که اندازه سفارش بیش از حد مجاز باشد.
    """
    status_code = 400
    default_detail = _('Order size exceeds the defined limit for this instrument or account.')
    default_code = 'order_size_limit_error'

# --- خطاهای مرتبط با ارز ---
class AssetNotFoundError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک ارز مشخص یافت نشود.
    """
    status_code = 404
    default_detail = _('The specified asset was not found.')
    default_code = 'asset_not_found'

# --- خطاهای مرتبط با زمان ---
class InvalidTimeframeError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک بازه زمانی نامعتبر ارائه شود.
    """
    status_code = 400
    default_detail = _('Invalid timeframe provided.')
    default_code = 'invalid_timeframe'

# --- خطاهای مرتبط با تایم‌استمپ ---
class InvalidTimestampError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که یک تایم‌استمپ نامعتبر ارائه شود.
    """
    status_code = 400
    default_detail = _('Invalid timestamp provided.')
    default_code = 'invalid_timestamp'

# --- خطاهای مرتبط با ارزش پول ---
class InsufficientFundsError(OrderExecutionError):
    """
    خطایی که زمانی رخ می‌دهد که موجودی کافی برای انجام یک عملیات (مثل برداشت یا معامله) وجود نداشته باشد.
    """
    status_code = 400
    default_detail = _('Insufficient funds to perform the operation.')
    default_code = 'insufficient_funds'

# --- خطاهای مرتبط با سفارشات ---
class OrderTypeNotSupportedError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که نوع سفارش درخواستی توسط صرافی پشتیبانی نشود.
    """
    status_code = 400
    default_detail = _('The requested order type is not supported on this exchange.')
    default_code = 'order_type_not_supported'

class OrderSideNotSupportedError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که سمت سفارش (BUY/SELL) درخواستی توسط صرافی پشتیبانی نشود (مثلاً فروش در یک حساب صرفاً خرید).
    """
    status_code = 400
    default_detail = _('The requested order side is not supported.')
    default_code = 'order_side_not_supported'

# --- خطاهای مرتبط با کش ---
class CacheInvalidationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که عملیات باطل کردن کش با خطا مواجه شود.
    """
    status_code = 500
    default_detail = _('An error occurred while invalidating the cache.')
    default_code = 'cache_invalidation_error'

# --- خطاهای مرتبط با لاگ ---
class AuditLogError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که لاگ حسابرسی نتواند ایجاد شود.
    """
    status_code = 500
    default_detail = _('An error occurred while logging an audit event.')
    default_code = 'audit_log_error'

logger.info("Exchanges exceptions loaded successfully.")
