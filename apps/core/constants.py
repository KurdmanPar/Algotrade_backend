# apps/core/constants.py

from django.utils.translation import gettext_lazy as _

# --- انتخاب‌های (Choices) عمومی ---

# مثال: نوع کاربر
USER_TYPE_CHOICES = [
    ('individual', _('Individual Trader')),
    ('institutional', _('Institutional Trader')),
    ('developer', _('Developer')),
    ('bot', _('Trading Bot')), # اگر بات‌ها نیز کاربر محسوب شوند
]

# مثال: وضعیت کلید API
API_KEY_STATUS_CHOICES = [
    ('active', _('Active')),
    ('inactive', _('Inactive')),
    ('revoked', _('Revoked')),
]

# مثال: نوع عملیات برای AuditLog
AUDIT_ACTION_CHOICES = [
    ('CREATE', _('Create')),
    ('READ', _('Read')),
    ('UPDATE', _('Update')),
    ('DELETE', _('Delete')),
    ('LOGIN', _('Login')),
    ('LOGOUT', _('Logout')),
    ('ORDER_PLACE', _('Place Order')),
    ('ORDER_CANCEL', _('Cancel Order')),
    ('RISK_VIOLATION', _('Risk Violation')),
    ('AGENT_START', _('Agent Start')),
    ('AGENT_STOP', _('Agent Stop')),
    ('AGENT_ERROR', _('Agent Error')),
    # ... سایر عملیات مرتبط با MAS
]

# مثال: نوع داده بازار
MARKET_DATA_TYPE_CHOICES = [
    ('TICK', _('Tick Data')),
    ('OHLCV', _('OHLCV')),
    ('ORDER_BOOK', _('Order Book')),
    ('TRADES', _('Trades')),
    ('INDEX', _('Index')),
    ('FUNDING_RATE', _('Funding Rate')),
    ('LIQUIDATION', _('Liquidation')),
    ('OPEN_INTEREST', _('Open Interest')),
]

# مثال: نوع اندیکاتور
INDICATOR_TYPE_CHOICES = [
    ('technical', _('Technical')),
    ('fundamental', _('Fundamental')),
    ('sentiment', _('Sentiment')),
    ('ai_ml', _('AI/ML Based')),
]

# مثال: سطح ریسک
RISK_LEVEL_CHOICES = [
    ('low', _('Low Risk')),
    ('medium', _('Medium Risk')),
    ('high', _('High Risk')),
]

# مثال: واحد زمانی (Timeframe)
TIMEFRAME_CHOICES = [
    ('1s', _('1 Second')),
    ('1m', _('1 Minute')),
    ('5m', _('5 Minutes')),
    ('15m', _('15 Minutes')),
    ('30m', _('30 Minutes')),
    ('1h', _('1 Hour')),
    ('4h', _('4 Hours')),
    ('1d', _('1 Day')),
    ('1w', _('1 Week')),
    ('1M', _('1 Month')),
]

# مثال: نوع سفارش
ORDER_TYPE_CHOICES = [
    ('MARKET', _('Market')),
    ('LIMIT', _('Limit')),
    ('STOP_LOSS', _('Stop Loss')),
    ('TAKE_PROFIT', _('Take Profit')),
    ('STOP_LOSS_LIMIT', _('Stop Loss Limit')),
    ('TAKE_PROFIT_LIMIT', _('Take Profit Limit')),
]

# مثال: سمت سفارش
ORDER_SIDE_CHOICES = [
    ('BUY', _('Buy')),
    ('SELL', _('Sell')),
]

# مثال: وضعیت سفارش
ORDER_STATUS_CHOICES = [
    ('NEW', _('New')),
    ('PARTIALLY_FILLED', _('Partially Filled')),
    ('FILLED', _('Filled')),
    ('CANCELED', _('Canceled')),
    ('PENDING_CANCEL', _('Pending Cancel')),
    ('REJECTED', _('Rejected')),
    ('EXPIRED', _('Expired')),
]

# مثال: وضعیت عامل (Agent)
AGENT_STATUS_CHOICES = [
    ('IDLE', _('Idle')),
    ('RUNNING', _('Running')),
    ('PAUSED', _('Paused')),
    ('ERROR', _('Error')),
    ('STOPPED', _('Stopped')),
]

# مثال: نوع عامل (Agent)
AGENT_TYPE_CHOICES = [
    ('DATA_COLLECTOR', _('Data Collector')),
    ('STRATEGY_ANALYZER', _('Strategy Analyzer')),
    ('ORDER_EXECUTOR', _('Order Executor')),
    ('RISK_MANAGER', _('Risk Manager')),
    ('REPORT_GENERATOR', _('Report Generator')),
]

# --- مقادیر پیش‌فرض ---
DEFAULT_BASE_CURRENCY = 'USD'
DEFAULT_RISK_LEVEL = 'medium'
DEFAULT_MAX_ACTIVE_TRADES = 5
DEFAULT_LEVERAGE = 1
DEFAULT_TIMEZONE = 'UTC'
DEFAULT_API_RATE_LIMIT_PER_MINUTE = 1200
DEFAULT_ORDER_TIMEOUT_SECONDS = 30

# --- محدودیت‌های سیستم ---
MAX_API_KEYS_PER_USER = 10
MAX_WATCHLISTS_PER_USER = 20
MAX_CACHE_SIZE_MB = 100 # اگر از کش پایگاه داده استفاده می‌شود
MIN_RATE_LIMIT_PER_MINUTE = 1
MAX_RATE_LIMIT_PER_MINUTE = 10000
MAX_STRATEGIES_PER_USER = 50
MAX_BOTS_PER_USER = 10

# --- مقادیر پیش‌فرض تنظیمات ---
SYSTEM_SETTING_DEFAULTS = {
    'GLOBAL_RATE_LIMIT_PER_MINUTE': 1000,
    'DEFAULT_MARKET_DATA_BACKEND': 'TIMESCALE',
    'ENABLE_REALTIME_SYNC': True,
    'ENABLE_HISTORICAL_SYNC': True,
    'SYNC_BATCH_SIZE': 1000,
    'DEFAULT_RISK_TOLERANCE': 'medium',
    'MAX_OPEN_ORDERS_PER_INSTRUMENT': 10,
}

# --- مقادیر مربوط به MAS ---
# مثال: تعداد حداکثر تلاش مجدد برای تاسک‌های Celery
CELERY_TASK_RETRY_MAX = 3
CELERY_TASK_RETRY_COUNTDOWN = 60 # ثانیه

# مثال: انواع پیام‌های MAS
MAS_MESSAGE_TYPES = [
    'DATA_RECEIVED',
    'ORDER_PLACED',
    'ORDER_FILLED',
    'ORDER_CANCELED',
    'RISK_ALERT',
    'AGENT_STARTED',
    'AGENT_STOPPED',
    'HEARTBEAT',
    'CONFIG_UPDATE',
    'SHUTDOWN_REQUEST',
]

# --- مقادیر مربوط به امنیت ---
# مثال: حداکثر تعداد تلاش ناموفق ورود به سیستم قبل از قفل شدن
MAX_LOGIN_ATTEMPTS_BEFORE_LOCKOUT = 5
LOCKOUT_DURATION_MINUTES = 30

# --- مقادیر مربوط به مدیریت داده ---
# مثال: حداکثر حجم داده‌هایی که در هر بار همگام‌سازی پردازش می‌شود
SYNC_BATCH_SIZE_DEFAULT = 1000
SYNC_BATCH_SIZE_MAX = 10000

# --- مقادیر مربوط به کارمزدها و محدودیت‌های صرافی ---
# این ممکن است در مدل‌های جداگانه یا فایل‌های تنظیمات صرافی (exchanges app) قرار گیرد
# DEFAULT_EXCHANGE_FEES = { 'binance': 0.001, 'coinbase': 0.005, ... }
# MAX_POSITION_SIZE_USD = 1000000
# STOP_LOSS_PERCENTAGE_LIMIT = 5

# --- مقادیر مربوط به کش ---
CACHE_TIMEOUT_SHORT = 300  # 5 minutes
CACHE_TIMEOUT_MEDIUM = 3600 # 1 hour
CACHE_TIMEOUT_LONG = 86400  # 24 hours
CACHE_PREFIX_INSTRUMENTS = "inst_"
CACHE_PREFIX_INDICATORS = "ind_"
CACHE_PREFIX_MARKET_DATA = "md_"
CACHE_PREFIX_AGENTS = "agt_"

# --- مقادیر مربوط به احراز هویت ---
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 15
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 7

# --- مقادیر مربوط به لاگ ---
LOG_LEVEL_DEFAULT = 'INFO'
LOG_FORMAT_DEFAULT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# --- سایر ثابت‌های ممکن ---
# مثلاً:
# EXCHANGE_FEES = { 'binance': 0.001, 'coinbase': 0.005, ... }
# MAX_POSITION_SIZE_USD = 1000000
# STOP_LOSS_PERCENTAGE_LIMIT = 5
