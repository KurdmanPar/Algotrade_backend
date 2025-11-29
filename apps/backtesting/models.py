# apps/backtesting/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class BacktestRun(BaseModel):
    """
    برای نگهداری اطلاعات یک اجرای بک‌تست.
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
        related_name="backtest_runs",
        verbose_name=_("Strategy Version")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backtest_runs",
        verbose_name=_("Owner")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PENDING",
        verbose_name=_("Status")
    )
    # اتصال به نماد و صرافی
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

    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started At"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Finished At"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    def __str__(self):
        return f"Backtest of {self.strategy_version} on {self.instrument.symbol}"

    class Meta:
        verbose_name = _("Backtest Run")
        verbose_name_plural = _("Backtest Runs")
        ordering = ['-created_at']
        # ممکن است بخواهید بر اساس owner و created_at جستجو کنید
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['status']),
        ]


class BacktestResult(BaseModel):
    """
    نگهداری جزئیات معاملات و داده‌های پیشرفته بک‌تست در PostgreSQL (برای دسترسی سریع).
    """
    backtest_run = models.ForeignKey(
        "backtesting.BacktestRun",
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
