# apps/strategies/models.py
from django.db import models
from django.conf import settings

class Strategy(models.Model):
    """برای تعریف یک استراتژی معاملاتی"""
    STRATEGY_CATEGORY_CHOICES = [
        ("ENTRY", "Entry Signal"),
        ("EXIT", "Exit Signal"),
        ("FULL", "Full Strategy"),
        ("RISK", "Risk Model"),
        ("ML", "ML Model"),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategies")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=16, choices=STRATEGY_CATEGORY_CHOICES, default="FULL")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.owner.email}"

class StrategyVersion(models.Model):
    """برای نگهداری نسخه‌های مختلف یک استراتژی"""
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=32) # e.g. 1.0.0
    parameters_schema = models.JSONField(default=dict) # تعریف پارامترها
    indicator_configs = models.JSONField(default=list) # لیست اندیکاتورها + params
    price_action_configs = models.JSONField(default=list)
    smart_money_configs = models.JSONField(default=list)
    ai_metrics_configs = models.JSONField(default=list)

    code_ref = models.CharField(max_length=256, blank=True) # path, git ref, ...
    is_approved_for_live = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("strategy", "version")

    def __str__(self):
        return f"{self.strategy.name} v{self.version}"

class BacktestRun(models.Model):
    """برای نگهداری اطلاعات یک اجرای بک‌تست"""
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("RUNNING", "Running"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]
    strategy_version = models.ForeignKey("strategies.StrategyVersion", on_delete=models.CASCADE, related_name="backtests")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="backtests")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")

    # این فیلد به صورت موقت است. بعداً به مدل Instrument لینک می‌شود.
    instrument_symbol = models.CharField(max_length=64, help_text="e.g., BTCUSDT")
    timeframe = models.CharField(max_length=16, help_text="e.g., 1h, 4h, 1d")

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    initial_capital = models.DecimalField(max_digits=32, decimal_places=8, default=0)
    position_size_mode = models.CharField(max_length=16, default="fixed", help_text="fixed / percent")
    position_size_value = models.DecimalField(max_digits=32, decimal_places=8, default=0)

    parameters = models.JSONField(default=dict, help_text="Parameters for this specific run")
    runtime_config = models.JSONField(default=dict, help_text="commission, slippage, etc.")

    result_summary = models.JSONField(default=dict, help_text="PnL, drawdown, win_rate, ...")
    result_ref = models.CharField(max_length=256, blank=True, help_text="Reference to detailed results in MongoDB")

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Backtest of {self.strategy_version} on {self.instrument_symbol}"