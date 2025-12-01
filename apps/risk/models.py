# apps/risk/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class RiskProfile(BaseModel):
    """
    پروفایل ریسک برای یک کاربر یا یک بات.
    """
    RISK_MODEL_TYPE_CHOICES = [
        ('CLASSIC', _('Classic Risk Model')),
        ('AI', _('AI Risk Model')),
        ('RAG', _('RAG-based Risk Model')),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_profiles",
        null=True,
        blank=True,
        verbose_name=_("Owner (User)")
    )
    bot = models.OneToOneField(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="risk_profile_model",  # این نام مربوط به related_name ای است که قبلاً تغییر دادیم
        null=True,
        blank=True,
        verbose_name=_("Bot Owner")
    )
    name = models.CharField(max_length=128, verbose_name=_("Profile Name"), help_text=_("e.g., Conservative, Aggressive, Custom Bot Risk"))

    risk_model_type = models.CharField(
        max_length=16,
        choices=RISK_MODEL_TYPE_CHOICES,
        default='CLASSIC',
        verbose_name=_("Risk Model Type")
    )
    risk_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_profiles",
        verbose_name=_("Responsible Agent (MAS)")
    )

    # محدودیت‌های مالی
    max_daily_loss_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Max Daily Loss (%)"),
        help_text=_("Max daily loss in % (e.g., 2.50 for 2.5%).")
    )
    max_drawdown_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Max Drawdown (%)"),
        help_text=_("Max allowed drawdown in %.")
    )
    max_position_size_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Max Position Size (%)"),
        help_text=_("Max position size as % of total equity.")
    )
    max_capital = models.DecimalField(
        max_digits=32, decimal_places=8, null=True, blank=True,
        verbose_name=_("Max Capital to Risk")
    )
    max_positions = models.IntegerField(null=True, blank=True, verbose_name=_("Max Open Positions"))
    max_exposure_per_instrument = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Max Exposure per Instrument (%)")
    )
    max_correlation_with_portfolio = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Max Correlation with Portfolio (%)")
    )

    risk_per_trade_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Risk per Trade (%)"),
        help_text=_("Risk to take on a single trade in %.")
    )

    # تنظیمات حدضرر و حدسود
    use_trailing_stop = models.BooleanField(default=False, verbose_name=_("Use Trailing Stop"), help_text=_("Enable trailing stop loss."))
    trailing_stop_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Trailing Stop Config (JSON)"),
        help_text=_("e.g., {'activation_percent': 1.0, 'trail_percent': 0.5}")
    )
    use_ai_risk_model = models.BooleanField(default=False, verbose_name=_("Use AI Risk Model"))

    def __str__(self):
        if self.bot:
            return f"Risk Profile for Bot: {self.bot.name}"
        if self.owner:
            return f"Risk Profile for User: {self.owner.email} ({self.name})"
        return f"Unassigned Risk Profile ({self.name})"

    class Meta:
        verbose_name = _("Risk Profile")
        verbose_name_plural = _("Risk Profiles")
        unique_together = (("owner", "name"), ("bot", "name"))  # جلوگیری از نام تکراری برای یک کاربر یا یک بات


class RiskRule(BaseModel):
    """
    قوانین خاص و سفارشی برای مدیریت ریسک.
    """
    ACTION_CHOICES = [
        ('ALLOW', _('Allow')),
        ('DENY', _('Deny')),
        ('ADJUST', _('Adjust')),
    ]
    profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name=_("Risk Profile")
    )
    name = models.CharField(max_length=128, verbose_name=_("Rule Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    rule_type = models.CharField(
        max_length=64,
        verbose_name=_("Rule Type"),
        help_text=_("e.g., 'no_trading_weekends', 'max_open_positions'")
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Parameters (JSON)"),
        help_text=_("Parameters for the rule, e.g., {'days': ['Sat', 'Sun']}")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    priority = models.IntegerField(default=0, verbose_name=_("Priority (Higher = Checked First)"))
    action = models.CharField(
        max_length=16,
        choices=ACTION_CHOICES,
        default='DENY',
        verbose_name=_("Action")
    )
    agent_responsible = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Responsible Agent (MAS)")
    )

    def __str__(self):
        return f"Rule '{self.name}' for {self.profile}"

    class Meta:
        verbose_name = _("Risk Rule")
        verbose_name_plural = _("Risk Rules")
        ordering = ['-priority', 'created_at']


# سایر مدل‌های Risk: RiskEvent, RiskMetric, RiskAlert و غیره...



class RiskEvent(BaseModel):
    EVENT_TYPE_CHOICES = [
        ("LIMIT_BREACHED", _("Limit Breached")),
        ("STOP_LOSS_TRIGGERED", _("Stop Loss Triggered")),
        ("RULE_VIOLATION", _("Rule Violation")),
        ("WARNING", _("Warning")),
        ("LIQUIDATION", _("Position Liquidation")),
        ("RISK_MODEL_OVERRIDE", _("Risk Model Override")),
    ]
    SEVERITY_CHOICES = [
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Critical")),
        (5, _("Emergency")),
    ]
    profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
        verbose_name=_("Risk Profile")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="risk_events",
        null=True,
        blank=True,
        verbose_name=_("Bot")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Agent (MAS)")
    )
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Strategy Version")
    )
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Signal")
    )

    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES, verbose_name=_("Event Type"))
    severity = models.IntegerField(
        choices=SEVERITY_CHOICES,
        default=1,
        verbose_name=_("Severity"),
        help_text=_("Severity level from 1 to 5.")
    )
    message = models.TextField(verbose_name=_("Message"))

    order = models.ForeignKey(
        "trading.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_events",
        verbose_name=_("Order")
    )
    position = models.ForeignKey(
        "trading.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_events",
        verbose_name=_("Position")
    )

    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    is_resolved = models.BooleanField(default=False, verbose_name=_("Is Resolved"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Resolved At"))
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Resolved By")
    )
    resolution_notes = models.TextField(blank=True, verbose_name=_("Resolution Notes"))

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    def __str__(self):
        return f"Risk Event: {self.event_type} for {self.bot.name if self.bot else 'User'}"

    class Meta:
        verbose_name = _("Risk Event")
        verbose_name_plural = _("Risk Events")
        indexes = [
            models.Index(fields=['profile', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]


class RiskMetric(BaseModel):
    profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name=_("Risk Profile")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="risk_metrics",
        null=True,
        blank=True,
        verbose_name=_("Bot")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Agent (MAS)")
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"))

    value_at_risk = models.DecimalField(max_digits=32, decimal_places=8, null=True, blank=True, verbose_name=_("Value at Risk (VaR)"))
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name=_("Max Drawdown (%)"))
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True, verbose_name=_("Sharpe Ratio"))
    volatility = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True, verbose_name=_("Volatility"))
    exposure = models.DecimalField(max_digits=32, decimal_places=8, null=True, blank=True, verbose_name=_("Total Exposure"))
    exposure_per_instrument = models.JSONField(default=dict, blank=True, verbose_name=_("Exposure per Instrument (JSON)"))

    class Meta:
        verbose_name = _("Risk Metric")
        verbose_name_plural = _("Risk Metrics")
        indexes = [
            models.Index(fields=['profile', 'timestamp']),
        ]

    def __str__(self):
        return f"Metrics for {self.profile} at {self.timestamp}"


class RiskAlert(BaseModel):
    ALERT_TYPE_CHOICES = [
        ("THRESHOLD_BREACH", _("Threshold Breach")),
        ("RULE_VIOLATION", _("Rule Violation")),
        ("HIGH_RISK_SIGNAL", _("High Risk Signal")),
        ("SYSTEM_ANOMALY", _("System Anomaly")),
    ]
    SEVERITY_CHOICES = [
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Critical")),
        (5, _("Emergency")),
    ]
    profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name=_("Risk Profile")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="risk_alerts",
        null=True,
        blank=True,
        verbose_name=_("Bot")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Agent (MAS)")
    )

    alert_type = models.CharField(max_length=32, choices=ALERT_TYPE_CHOICES, verbose_name=_("Alert Type"))
    severity = models.IntegerField(choices=SEVERITY_CHOICES, verbose_name=_("Severity"))
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))

    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    is_acknowledged = models.BooleanField(default=False, verbose_name=_("Is Acknowledged"))
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Acknowledged At"))
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Acknowledged By")
    )

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    class Meta:
        verbose_name = _("Risk Alert")
        verbose_name_plural = _("Risk Alerts")
        indexes = [
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['is_acknowledged', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"