# apps/market_data/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class DataSource(BaseModel):
    """
    تعریف منابع داده (مانند API یک صرافی یا یک فایل CSV).
    """
    SOURCE_TYPE_CHOICES = [
        ('REST', _('REST API')),
        ('WEBSOCKET', _('WebSocket')),
        ('FILE', _('File Import')),
        ('FTP', _('FTP')),
        ('DATABASE', _('Database')),
    ]
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Data Source Name"))
    type = models.CharField(max_length=32, choices=SOURCE_TYPE_CHOICES, verbose_name=_("Source Type"))
    base_url = models.URLField(blank=True, verbose_name=_("Base URL"))
    rate_limit_per_minute = models.IntegerField(default=100, verbose_name=_("Rate Limit Per Minute"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuration (JSON)"))
    # امنیت: اطلاعات احراز هویت منبع (مثلاً API Key/Secret یا نام کاربری/رمز) ممکن است نیاز به رمزنگاری داشته باشد
    # در اینجا فقط یک فیلد کلی ارائه شده. در صورت نیاز، می‌توان از فیلدهای رمزنگاری شده استفاده کرد.
    credentials_encrypted = models.JSONField(default=dict, blank=True, verbose_name=_("Encrypted Credentials (JSON)"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Data Source")
        verbose_name_plural = _("Data Sources")


class MarketDataConfig(BaseModel):
    """
    تنظیم نحوه دریافت و ذخیره داده‌های بازار برای هر نماد.
    این مدل به یک کالکشن در MongoDB یا جدول در PostgreSQL اشاره می‌کند.
    """
    STORAGE_BACKEND_CHOICES = [
        ('POSTGRES', _('PostgreSQL')),
        ('MONGODB', _('MongoDB')),
        ('TIMESCALE', _('TimescaleDB')),
    ]
    DATA_FORMAT_CHOICES = [
        ('OHLCV', _('OHLCV')),
        ('TICK', _('Tick Data')),
        ('ORDER_BOOK', _('Order Book')),
        ('CUSTOM', _('Custom Format')),
    ]
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="market_data_configs",
        verbose_name=_("Instrument")
    )
    timeframe = models.CharField(max_length=16, verbose_name=_("Timeframe"))  # e.g., '1m', '5m', '1h', '1d'
    data_source = models.ForeignKey(
        "market_data.DataSource",
        on_delete=models.PROTECT,
        related_name="market_data_configs",
        verbose_name=_("Data Source")
    )
    storage_backend = models.CharField(
        max_length=16,
        choices=STORAGE_BACKEND_CHOICES,
        default='MONGODB',
        verbose_name=_("Storage Backend")
    )
    data_format = models.CharField(
        max_length=16,
        choices=DATA_FORMAT_CHOICES,
        default='OHLCV',
        verbose_name=_("Data Format")
    )
    # نام کالکشن یا جدول در بک‌اند ذخیره‌سازی
    collection_name = models.CharField(
        max_length=128,
        help_text=_("e.g., binance_spot_btcusdt_1m"),
        verbose_name=_("Collection/ Table Name")
    )
    is_realtime = models.BooleanField(default=False, verbose_name=_("Is Real-time"))
    is_historical = models.BooleanField(default=True, verbose_name=_("Is Historical"))
    preprocessing_pipeline = models.JSONField(default=dict, blank=True, verbose_name=_("Preprocessing Pipeline (JSON)"))
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Sync At"))
    last_successful_sync_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Successful Sync At"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        verbose_name = _("Market Data Config")
        verbose_name_plural = _("Market Data Configs")
        unique_together = ("instrument", "timeframe", "data_source")

    def __str__(self):
        return f"{self.instrument.symbol} ({self.timeframe}) from {self.data_source.name}"


class MarketDataSyncLog(BaseModel):
    """
    لاگ کردن تاریخچه همگام‌سازی داده (هم تاریخی و هم لحظه‌ای).
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('RUNNING', _('Running')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed')),
        ('CANCELLED', _('Cancelled')),
    ]
    config = models.ForeignKey(
        "market_data.MarketDataConfig",
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name=_("Market Data Config")
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("Status"))
    start_time = models.DateTimeField(verbose_name=_("Sync Start Time"))
    end_time = models.DateTimeField(null=True, blank=True, verbose_name=_("Sync End Time"))
    records_synced = models.PositiveIntegerField(default=0, verbose_name=_("Number of Records Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message")
    )
    # اطلاعات بیشتر در مورد داده‌های همگام‌سازی شده (مثلاً بازه زمانی)
    sync_details = models.JSONField(default=dict, blank=True, verbose_name=_("Sync Details (JSON)"))

    class Meta:
        verbose_name = _("Market Data Sync Log")
        verbose_name_plural = _("Market Data Sync Logs")
        # ممکن است بخواهید بر اساس تاریخ شروع و config جستجو کنید
        # indexes = [
        #     models.Index(fields=['config', 'start_time']),
        # ]

    def __str__(self):
        return f"{self.config} - {self.status} at {self.start_time}"


class MarketDataSnapshot(BaseModel):
    """
    ذخیره سریع داده‌های OHLCV در پایگاه داده رابطه‌ای برای کاربردهای سریع (مثلاً نمایش در داشبورد).
    برای داده‌های حجیم و بلادرنگ، از MongoDB یا TimescaleDB استفاده می‌شود.
    """
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name=_("Instrument")
    )
    timeframe = models.CharField(max_length=16, verbose_name=_("Timeframe"))  # e.g., '1m', '5m', '1h'
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))
    open_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Open Price"))
    high_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("High Price"))
    low_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Low Price"))
    close_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Close Price"))
    volume = models.DecimalField(max_digits=30, decimal_places=8, verbose_name=_("Volume"))

    class Meta:
        verbose_name = _("Market Data Snapshot")
        verbose_name_plural = _("Market Data Snapshots")
        unique_together = ("instrument", "timeframe", "timestamp")
        # برای کوئری‌های سریع بر اساس نماد، تایم‌فریم و زمان
        indexes = [
            models.Index(fields=['instrument', 'timeframe', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.instrument.symbol} - {self.timeframe} - {self.timestamp}"