# apps/bots/models.py
from django.db import models
from django.conf import settings


class Bot(models.Model):
    """مدل اصلی برای هر ربات معاملاتی که کاربر ایجاد می‌کند"""
    BOT_TYPE_CHOICES = [
        ("BUY_ONLY", "Buy Only"),
        ("SELL_ONLY", "Sell Only"),
        ("LONG_SHORT", "Long & Short"),
        ("GRID", "Grid Bot"),
        ("DCA", "Dollar Cost Averaging"),
    ]
    STATUS_CHOICES = [
        ("INACTIVE", "Inactive"),
        ("ACTIVE", "Active"),
        ("PAUSED", "Paused"),
        ("STOPPED", "Stopped"),
        ("ERROR", "Error"),
    ]
    MODE_CHOICES = [
        ("LIVE", "Live Trading"),
        ("PAPER", "Paper Trading"),
    ]
    CONTROL_CHOICES = [
        ("MANUAL", "Manual Control by User"),
        ("AUTOMATIC", "Automatic Control by System"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bots")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # اتصال به حساب کاربری در یک صرافی خاص
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.PROTECT, related_name="bots")

    # اتصال به نماد معاملاتی مشخص (بسیار مهم)
    # instrument = models.ForeignKey("instruments.Instrument", on_delete=models.PROTECT, related_name="bots",
    #                                help_text="The specific trading instrument for this bot.")

    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.PROTECT, related_name="bots",
                                   null=True, blank=True, help_text="The specific trading instrument for this bot.")

    bot_type = models.CharField(max_length=16, choices=BOT_TYPE_CHOICES, default="LONG_SHORT")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="INACTIVE")
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="PAPER")
    control_type = models.CharField(max_length=16, choices=CONTROL_CHOICES, default="MANUAL",
                                    help_text="How the bot is started/stopped.")

    # تنظیمات کلی ربات
    max_concurrent_trades = models.IntegerField(default=1, help_text="Maximum number of open trades/positions.")
    desired_profit_target_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True,
                                                        help_text="Target profit in percentage (e.g., 2.50 for 2.5%).")
    max_allowed_loss_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True,
                                                   help_text="Maximum allowed loss in percentage.")

    # تنظیمات مربوط به حالت Paper Trading
    paper_trading_balance = models.DecimalField(max_digits=32, decimal_places=8, default=10000,
                                                help_text="Starting balance for paper trading mode.")

    # تنظیمات زمان‌بندی و اجرا
    schedule_config = models.JSONField(default=dict, blank=True,
                                       help_text="e.g., {'start_time': '09:00', 'end_time': '17:00', 'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']}")

    # اتصال به پروفایل ریسک (بسیار مهم)
    # risk_profile = models.ForeignKey("risk.RiskProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="bots")

    # فیلدهای مربوط به دیباگ و مانیتورینگ
    last_error_log = models.TextField(blank=True, help_text="Stores the last error message for debugging.")
    last_heartbeat_at = models.DateTimeField(null=True, blank=True,
                                             help_text="Last time the bot sent a heartbeat signal.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # جلوگیری از ایجاد دو ربات با نام یکسان برای یک کاربر
        unique_together = ("owner", "name")

    def __str__(self):
        return f"{self.name} ({self.instrument.symbol}) by {self.owner.email}"


class BotStrategyConfig(models.Model):
    """برای اتصال یک یا چند استراتژی به یک ربات"""
    bot = models.ForeignKey("bots.Bot", on_delete=models.CASCADE, related_name="strategy_configs")
    strategy_version = models.ForeignKey("strategies.StrategyVersion", on_delete=models.CASCADE,
                                         related_name="bot_configs")

    weight = models.FloatField(default=1.0, help_text="Weight of this strategy in the bot's final decision.")
    is_primary = models.BooleanField(default=False, help_text="Mark if this is the primary strategy for the bot.")

    # اجازه به کاربر برای بازنویسی پارامترهای استراتژی فقط برای این ربات خاص
    parameters_override = models.JSONField(default=dict, blank=True,
                                           help_text="Override default strategy parameters for this specific bot.")

    class Meta:
        unique_together = ("bot", "strategy_version")

    def __str__(self):
        return f"{self.bot.name} - {self.strategy_version}"