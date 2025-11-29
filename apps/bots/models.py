# apps/bots/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Bot(BaseModel):
    """
    مدل اصلی برای هر ربات معاملاتی که کاربر ایجاد می‌کند.
    """
    BOT_TYPE_CHOICES = [
        ("BUY_ONLY", _("Buy Only")),
        ("SELL_ONLY", _("Sell Only")),
        ("LONG_SHORT", _("Long & Short")),
        ("GRID", _("Grid Bot")),
        ("DCA", _("Dollar Cost Averaging")),
        ("ARBITRAGE", _("Arbitrage")),
        ("MEAN_REVERSION", _("Mean Reversion")),
        ("TREND_FOLLOWING", _("Trend Following")),
    ]
    STATUS_CHOICES = [
        ("INACTIVE", _("Inactive")),
        ("ACTIVE", _("Active")),
        ("PAUSED", _("Paused")),
        ("STOPPED", _("Stopped")),
        ("ERROR", _("Error")),
    ]
    MODE_CHOICES = [
        ("LIVE", _("Live Trading")),
        ("PAPER", _("Paper Trading")),
    ]
    CONTROL_CHOICES = [
        ("MANUAL", _("Manual Control by User")),
        ("AUTOMATIC", _("Automatic Control by System")),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bots",
        verbose_name=_("Owner")
    )
    name = models.CharField(max_length=128, verbose_name=_("Bot Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # اتصال به حساب کاربری در یک صرافی خاص
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.PROTECT,
        related_name="bots",
        verbose_name=_("Exchange Account")
    )
    # اتصال به نماد معاملاتی مشخص (بسیار مهم)
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="bots",
        verbose_name=_("Trading Instrument")
    )

    bot_type = models.CharField(max_length=16, choices=BOT_TYPE_CHOICES, default="LONG_SHORT", verbose_name=_("Bot Type"))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="INACTIVE", verbose_name=_("Status"))
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="PAPER", verbose_name=_("Trading Mode"))
    control_type = models.CharField(
        max_length=16,
        choices=CONTROL_CHOICES,
        default="MANUAL",
        verbose_name=_("Control Type"),
        help_text=_("How the bot is started/stopped.")
    )

    # اتصال به پروفایل ریسک (بسیار مهم)
    risk_profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bots",
        verbose_name=_("Risk Profile")
    )

    # تنظیمات کلی ربات
    max_concurrent_trades = models.IntegerField(default=1, verbose_name=_("Max Concurrent Trades"), help_text=_("Maximum number of open trades/positions."))
    max_position_size = models.DecimalField(max_digits=32, decimal_places=8, null=True, blank=True, verbose_name=_("Max Position Size"))
    max_total_capital = models.DecimalField(max_digits=32, decimal_places=8, null=True, blank=True, verbose_name=_("Max Total Capital to Use"))
    leverage = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name=_("Leverage"))
    desired_profit_target_percent = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True, verbose_name=_("Desired Profit Target (%)"),
        help_text=_("Target profit in percentage (e.g., 2.50 for 2.5%).")
    )
    max_allowed_loss_percent = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True, verbose_name=_("Max Allowed Loss (%)"),
        help_text=_("Maximum allowed loss in percentage.")
    )
    # تنظیمات حد سود/ضرر و تریلینگ استاپ
    trailing_stop_config = models.JSONField(default=dict, blank=True, verbose_name=_("Trailing Stop Config (JSON)"))

    # تنظیمات زمان‌بندی و اجرا
    schedule_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Schedule Config (JSON)"),
        help_text=_("e.g., {'start_time': '09:00', 'end_time': '17:00', 'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']}")
    )

    # تنظیمات مربوط به حالت Paper Trading
    paper_trading_balance = models.DecimalField(
        max_digits=32, decimal_places=8, default=10000, verbose_name=_("Paper Trading Balance"),
        help_text=_("Starting balance for paper trading mode.")
    )

    # فیلدهای مربوط به دیباگ و مانیتورینگ
    last_error_log = models.TextField(blank=True, verbose_name=_("Last Error Log"), help_text=_("Stores the last error message for debugging."))
    last_heartbeat_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Heartbeat At"), help_text=_("Last time the bot sent a heartbeat signal."))
    is_paused_by_system = models.BooleanField(default=False, verbose_name=_("Is Paused by System"))

    # معیارهای عملکرد کلی (برای نمایش سریع)
    performance_metrics = models.JSONField(default=dict, blank=True, verbose_name=_("Performance Metrics (JSON)"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Bot")
        verbose_name_plural = _("Bots")
        # جلوگیری از ایجاد دو ربات با نام یکسان برای یک کاربر
        unique_together = ("owner", "name")

    def __str__(self):
        return f"{self.name} ({self.instrument.symbol}) by {self.owner.email}"


class BotStrategyConfig(BaseModel):
    """
    برای اتصال یک یا چند استراتژی به یک ربات.
    """
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="strategy_configs",
        verbose_name=_("Bot")
    )
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.CASCADE,
        related_name="bot_configs",
        verbose_name=_("Strategy Version")
    )

    weight = models.FloatField(default=1.0, verbose_name=_("Weight"), help_text=_("Weight of this strategy in the bot's final decision."))
    priority = models.IntegerField(default=0, verbose_name=_("Priority"))
    is_primary = models.BooleanField(default=False, verbose_name=_("Is Primary"), help_text=_("Mark if this is the primary strategy for the bot."))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    # اجازه به کاربر برای بازنویسی پارامترهای استراتژی فقط برای این ربات خاص
    parameters_override = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Parameters Override (JSON)"),
        help_text=_("Override default strategy parameters for this specific bot.")
    )
    # نتیجه آخرین اجرای استراتژی در این ربات
    last_execution_result = models.JSONField(default=dict, blank=True, verbose_name=_("Last Execution Result (JSON)"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Bot Strategy Config")
        verbose_name_plural = _("Bot Strategy Configs")
        unique_together = ("bot", "strategy_version")

    def __str__(self):
        return f"{self.bot.name} - {self.strategy_version}"


class BotLog(BaseModel):
    """
    لاگ کردن رویدادهای مهم ربات (شروع، توقف، خطا، سیگنال دریافتی و ...).
    """
    EVENT_TYPE_CHOICES = [
        ('STARTED', _('Started')),
        ('STOPPED', _('Stopped')),
        ('PAUSED', _('Paused')),
        ('RESUMED', _('Resumed')),
        ('ERROR', _('Error')),
        ('WARNING', _('Warning')),
        ('INFO', _('Info')),
        ('SIGNAL_RECEIVED', _('Signal Received')),
        ('ORDER_PLACED', _('Order Placed')),
        ('ORDER_FILLED', _('Order Filled')),
        ('POSITION_OPENED', _('Position Opened')),
        ('POSITION_CLOSED', _('Position Closed')),
    ]
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name=_("Bot")
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES, verbose_name=_("Event Type"))
    message = models.TextField(verbose_name=_("Log Message"))
    # اطلاعات بیشتر در مورد رویداد (مثلاً جزئیات سفارش یا سیگنال)
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Bot Log")
        verbose_name_plural = _("Bot Logs")
        # ممکن است بخواهید بر اساس bot و زمان جستجو کنید
        indexes = [
            models.Index(fields=['bot', '-created_at']), # برای نمایش معکوس تاریخچه
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.bot.name} at {self.created_at}"


class BotPerformanceSnapshot(BaseModel):
    """
    ذخیره دوره‌ای معیارهای عملکرد ربات (P&L، Sharpe، MaxDD و ...).
    """
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="performance_snapshots",
        verbose_name=_("Bot")
    )
    period_start = models.DateTimeField(verbose_name=_("Period Start"))
    period_end = models.DateTimeField(verbose_name=_("Period End"))

    # معیارهای عملکرد
    total_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total P&L"))
    total_pnl_percentage = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name=_("Total P&L (%)"))
    realized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Realized P&L"))
    unrealized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Unrealized P&L"))
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name=_("Max Drawdown (%)"))
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True, verbose_name=_("Sharpe Ratio"))
    total_trades = models.IntegerField(default=0, verbose_name=_("Total Trades"))
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Win Rate (%)"))

    # سایر معیارهای قابل نمایش
    avg_trade_duration = models.DurationField(null=True, blank=True, verbose_name=_("Average Trade Duration"))
    profit_factor = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True, verbose_name=_("Profit Factor"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Bot Performance Snapshot")
        verbose_name_plural = _("Bot Performance Snapshots")
        indexes = [
            models.Index(fields=['bot', '-period_end']), # برای نمایش معکوس تاریخچه
        ]

    def __str__(self):
        return f"{self.bot.name} Performance ({self.period_start} to {self.period_end})"

