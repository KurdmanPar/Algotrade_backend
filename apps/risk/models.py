# apps/risk/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel  # ارث‌بری از BaseModel برای فیلدهای timestamp


class RiskProfile(BaseModel):
    """
    پروفایل ریسک که می‌تواند در سطح کاربر یا یک بات خاص تعریف شود.
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_profiles",
                              null=True, blank=True)
    bot = models.OneToOneField("bots.Bot", on_delete=models.CASCADE, related_name="risk_profile", null=True, blank=True)

    name = models.CharField(max_length=128, help_text="e.g., Conservative, Aggressive, Custom Bot Risk")

    # محدودیت‌های مالی
    max_daily_loss_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                                 help_text="Max daily loss in % (e.g., 2.50 for 2.5%).")
    max_drawdown_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                               help_text="Max allowed drawdown in %.")
    max_position_size_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                                    help_text="Max position size as % of total equity.")
    risk_per_trade_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                                 help_text="Risk to take on a single trade in %.")

    # تنظیمات حدضرر و حدسود
    use_trailing_stop = models.BooleanField(default=False, help_text="Enable trailing stop loss.")
    trailing_stop_config = models.JSONField(default=dict, blank=True,
                                            help_text="e.g., {'activation_percent': 1.0, 'trail_percent': 0.5}")

    def __str__(self):
        if self.bot:
            return f"Risk Profile for Bot: {self.bot.name}"
        return f"Risk Profile for User: {self.owner.email} ({self.name})"


class RiskRule(BaseModel):
    """
    قوانین خاص و سفارشی برای مدیریت ریسک (مثلاً ممنوعیت معامله در سشن‌های خاص).
    """
    profile = models.ForeignKey("risk.RiskProfile", on_delete=models.CASCADE, related_name="rules")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    rule_type = models.CharField(max_length=64, help_text="e.g., 'no_trading_weekends', 'max_open_positions'")
    parameters = models.JSONField(default=dict, blank=True,
                                  help_text="Parameters for the rule, e.g., {'days': ['Sat', 'Sun']}")

    def __str__(self):
        return f"Rule '{self.name}' for {self.profile}"


class RiskEvent(BaseModel):
    """
    برای ثبت رویدادهای مربوط به ریسک (مثلاً وقتی یک حدضرر فعال شد یا یک محدودیت نقض شد).
    """
    EVENT_TYPE_CHOICES = [
        ("LIMIT_BREACHED", "Limit Breached"),
        ("STOP_LOSS_TRIGGERED", "Stop Loss Triggered"),
        ("RULE_VIOLATION", "Rule Violation"),
        ("WARNING", "Warning"),
    ]
    profile = models.ForeignKey("risk.RiskProfile", on_delete=models.CASCADE, related_name="events", null=True,
                                blank=True)
    bot = models.ForeignKey("bots.Bot", on_delete=models.CASCADE, related_name="risk_events", null=True, blank=True)

    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    severity = models.IntegerField(default=1, help_text="Severity level from 1 to 5.")
    message = models.TextField()

    # ارجاع به مدل مربوطه (مثلاً یک سفارش یا پوزیشن)
    order = models.ForeignKey("trading.Order", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="risk_events")
    position = models.ForeignKey("trading.Position", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="risk_events")

    def __str__(self):
        return f"Risk Event: {self.event_type} for {self.bot.name if self.bot else 'User'}"
