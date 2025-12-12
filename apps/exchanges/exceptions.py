''''''
با سلام،


ممنون بابت تاکید بر اهمیت مدیریت خطا. این موضوع بسیار حیاتی به ویژه در یک سیستم معاملات الگوریتمی حساس و پیچیده مانند سیستم شما است. در ادامه، فایل `exceptions.py` را با تعریف گسترده‌تری از کلاس‌های استثنا (Exception Classes) ارائه می‌دهم که پوشش کامل‌تری از خطاهای احتمالی در اپلیکیشن `exchanges` فراهم می‌کند.

### 8. فایل `apps/exchanges/exceptions.py` (ارتقا یافته و کامل)

این فایل کلاس‌های استثنا (Exception Classes) را برای مدیریت خطاهای خاص اپلیکیشن `exchanges` تعریف می‌کند. هدف از این ارتقا، ایجاد یک سیستم مدیریت خطا جامع است که بتواند انواع مختلف خطاها را به طور دقیق شناسایی، طبقه‌بندی و گزارش دهد. این کار باعث می‌شود که:

1.  **عیب‌یابی آسان‌تر شود:** هر خطای خاص، یک کلاس منحصر به فرد دارد که می‌تواند به راحتی در لاگ‌ها یا کد شناسایی شود.
2.  **پاسخ‌دهی بهتر امکان‌پذیر شود:** نماها (Views) یا سرویس‌ها (Services) می‌توانند بر اساس نوع استثنا، عملکردهای متفاوتی (مثل تلاش مجدد، بازگرداندن پاسخ خاص، ثبت خطا در سیستم نظارتی) داشته باشند.
3.  **امنیت سیستم تقویت شود:** خطاهای مرتبط با امنیت (مثل تلاش برای دسترسی غیرمجاز یا اعتبارسنجی ناموفق کلیدها) به طور جداگانه مدیریت شوند.
4.  **کاربر تجربه بهتری داشته باشد:** پاسخ‌های خطا می‌توانند واضح‌تر و قابل فهم‌تر باشند.

```python

# apps/exchanges/exceptions.py

from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _

# --- خطاهای عمومی و سطح بالا ---
class ExchangeBaseError(APIException):
    """
    کلاس پایه برای تمام استثناهای مرتبط با اپلیکیشن exchanges.
    استفاده از این کلاس می‌تواند کمک کند تا تمام استثناهای این اپلیکیشن
    را در یک بلاک try-except جامع گرفت.
    """
    status_code = 500
    default_detail = _('An error occurred within the exchange application.')
    default_code = 'exchange_base_error'

class ExchangeConfigurationError(ExchangeBaseError):
    """
    خطایی که زمانی رخ می‌دهد که تنظیمات مربوط به صرافی یا اتصال به آن نامعتبر باشد.
    مثلاً URL پایه اشتباه یا نسخه API پشتیبانی نشده.
    """
    status_code = 500
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
    status_code = 500
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

# سایر استثناهای مرتبط می‌توانند در این فایل اضافه شوند
# مثلاً استثنایی برای زمانی که نماد معاملاتی وجود ندارد یا ارتباط با کانکتور قطع شده است

