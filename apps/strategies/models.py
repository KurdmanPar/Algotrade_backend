# apps/strategies/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Strategy(BaseModel):
    """
    تعریف یک استراتژی معاملاتی.
    """
    STRATEGY_CATEGORY_CHOICES = [
        ("ENTRY", _("Entry Signal")),
        ("EXIT", _("Exit Signal")),
        ("FULL", _("Full Strategy")),
        ("RISK", _("Risk Model")),
        ("ML", _("ML Model")),
        ("AI", _("AI Model")),
        ("PRICE_ACTION", _("Price Action Strategy")),
        ("SMART_MONEY", _("Smart Money Concept Strategy")),
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="strategies",
        verbose_name=_("Owner")
    )
    name = models.CharField(max_length=128, verbose_name=_("Strategy Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    category = models.CharField(
        max_length=16,
        choices=STRATEGY_CATEGORY_CHOICES,
        default="FULL",
        verbose_name=_("Category")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_public = models.BooleanField(default=False, verbose_name=_("Is Public (for marketplace)"))
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Low Risk')),
            ('medium', _('Medium Risk')),
            ('high', _('High Risk')),
        ],
        default='medium',
        verbose_name=_("Risk Level")
    )
    # امنیت: کد منبع ممکن است حاوی اطلاعات حساس باشد
    source_code_encrypted = models.TextField(blank=True, verbose_name=_("Encrypted Source Code"))
    code_language = models.CharField(max_length=32, default="Python", verbose_name=_("Code Language"))

    def __str__(self):
        return f"{self.name} by {self.owner.email}"

    class Meta:
        verbose_name = _("Strategy")
        verbose_name_plural = _("Strategies")


class StrategyVersion(BaseModel):
    """
    نگهداری نسخه‌های مختلف یک استراتژی.
    """
    strategy = models.ForeignKey(
        "strategies.Strategy",
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name=_("Strategy")
    )
    version = models.CharField(max_length=32, verbose_name=_("Version"))  # e.g. 1.0.0
    parameters_schema = models.JSONField(default=dict, verbose_name=_("Parameters Schema (JSON)"))
    indicator_configs = models.JSONField(default=list, verbose_name=_("Indicator Configs (JSON)"))
    price_action_configs = models.JSONField(default=list, verbose_name=_("Price Action Configs (JSON)"))
    smart_money_configs = models.JSONField(default=list, verbose_name=_("Smart Money Configs (JSON)"))
    ai_metrics_configs = models.JSONField(default=list, verbose_name=_("AI Metrics Configs (JSON)"))

    # ارجاع به کد منبع یا فایل آموزش مدل
    source_code_ref = models.CharField(
        max_length=256,
        blank=True,
        verbose_name=_("Source Code Reference (Path, Git Ref, ...)")
    )
    model_artifact_ref = models.CharField(
        max_length=256,
        blank=True,
        verbose_name=_("Model Artifact Reference (Path, MLflow, ...)")
    )
    is_approved_for_live = models.BooleanField(default=False, verbose_name=_("Is Approved for Live Trading"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Strategy Version")
        verbose_name_plural = _("Strategy Versions")
        unique_together = ("strategy", "version")

    def __str__(self):
        return f"{self.strategy.name} v{self.version}"


class StrategyAssignment(BaseModel):
    """
    اتصال یک نسخه استراتژی به یک بات خاص.
    """
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.CASCADE,
        related_name="bot_assignments",
        verbose_name=_("Strategy Version")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="strategy_assignments",
        verbose_name=_("Bot")
    )
    weight = models.FloatField(default=1.0, verbose_name=_("Weight (for ensemble)"))
    priority = models.IntegerField(default=0, verbose_name=_("Priority (for execution order)")
    )
    parameters_override = models.JSONField(default=dict, verbose_name=_("Parameters Override (JSON)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active on this Bot"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Strategy Assignment")
        verbose_name_plural = _("Strategy Assignments")
        unique_together = ("bot", "strategy_version")

    def __str__(self):
        return f"{self.strategy_version} -> {self.bot}"


class BacktestRun(BaseModel):
    """
    نگهداری اطلاعات یک اجرای بک‌تست.
    """
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("RUNNING", _("Running")),
        ("COMPLETED", _("Completed")),
        ("FAILED", _("Failed")),
        ("CANCELLED", _("Cancelled")),
    ]
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.CASCADE,
        related_name="backtests",
        verbose_name=_("Strategy Version")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backtests",
        verbose_name=_("Owner")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PENDING",
        verbose_name=_("Status")
    )
    # ارجاع به نماد و صرافی
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        verbose_name=_("Instrument")
    )
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Exchange Account (for data source)")
    )
    timeframe = models.CharField(max_length=16, verbose_name=_("Timeframe"))  # e.g., 1h, 4h, 1d

    start_datetime = models.DateTimeField(verbose_name=_("Start Datetime"))
    end_datetime = models.DateTimeField(verbose_name=_("End Datetime"))

    initial_capital = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Initial Capital"))
    position_size_mode = models.CharField(
        max_length=16,
        default="fixed",
        verbose_name=_("Position Size Mode"),
        help_text=_("fixed / percent / risk_pct")
    )
    position_size_value = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Position Size Value"))

    parameters = models.JSONField(default=dict, verbose_name=_("Run Parameters (JSON)"))
    runtime_config = models.JSONField(default=dict, verbose_name=_("Runtime Config (JSON)"))  # commission, slippage, etc.

    # نتایج خلاصه
    result_summary = models.JSONField(default=dict, verbose_name=_("Result Summary (JSON)"))
    # ارجاع به نتایج جزئی در MongoDB
    result_ref = models.CharField(
        max_length=256,
        blank=True,
        verbose_name=_("Detailed Result Reference (MongoDB)"),
        help_text=_("Reference to detailed results in MongoDB")
    )

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started At"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Finished At"))

    class Meta:
        verbose_name = _("Backtest Run")
        verbose_name_plural = _("Backtest Runs")

    def __str__(self):
        return f"Backtest of {self.strategy_version} on {self.instrument.symbol}"


class BacktestResult(BaseModel):
    """
    نگهداری جزئیات معاملات و داده‌های پیشرفته بک‌تست در PostgreSQL (برای دسترسی سریع).
    """
    backtest_run = models.ForeignKey(
        "strategies.BacktestRun",
        on_delete=models.CASCADE,
        related_name="detailed_results",
        verbose_name=_("Backtest Run")
    )
    order_id = models.CharField(max_length=128, verbose_name=_("Order ID"))
    trade_id = models.CharField(max_length=128, verbose_name=_("Trade ID"))
    side = models.CharField(max_length=4, choices=[('BUY', _('Buy')), ('SELL', _('Sell'))], verbose_name=_("Side"))
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quantity"))
    price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Price"))
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))
    pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("P&L")
    )
    # سایر اطلاعات مرتبط با زمان اجرای سفارش
    entry_signal_confidence = models.FloatField(null=True, blank=True, verbose_name=_("Entry Signal Confidence"))
    exit_reason = models.CharField(max_length=64, blank=True, verbose_name=_("Exit Reason"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Backtest Result Detail")
        verbose_name_plural = _("Backtest Result Details")
        # ممکن است بخواهید بر اساس backtest_run و timestamp جستجو کنید
        indexes = [
            models.Index(fields=['backtest_run', 'timestamp']),
        ]

    def __str__(self):
        return f"Trade {self.trade_id} in {self.backtest_run}"