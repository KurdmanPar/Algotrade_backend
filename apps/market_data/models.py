# apps/market_data/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel
from apps.instruments.models import Instrument # اطمینان از وجود مدل Instrument
from django.core.validators import MinValueValidator, MaxValueValidator
import logging

logger = logging.getLogger(__name__)

class DataSource(BaseModel):
    """
    تعریف منابع داده (مثل Binance, CoinGecko, LBank, LBANK_WS).
    """
    TYPE_CHOICES = [
        ('REST_API', _('REST API')),
        ('WEBSOCKET', _('WebSocket')),
        ('FILE', _('File Import')),
        ('DATABASE', _('Database')),
        ('CUSTOM', _('Custom Endpoint')), # برای APIهای سفارشی
    ]
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, verbose_name=_("Type"))
    base_url = models.URLField(blank=True, verbose_name=_("Base URL"))
    ws_url = models.URLField(blank=True, verbose_name=_("WebSocket URL"))
    api_docs_url = models.URLField(blank=True, verbose_name=_("API Documentation URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_sandbox = models.BooleanField(default=False, verbose_name=_("Is Sandbox/Testnet"))
    rate_limit_per_minute = models.IntegerField(
        default=1200,
        verbose_name=_("Rate Limit Per Minute"),
        validators=[MinValueValidator(1)] # حداقل 1 درخواست در دقیقه
    )
    # اطلاعات امنیتی و احراز هویت
    requires_api_key = models.BooleanField(default=False, verbose_name=_("Requires API Key"))
    supports_websocket_auth = models.BooleanField(default=False, verbose_name=_("Supports WebSocket Auth"))
    # تنظیمات داده
    supported_timeframes = models.JSONField(default=list, blank=True, verbose_name=_("Supported Timeframes (JSON Array)"))
    supported_data_types = models.JSONField(default=list, blank=True, verbose_name=_("Supported Data Types (JSON Array)"))
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuration (JSON)"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Data Source")
        verbose_name_plural = _("Data Sources")


class MarketDataConfig(BaseModel):
    """
    پیکربندی نحوه دریافت داده برای یک نماد/تایم‌فریم/نوع داده خاص از یک منبع.
    """
    INSTRUMENT_SOURCE_STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('SUBSCRIBED', _('Subscribed')),
        ('UNSUBSCRIBED', _('Unsubscribed')),
        ('ERROR', _('Error')),
    ]
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
        related_name="market_data_configs",
        verbose_name=_("Instrument")
    )
    data_source = models.ForeignKey(
        "market_data.DataSource",
        on_delete=models.PROTECT, # اگر DataSource حذف شود، کانفیگ‌ها حذف نشوند
        related_name="configs",
        verbose_name=_("Data Source")
    )
    timeframe = models.CharField(max_length=16, verbose_name=_("Timeframe"))  # e.g., 1m, 5m, 1h, 1d
    data_type = models.CharField(
        max_length=32,
        choices=[
            ('TICK', _('Tick Data')),
            ('OHLCV', _('OHLCV')),
            ('ORDER_BOOK', _('Order Book')),
            ('TRADES', _('Trades')),
            ('INDEX', _('Index')),
            ('FUNDING_RATE', _('Funding Rate')),
            ('LIQUIDATION', _('Liquidation')),
            ('OPEN_INTEREST', _('Open Interest')),
        ],
        verbose_name=_("Data Type")
    )
    is_realtime = models.BooleanField(default=False, verbose_name=_("Is Real-time"))
    is_historical = models.BooleanField(default=True, verbose_name=_("Is Historical"))
    storage_backend = models.CharField(
        max_length=32,
        choices=[
            ('POSTGRES', _('PostgreSQL')),
            ('MONGODB', _('MongoDB')),
            ('TIMESCALE', _('TimescaleDB')),
            ('INFLUXDB', _('InfluxDB')),
        ],
        default='POSTGRES',
        verbose_name=_("Storage Backend")
    )
    collection_or_table_name = models.CharField(
        max_length=128,
        verbose_name=_("Collection/ Table Name"),
        help_text=_("e.g., binance_spot_btcusdt_1m_ticks")
    )
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Sync At"))
    status = models.CharField(
        max_length=16,
        choices=INSTRUMENT_SOURCE_STATUS_CHOICES,
        default='PENDING',
        verbose_name=_("Status")
    )
    # تنظیمات پیشرفته
    depth_levels = models.IntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(500)], # محدودیت تعداد سطح سفارش
        verbose_name=_("Depth Levels (for Order Book)")
    )
    include_additional_fields = models.JSONField(default=list, blank=True, verbose_name=_("Include Additional Fields (JSON Array)"))

    class Meta:
        verbose_name = _("Market Data Config")
        verbose_name_plural = _("Market Data Configs")
        unique_together = ("instrument", "data_source", "timeframe", "data_type")

    def __str__(self):
        return f"{self.instrument.symbol} ({self.timeframe} - {self.data_type}) from {self.data_source.name}"


class MarketDataSnapshot(BaseModel):
    """
    ذخیره یک نمونه داده OHLCV برای یک نماد خاص در یک زمان مشخص.
    این مدل برای داده‌های سری زمانی سریع مناسب است (مثلاً در PostgreSQL یا TimescaleDB).
    """
    config = models.ForeignKey(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name=_("Market Data Config")
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))
    open_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Open Price"))
    high_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("High Price"))
    low_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Low Price"))
    close_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Close Price"))
    volume = models.DecimalField(max_digits=30, decimal_places=8, verbose_name=_("Volume"))

    # فیلدهای اختیاری برای داده‌های پیشرفته
    best_bid = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, verbose_name=_("Best Bid"))
    best_ask = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, verbose_name=_("Best Ask"))
    bid_size = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True, verbose_name=_("Bid Size"))
    ask_size = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True, verbose_name=_("Ask Size"))
    quote_volume = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True, verbose_name=_("Quote Asset Volume"))
    number_of_trades = models.IntegerField(null=True, blank=True, verbose_name=_("Number of Trades"))
    taker_buy_base_asset_volume = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True, verbose_name=_("Taker Buy Base Asset Volume"))
    taker_buy_quote_asset_volume = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True, verbose_name=_("Taker Buy Quote Asset Volume"))

    # فیلدی برای داده‌های اضافی (قابل گسترش)
    additional_data = models.JSONField(default=dict, blank=True, verbose_name=_("Additional Data (JSON)"))

    class Meta:
        verbose_name = _("Market Data Snapshot")
        verbose_name_plural = _("Market Data Snapshots")
        # برای کوئری‌های سریع بر اساس زمان و نماد
        indexes = [
            models.Index(fields=['config', '-timestamp']), # برای کوئری از آخرین داده
            models.Index(fields=['timestamp']),
            models.Index(fields=['config', 'timestamp']), # برای بازه زمانی روی یک کانفیگ
        ]
        # می‌توانید از TimescaleDB Hypertable برای این مدل استفاده کنید:
        # db_table = "market_data_snapshot"  # اگر با TimescaleDB کار می‌کنید

    def __str__(self):
        return f"{self.config.instrument.symbol} at {self.timestamp} - C:{self.close_price}"


class MarketDataOrderBook(BaseModel):
    """
    ذخیره ساختار عمیق سفارش (Order Book) برای یک نماد خاص در یک زمان مشخص.
    این مدل برای تحلیل‌های پیشرفته و سیگنال‌های مبتنی بر ساختار سفارش مناسب است.
    """
    config = models.ForeignKey(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="order_books",
        verbose_name=_("Market Data Config")
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))
    bids = models.JSONField(default=list, verbose_name=_("Bids (JSON Array of [Price, Quantity])")) # مثلاً [[price1, qty1], [price2, qty2], ...]
    asks = models.JSONField(default=list, verbose_name=_("Asks (JSON Array of [Price, Quantity])")) # مثلاً [[price1, qty1], [price2, qty2], ...]
    sequence = models.BigIntegerField(null=True, blank=True, verbose_name=_("Sequence Number (if provided by source)"))
    checksum = models.CharField(max_length=64, null=True, blank=True, verbose_name=_("Checksum (if provided by source)"))

    class Meta:
        verbose_name = _("Market Data Order Book")
        verbose_name_plural = _("Market Data Order Books")
        indexes = [
            models.Index(fields=['config', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Order Book for {self.config.instrument.symbol} at {self.timestamp}"


class MarketDataTick(BaseModel):
    """
    ذخیره داده تیک (Tick) - یک معامله یا تغییر قیمت.
    مناسب برای تحلیل‌های بسیار پویا و محاسباتی مانند VWAP.
    """
    config = models.ForeignKey(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="ticks",
        verbose_name=_("Market Data Config")
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))
    price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Price"))
    quantity = models.DecimalField(max_digits=30, decimal_places=8, verbose_name=_("Quantity"))
    side = models.CharField(max_length=4, choices=[('BUY', _('Buy')), ('SELL', _('Sell'))], verbose_name=_("Side"))
    trade_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Trade ID (if provided by source)"))

    class Meta:
        verbose_name = _("Market Data Tick")
        verbose_name_plural = _("Market Data Ticks")
        indexes = [
            models.Index(fields=['config', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['config', 'side']),
        ]

    def __str__(self):
        return f"Tick: {self.side} {self.quantity} @ {self.price} for {self.config.instrument.symbol} at {self.timestamp}"


class MarketDataSyncLog(BaseModel):
    """
    ثبت لاگ همگام‌سازی داده (برای ردیابی و اشکال‌زدایی).
    """
    config = models.ForeignKey(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name=_("Market Data Config")
    )
    start_time = models.DateTimeField(verbose_name=_("Sync Start Time"))
    end_time = models.DateTimeField(verbose_name=_("Sync End Time"))
    status = models.CharField(
        max_length=16,
        choices=[
            ('SUCCESS', _('Success')),
            ('FAILED', _('Failed')),
            ('PARTIAL', _('Partial Success')),
        ],
        verbose_name=_("Status")
    )
    records_synced = models.IntegerField(default=0, verbose_name=_("Records Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    class Meta:
        verbose_name = _("Market Data Sync Log")
        verbose_name_plural = _("Market Data Sync Logs")
        ordering = ['-start_time']

    def __str__(self):
        return f"Sync Log for {self.config} - {self.status} at {self.start_time}"


class MarketDataCache(BaseModel):
    """
    مدلی اختیاری برای کش کردن داده‌های اخیر جهت دسترسی سریع.
    می‌تواند در Redis یا یک جدول جداگانه در پایگاه داده ذخیره شود.
    """
    config = models.OneToOneField(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="cache",
        verbose_name=_("Market Data Config")
    )
    latest_snapshot = models.JSONField(default=dict, blank=True, verbose_name=_("Latest Snapshot (JSON)"))
    cached_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Cached At"))

    class Meta:
        verbose_name = _("Market Data Cache")
        verbose_name_plural = _("Market Data Caches")

    def __str__(self):
        return f"Cache for {self.config}"
