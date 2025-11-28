# # apps/instruments/models.py
# from django.db import models
# from apps.core.models import BaseModel
#
# class InstrumentGroup(BaseModel):
#     """برای گروه‌بندی نمادها (مثلاً: Crypto, Stock, Forex)"""
#     name = models.CharField(max_length=64, unique=True)
#     description = models.TextField(blank=True)
#
#     def __str__(self):
#         return self.name
#
# class Instrument(models.Model):
#     """برای تعریف نمادهای معاملاتی (مثلاً: BTCUSDT, AAPL)"""
#     symbol = models.CharField(max_length=64)  # e.g. BTCUSDT
#     name = models.CharField(max_length=128, blank=True)
#     group = models.ForeignKey("instruments.InstrumentGroup", on_delete=models.PROTECT, related_name="instruments")
#
#     base_asset = models.CharField(max_length=32, blank=True)  # e.g. BTC
#     quote_asset = models.CharField(max_length=32, blank=True) # e.g. USDT
#
#     # exchange را بعداً اضافه می‌کنیم چون به مدل Exchange نیاز دارد
#     # exchange = models.ForeignKey("exchanges.Exchange", null=True, blank=True, on_delete=models.SET_NULL, related_name="instruments")
#
#     tick_size = models.DecimalField(max_digits=32, decimal_places=16, default=0)
#     lot_size = models.DecimalField(max_digits=32, decimal_places=16, default=0)
#     is_active = models.BooleanField(default=True)
#
#     class Meta:
#         # برای جلوگیری از تکرار یک نماد در یک صرافی
#         # در حال حاضر چون exchange نداریم، symbol را منحصر به فرد نگه می‌داریم
#         constraints = [
#             models.UniqueConstraint(fields=['symbol'], name='unique_instrument_symbol')
#         ]
#
#     def __str__(self):
#         return f"{self.symbol} ({self.group.name})"
#
# class IndicatorGroup(models.Model):
#     """برای گروه‌بندی اندیکاتورها (مثلاً: Trend, Oscillator, Volume)"""
#     name = models.CharField(max_length=64, unique=True)
#     description = models.TextField(blank=True)
#
#     def __str__(self):
#         return self.name
#
# class Indicator(models.Model):
#     """برای تعریف اندیکاتورهای تکنیکال (مثلاً: RSI, MACD, EMA)"""
#     name = models.CharField(max_length=64)  # RSI, MACD, EMA
#     code = models.CharField(max_length=64, unique=True) # RSI, MACD, EMA
#     group = models.ForeignKey("instruments.IndicatorGroup", on_delete=models.PROTECT, related_name="indicators")
#     description = models.TextField(blank=True)
#
#     def __str__(self):
#         return self.name
#
# class IndicatorParameter(models.Model):
#     """برای نگهداری پارامترهای هر اندیکاتور (مثلاً: period, fast_period)"""
#     indicator = models.ForeignKey("instruments.Indicator", on_delete=models.CASCADE, related_name="parameters")
#     name = models.CharField(max_length=64)  # period, fast_period, slow_period
#     data_type = models.CharField(max_length=16)  # int, float, bool, choice
#     default_value = models.CharField(max_length=64, blank=True)
#     min_value = models.CharField(max_length=64, blank=True)
#     max_value = models.CharField(max_length=64, blank=True)
#
#     class Meta:
#         unique_together = ("indicator", "name")
#
#     def __str__(self):
#         return f"{self.indicator.name} - {self.name}"

### New Code : #########################################################


# apps/instruments/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class InstrumentGroup(BaseModel):
    """
    گروه‌بندی نمادها (مثلاً: Crypto, Stock, Forex).
    """
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Instrument Group")
        verbose_name_plural = _("Instrument Groups")


class InstrumentCategory(BaseModel):
    """
    دسته‌بندی انواع نمادها (مثلاً: SPOT, FUTURES, PERPETUAL, OPTION).
    """
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Category Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Instrument Category")
        verbose_name_plural = _("Instrument Categories")


class Instrument(BaseModel):
    """
    نماد معاملاتی (مثلاً: BTCUSDT).
    """
    symbol = models.CharField(max_length=64, verbose_name=_("Symbol"))  # e.g. BTCUSDT
    name = models.CharField(max_length=128, blank=True, verbose_name=_("Full Name"))  # e.g. Bitcoin / Tether
    group = models.ForeignKey(
        "instruments.InstrumentGroup",
        on_delete=models.PROTECT,
        related_name="instruments",
        verbose_name=_("Group")
    )
    category = models.ForeignKey(
        "instruments.InstrumentCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instruments",
        verbose_name=_("Category")
    )
    base_asset = models.CharField(max_length=32, blank=True, verbose_name=_("Base Asset"))  # e.g. BTC
    quote_asset = models.CharField(max_length=32, blank=True, verbose_name=_("Quote Asset"))  # e.g. USDT
    # اطلاعات دقت معاملاتی
    tick_size = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Tick Size"))
    lot_size = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Lot Size"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    # اطلاعات اضافی
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata (JSON)"))

    class Meta:
        verbose_name = _("Instrument")
        verbose_name_plural = _("Instruments")
        constraints = [
            models.UniqueConstraint(
                fields=['symbol'],
                name='unique_instrument_symbol'
            )
        ]

    def __str__(self):
        return f"{self.symbol} ({self.group.name})"


class InstrumentExchangeMap(BaseModel):
    """
    نگاشت نمادها به صرافی‌ها (چون نماد در هر صرافی ممکن است ویژگی‌های متفاوتی داشته باشد).
    """
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="exchange_mappings",
        verbose_name=_("Instrument")
    )
    exchange = models.ForeignKey(
        "exchanges.Exchange",  # این مدل باید قبلاً تعریف شده باشد یا به صورت رشته ارجاع داده شود
        on_delete=models.CASCADE,
        related_name="instrument_mappings",
        verbose_name=_("Exchange")
    )
    exchange_symbol = models.CharField(max_length=64, verbose_name=_("Exchange Symbol"))  # e.g. BTCUSDT, BTCUSD_PERP
    tick_size = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Exchange Tick Size"))
    lot_size = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Exchange Lot Size"))
    min_notional = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Min Notional"))
    max_notional = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Max Notional"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active on Exchange"))

    class Meta:
        verbose_name = _("Instrument-Exchange Map")
        verbose_name_plural = _("Instrument-Exchange Maps")
        unique_together = ("exchange", "exchange_symbol")  # یک نماد در یک صرافی فقط یک بار وجود داشته باشد

    def __str__(self):
        return f"{self.exchange.name} - {self.exchange_symbol}"


class IndicatorGroup(BaseModel):
    """
    گروه‌بندی اندیکاتورها (مثلاً: Trend, Oscillator, Volume).
    """
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Group Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Indicator Group")
        verbose_name_plural = _("Indicator Groups")


class Indicator(BaseModel):
    """
    تعریف اندیکاتورهای تکنیکال (مثلاً: RSI, MACD, EMA).
    """
    name = models.CharField(max_length=64, verbose_name=_("Display Name"))  # RSI, MACD, EMA
    code = models.CharField(max_length=64, unique=True, verbose_name=_("Code"))  # RSI, MACD, EMA
    group = models.ForeignKey(
        "instruments.IndicatorGroup",
        on_delete=models.PROTECT,
        related_name="indicators",
        verbose_name=_("Group")
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    # فیلدهای امنیتی و اطلاعات بیشتر
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_builtin = models.BooleanField(default=True, verbose_name=_("Is Built-in"))  # اگر از قبل تعریف شده
    version = models.CharField(max_length=32, default="1.0.0", verbose_name=_("Version"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Indicator")
        verbose_name_plural = _("Indicators")


class IndicatorParameter(BaseModel):
    """
    پارامترهای هر اندیکاتور (مثلاً: period, fast_period).
    """
    DATA_TYPE_CHOICES = [
        ('int', _('Integer')),
        ('float', _('Float')),
        ('bool', _('Boolean')),
        ('str', _('String')),
        ('choice', _('Choice List')),
    ]
    indicator = models.ForeignKey(
        "instruments.Indicator",
        on_delete=models.CASCADE,
        related_name="parameters",
        verbose_name=_("Indicator")
    )
    name = models.CharField(max_length=64, verbose_name=_("Parameter Name"))  # period, fast_period
    display_name = models.CharField(max_length=128, verbose_name=_("Display Name"))
    data_type = models.CharField(max_length=16, choices=DATA_TYPE_CHOICES, verbose_name=_("Data Type"))
    default_value = models.TextField(blank=True, verbose_name=_("Default Value"))
    min_value = models.TextField(blank=True, verbose_name=_("Minimum Value"))
    max_value = models.TextField(blank=True, verbose_name=_("Maximum Value"))
    choices = models.TextField(blank=True, verbose_name=_("Choices (comma-separated)"), help_text=_("Used if data_type is 'choice'"))

    class Meta:
        verbose_name = _("Indicator Parameter")
        verbose_name_plural = _("Indicator Parameters")
        unique_together = ("indicator", "name")

    def __str__(self):
        return f"{self.indicator.name} - {self.name}"


class IndicatorTemplate(BaseModel):
    """
    ذخیره پیکربندی‌های از پیش تعریف شده اندیکاتورها برای استفاده در استراتژی‌ها.
    """
    name = models.CharField(max_length=128, verbose_name=_("Template Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    indicator = models.ForeignKey(
        "instruments.Indicator",
        on_delete=models.PROTECT,
        verbose_name=_("Indicator")
    )
    parameters = models.JSONField(verbose_name=_("Parameters (JSON)"))  # e.g., {"period": 14, "ma_type": "SMA"}
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Indicator Template")
        verbose_name_plural = _("Indicator Templates")


class PriceActionPattern(BaseModel):
    """
    الگوهای اکشن قیمتی (مثلاً: Support/Resistance, Trendline, Fibonacci).
    """
    name = models.CharField(max_length=128, verbose_name=_("Pattern Name"))
    code = models.CharField(max_length=64, unique=True, verbose_name=_("Code"))  # e.g., SUP_RES, TRENDLINE
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Price Action Pattern")
        verbose_name_plural = _("Price Action Patterns")


class SmartMoneyConcept(BaseModel):
    """
    مفاهیم اسمارت مانی (مثلاً: OrderBlock, FairValueGap, LiquidityZone).
    """
    name = models.CharField(max_length=128, verbose_name=_("SMC Name"))
    code = models.CharField(max_length=64, unique=True, verbose_name=_("Code"))  # e.g., OB, FVG, LZ
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Smart Money Concept")
        verbose_name_plural = _("Smart Money Concepts")


class AIMetric(BaseModel):
    """
    متغیرهای متریک هوش مصنوعی (مثلاً: model score, probability of direction).
    """
    name = models.CharField(max_length=128, verbose_name=_("Metric Name"))
    code = models.CharField(max_length=64, unique=True, verbose_name=_("Code"))  # e.g., MODEL_SCORE, PROB_UP
    description = models.TextField(blank=True, verbose_name=_("Description"))
    data_type = models.CharField(max_length=16, default='float', verbose_name=_("Data Type"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("AI Metric")
        verbose_name_plural = _("AI Metrics")
