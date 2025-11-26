# apps/instruments/models.py
from django.db import models

class InstrumentGroup(models.Model):
    """برای گروه‌بندی نمادها (مثلاً: Crypto, Stock, Forex)"""
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Instrument(models.Model):
    """برای تعریف نمادهای معاملاتی (مثلاً: BTCUSDT, AAPL)"""
    symbol = models.CharField(max_length=64)  # e.g. BTCUSDT
    name = models.CharField(max_length=128, blank=True)
    group = models.ForeignKey("instruments.InstrumentGroup", on_delete=models.PROTECT, related_name="instruments")

    base_asset = models.CharField(max_length=32, blank=True)  # e.g. BTC
    quote_asset = models.CharField(max_length=32, blank=True) # e.g. USDT

    # exchange را بعداً اضافه می‌کنیم چون به مدل Exchange نیاز دارد
    # exchange = models.ForeignKey("exchanges.Exchange", null=True, blank=True, on_delete=models.SET_NULL, related_name="instruments")

    tick_size = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    lot_size = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        # برای جلوگیری از تکرار یک نماد در یک صرافی
        # در حال حاضر چون exchange نداریم، symbol را منحصر به فرد نگه می‌داریم
        constraints = [
            models.UniqueConstraint(fields=['symbol'], name='unique_instrument_symbol')
        ]

    def __str__(self):
        return f"{self.symbol} ({self.group.name})"

class IndicatorGroup(models.Model):
    """برای گروه‌بندی اندیکاتورها (مثلاً: Trend, Oscillator, Volume)"""
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Indicator(models.Model):
    """برای تعریف اندیکاتورهای تکنیکال (مثلاً: RSI, MACD, EMA)"""
    name = models.CharField(max_length=64)  # RSI, MACD, EMA
    code = models.CharField(max_length=64, unique=True) # RSI, MACD, EMA
    group = models.ForeignKey("instruments.IndicatorGroup", on_delete=models.PROTECT, related_name="indicators")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class IndicatorParameter(models.Model):
    """برای نگهداری پارامترهای هر اندیکاتور (مثلاً: period, fast_period)"""
    indicator = models.ForeignKey("instruments.Indicator", on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=64)  # period, fast_period, slow_period
    data_type = models.CharField(max_length=16)  # int, float, bool, choice
    default_value = models.CharField(max_length=64, blank=True)
    min_value = models.CharField(max_length=64, blank=True)
    max_value = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = ("indicator", "name")

    def __str__(self):
        return f"{self.indicator.name} - {self.name}"