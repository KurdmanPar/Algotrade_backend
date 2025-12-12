# apps/instruments/models.py

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel # فرض بر این است که وجود دارد
from apps.exchanges.models import Exchange # فرض بر این است که مدل Exchange وجود دارد
# --- واردات فایل‌های جدید ---
from . import managers # منیجرهای سفارشی
from . import helpers # توابع کمکی
from . import exceptions # استثناهای سفارشی
# ----------------------------

class InstrumentGroup(BaseModel):
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Instrument Group")
        verbose_name_plural = _("Instrument Groups")


class InstrumentCategory(BaseModel):
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Category Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    supports_leverage = models.BooleanField(default=False, verbose_name=_("Supports Leverage"))
    supports_shorting = models.BooleanField(default=False, verbose_name=_("Supports Shorting"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Instrument Category")
        verbose_name_plural = _("Instrument Categories")


class Instrument(BaseModel):
    """
    Represents a trading instrument (e.g., BTCUSDT).
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
    tick_size = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Tick Size"))
    lot_size = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Lot Size"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    launch_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Launch Date"))
    delisting_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Delisting Date"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata (JSON)"))

    # --- اضافه شده برای سازگاری با فایل‌های جدید ---
    objects = managers.InstrumentManager() # استفاده از منیجر سفارشی

    class Meta:
        verbose_name = _("Instrument")
        verbose_name_plural = _("Instruments")
        constraints = [
            models.UniqueConstraint(
                fields=['symbol'],
                name='unique_instrument_symbol'
            )
        ]
        # اضافه کردن ایندکس‌ها از طریق منیجر یا در اینجا
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['group', 'category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.name})"

    def clean(self):
        """
        Validates the model instance.
        Uses helpers for complex validations.
        """
        super().clean()
        # مثال: اعتبارسنجی فیلد metadata یا سایر فیلدها
        # if self.metadata.get('some_key') not in allowed_values:
        #     raise ValidationError({'metadata': _('Invalid value for some_key in metadata.')})

        # اعتبارسنجی tick_size و lot_size (مثال ساده)
        if self.tick_size and self.tick_size <= 0:
            raise ValidationError({'tick_size': _('Tick size must be positive.')})
        if self.lot_size and self.lot_size <= 0:
            raise ValidationError({'lot_size': _('Lot size must be positive.')})

    @property
    def is_delisted(self):
        return self.delisting_date and self.delisting_date < timezone.now()

    @property
    def is_listed(self):
        return self.is_active and not self.is_delisted


class InstrumentExchangeMap(BaseModel):
    """
    Maps instruments to specific exchanges, as properties (like tick/lot size) can vary.
    """
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="exchange_mappings",
        verbose_name=_("Instrument")
    )
    exchange = models.ForeignKey(
        "exchanges.Exchange", # فرض بر این است که مدل وجود دارد
        on_delete=models.CASCADE,
        related_name="instrument_mappings",
        verbose_name=_("Exchange")
    )
    exchange_symbol = models.CharField(max_length=64, verbose_name=_("Exchange Symbol")) # e.g. BTCUSDT, BTCUSD_PERP
    tick_size = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Exchange Tick Size"))
    lot_size = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Exchange Lot Size"))
    min_notional = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Min Notional"))
    max_notional = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Max Notional"))
    min_lot_size = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Min Lot Size"))
    max_lot_size = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Max Lot Size"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active on Exchange"))
    is_margin_enabled = models.BooleanField(default=False, verbose_name=_("Is Margin Enabled"))
    is_funding_enabled = models.BooleanField(default=False, verbose_name=_("Is Funding Enabled"))
    max_leverage = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name=_("Max Leverage"))
    initial_margin_ratio = models.DecimalField(max_digits=10, decimal_places=6, default=0, verbose_name=_("Initial Margin Ratio"))
    maintenance_margin_ratio = models.DecimalField(max_digits=10, decimal_places=6, default=0, verbose_name=_("Maintenance Margin Ratio"))
    listing_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Listing Date on Exchange"))
    delisting_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Delisting Date on Exchange"))

    # --- اضافه شده برای سازگاری با فایل‌های جدید ---
    objects = managers.InstrumentExchangeMapManager() # استفاده از منیجر سفارشی

    class Meta:
        verbose_name = _("Instrument-Exchange Map")
        verbose_name_plural = _("Instrument-Exchange Maps")
        unique_together = ("exchange", "exchange_symbol") # یک نماد در یک صرافی فقط یک بار وجود داشته باشد
        indexes = [
            models.Index(fields=['exchange', 'is_active']),
            models.Index(fields=['instrument', 'is_active']),
        ]

    def __str__(self):
        return f"{self.exchange.name} - {self.exchange_symbol}"

    def clean(self):
        """
        Validates the model instance.
        """
        super().clean()
        if self.min_notional and self.max_notional and self.min_notional > self.max_notional:
            raise ValidationError(_('Min notional cannot be greater than max notional.'))
        if self.min_lot_size and self.max_lot_size and self.min_lot_size > self.max_lot_size:
            raise ValidationError(_('Min lot size cannot be greater than max lot size.'))
        if self.max_leverage and self.max_leverage < 1:
            raise ValidationError(_('Max leverage must be at least 1.'))
        if self.initial_margin_ratio and self.maintenance_margin_ratio and self.initial_margin_ratio < self.maintenance_margin_ratio:
            raise ValidationError(_('Initial margin ratio cannot be less than maintenance margin ratio.'))

    @property
    def is_delisted_on_exchange(self):
        return self.delisting_date and self.delisting_date < timezone.now()

    @property
    def is_listed_on_exchange(self):
        return self.is_active and not self.is_delisted_on_exchange


# --- مدل‌های جدید ---
class IndicatorGroup(BaseModel):
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Group Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Indicator Group")
        verbose_name_plural = _("Indicator Groups")


class Indicator(BaseModel):
    """
    Defines technical indicators (e.g., RSI, MACD, EMA).
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
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_builtin = models.BooleanField(default=True, verbose_name=_("Is Built-in"))
    version = models.CharField(max_length=32, default="1.0.0", verbose_name=_("Version"))
    calculation_frequency = models.CharField(max_length=16, default='1m', verbose_name=_("Calculation Frequency"))
    requires_price_data = models.BooleanField(default=True, verbose_name=_("Requires Price Data"))
    output_types = models.JSONField(default=list, verbose_name=_("Output Types (e.g., line, histogram, signal)"))

    objects = managers.IndicatorManager() # استفاده از منیجر سفارشی

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = _("Indicator")
        verbose_name_plural = _("Indicators")


class IndicatorParameter(BaseModel):
    """
    Parameters for each indicator (e.g., period, fast_period).
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
    Stores pre-defined configurations of indicators for use in strategies.
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

    objects = managers.IndicatorTemplateManager() # استفاده از منیجر سفارشی

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Indicator Template")
        verbose_name_plural = _("Indicator Templates")


class PriceActionPattern(BaseModel):
    """
    Price action patterns (e.g., Support/Resistance, Trendline, Fibonacci).
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
    Smart Money Concepts (e.g., OrderBlock, FairValueGap, LiquidityZone).
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
    AI Metric variables (e.g., model score, probability of direction).
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


class InstrumentWatchlist(BaseModel):
    """
    A list of selected instruments by a user or system.
    """
    name = models.CharField(max_length=128, verbose_name=_("Watchlist Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instrument_watchlists",
        verbose_name=_("Owner")
    )
    instruments = models.ManyToManyField(
        Instrument,
        related_name="watchlists",
        verbose_name=_("Instruments")
    )
    is_public = models.BooleanField(default=False, verbose_name=_("Is Public"))

    objects = managers.InstrumentWatchlistManager() # استفاده از منیجر سفارشی

    class Meta:
        verbose_name = _("Instrument Watchlist")
        verbose_name_plural = _("Instrument Watchlists")

    def __str__(self):
        return f"{self.name} (by {self.owner.username})"
