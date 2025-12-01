# apps/market_data/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class DataSource(BaseModel):
    """
    تعریف منابع داده (مثل Binance, CoinGecko, LBank, LBANK_WS).
    """
    TYPE_CHOICES = [
        ('REST_API', _('REST API')),
        ('WEBSOCKET', _('WebSocket')),
        ('FILE', _('File Import')),
        ('DATABASE', _('Database')),
    ]
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, verbose_name=_("Type"))
    base_url = models.URLField(blank=True, verbose_name=_("Base URL"))
    ws_url = models.URLField(blank=True, verbose_name=_("WebSocket URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    rate_limit_per_minute = models.IntegerField(default=1200, verbose_name=_("Rate Limit Per Minute"))
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuration (JSON)"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Data Source")
        verbose_name_plural = _("Data Sources")


class MarketDataConfig(BaseModel):
    """
    پیکربندی نحوه دریافت داده برای یک نماد/تایم‌فریم خاص از یک منبع.
    """
    INSTRUMENT_SOURCE_STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('SUBSCRIBED', _('Subscribed')),
        ('UNSUBSCRIBED', _('Unsubscribed')),
        ('ERROR', _('Error')),
    ]
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="market_data_configs",
        verbose_name=_("Instrument")
    )
    data_source = models.ForeignKey(
        "market_data.DataSource",
        on_delete=models.PROTECT,
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
    # فیلدهای امنیتی و احراز هویت
    api_credential = models.ForeignKey(
        "connectors.APICredential",  # فرض می‌کنیم از اپلیکیشن connectors استفاده شود
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("API Credential (if required)")
    )

    class Meta:
        verbose_name = _("Market Data Config")
        verbose_name_plural = _("Market Data Configs")
        unique_together = ("instrument", "data_source", "timeframe", "data_type")

    def __str__(self):
        return f"{self.instrument.symbol} ({self.timeframe}) from {self.data_source.name}"


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

    # فیلدی برای داده‌های اضافی (قابل گسترش)
    additional_data = models.JSONField(default=dict, blank=True, verbose_name=_("Additional Data (JSON)"))

    class Meta:
        verbose_name = _("Market Data Snapshot")
        verbose_name_plural = _("Market Data Snapshots")
        # برای کوئری‌های سریع بر اساس زمان و نماد
        indexes = [
            models.Index(fields=['config', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
        # می‌توانید از TimescaleDB Hypertable برای این مدل استفاده کنید:
        # db_table = "market_data_snapshot"  # اگر با TimescaleDB کار می‌کنید

    def __str__(self):
        return f"{self.config.instrument.symbol} at {self.timestamp} - C:{self.close_price}"


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
    error_message = models.TextField(blank=True, verbose_name=_("Error Message")
    )
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    class Meta:
        verbose_name = _("Market Data Sync Log")
        verbose_name_plural = _("Market Data Sync Logs")
        ordering = ['-start_time']

    def __str__(self):
        return f"Sync Log for {self.config} - {self.status}"