# apps/market_data/models.py
from django.db import models
from apps.core.models import BaseModel


class DataSource(BaseModel):
    """
    برای تعریف منابع داده (مانند API یک صرافی یا یک فایل CSV).
    """
    name = models.CharField(max_length=128, unique=True)  # e.g., 'Binance API', 'Coinbase Pro API'
    type = models.CharField(max_length=32)  # e.g., 'REST', 'WebSocket', 'FILE'
    config = models.JSONField(default=dict, blank=True)  # اطلاعات پیکربندی اضافی

    def __str__(self):
        return self.name


class MarketDataConfig(BaseModel):
    """
    برای تنظیم نحوه دریافت و ذخیره داده‌های بازار برای هر نماد.
    این مدل به یک کالکشن در MongoDB اشاره می‌کند.
    """
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE,
                                   related_name="market_data_configs")
    timeframe = models.CharField(max_length=16)  # e.g., '1m', '5m', '1h', '1d'
    data_source = models.ForeignKey("market_data.DataSource", on_delete=models.PROTECT,
                                    related_name="market_data_configs")

    # نام کالکشن در MongoDB که داده‌ها در آن ذخیره می‌شوند
    collection_name = models.CharField(max_length=128, help_text="e.g., binance_spot_btcusdt_1m")

    is_realtime = models.BooleanField(default=False, help_text="If true, this config is for real-time data.")
    is_historical = models.BooleanField(default=True, help_text="If true, this config is for historical data.")

    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("instrument", "timeframe", "data_source")

    def __str__(self):
        return f"{self.instrument.symbol} ({self.timeframe}) from {self.data_source.name}"
