# apps/signals/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Signal(BaseModel):
    DIRECTION_CHOICES = [
        ("BUY", _("Buy")),
        ("SELL", _("Sell")),
        ("CLOSE_LONG", _("Close Long")),
        ("CLOSE_SHORT", _("Close Short")),
    ]
    SIGNAL_TYPE_CHOICES = [
        ("ENTRY", _("Entry Signal")),
        ("EXIT", _("Exit Signal")),
        ("TAKE_PROFIT", _("Take Profit")),
        ("STOP_LOSS", _("Stop Loss")),
        ("SCALE_IN", _("Scale In")),
        ("SCALE_OUT", _("Scale Out")),
        ("LIQUIDATION", _("Liquidation Signal")),
    ]
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("SENT_TO_RISK", _("Sent to Risk Agent")),
        ("APPROVED", _("Approved by Risk")),
        ("REJECTED", _("Rejected by Risk")),
        ("SENT_TO_EXECUTION", _("Sent to Execution Agent")),
        ("EXECUTED", _("Executed")),
        ("EXPIRED", _("Expired")),
        ("CANCELED", _("Canceled")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signals",
        verbose_name=_("User")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="signals",
        null=True,
        blank=True,
        verbose_name=_("Bot")
    )
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signals",
        verbose_name=_("Strategy Version"),
        help_text=_("The strategy version that generated this signal.")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Agent (MAS)"),
        help_text=_("The agent that generated this signal.")
    )
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.PROTECT,
        related_name="signals",
        verbose_name=_("Exchange Account")
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="signals",
        verbose_name=_("Instrument")
    )

    direction = models.CharField(max_length=16, choices=DIRECTION_CHOICES, verbose_name=_("Direction"))
    signal_type = models.CharField(max_length=16, choices=SIGNAL_TYPE_CHOICES, default="ENTRY", verbose_name=_("Signal Type"))

    price = models.DecimalField(
        max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Suggested Price"),
        help_text=_("Suggested price for limit orders.")
    )
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Suggested Quantity"))
    confidence_score = models.FloatField(default=0.0, verbose_name=_("Confidence Score"), help_text=_("Confidence of the signal from 0.0 to 1.0"))
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("Payload (JSON)"), help_text=_("Additional data like indicators, AI scores, etc."))

    status = models.CharField(max_length=17, choices=STATUS_CHOICES, default="PENDING", verbose_name=_("Status"))  # تغییر max_length به 17
    priority = models.IntegerField(default=1, verbose_name=_("Priority (Higher = Processed First)"))
    is_recurring = models.BooleanField(default=False, verbose_name=_("Is Recurring"))

    sent_to_risk_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent to Risk At"))
    risk_approval_details = models.JSONField(default=dict, blank=True, verbose_name=_("Risk Approval Details (JSON)"))
    sent_to_execution_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent to Execution At"))
    final_order = models.OneToOneField(
        "trading.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_signal",
        verbose_name=_("Final Order")
    )

    generated_at = models.DateTimeField(verbose_name=_("Generated At"))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expires At"), help_text=_("Signal is invalid after this time."))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Processed At"), help_text=_("Time when signal was processed by risk agent."))

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    def __str__(self):
        return f"{self.direction} {self.quantity} {self.instrument.symbol} ({self.status})"

    class Meta:
        verbose_name = _("Signal")
        verbose_name_plural = _("Signals")
        indexes = [
            models.Index(fields=['user', '-generated_at']),
            models.Index(fields=['status', '-generated_at']),
            models.Index(fields=['correlation_id']),
        ]


class SignalLog(BaseModel):
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("Signal")
    )
    old_status = models.CharField(max_length=17, verbose_name=_("Old Status"))  # تغییر max_length
    new_status = models.CharField(max_length=17, verbose_name=_("New Status"))  # تغییر max_length
    message = models.TextField(blank=True, verbose_name=_("Log Message"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))
    changed_by_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By Agent (MAS)")
    )
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By User")
    )

    def __str__(self):
        return f"Signal {self.signal.id} changed from {self.old_status} to {self.new_status}"

    class Meta:
        verbose_name = _("Signal Log")
        verbose_name_plural = _("Signal Logs")
        indexes = [
            models.Index(fields=['signal', '-created_at']),
        ]


class SignalAlert(BaseModel):
    ALERT_TYPE_CHOICES = [
        ("HIGH_CONFIDENCE", _("High Confidence Signal")),
        ("RISK_REJECTION", _("Risk Rejection")),
        ("EXECUTION_ERROR", _("Execution Error")),
        ("MANUAL_OVERRIDE", _("Manual Override")),
    ]
    SEVERITY_CHOICES = [
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Critical")),
    ]
    signal = models.ForeignKey(  # اینجا related_name تغییر کرد
        "signals.Signal",
        on_delete=models.CASCADE,
        related_name="signal_alerts",  # تغییر از "alerts" به "signal_alerts"
        verbose_name=_("Signal")
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
        verbose_name = _("Signal Alert")
        verbose_name_plural = _("Signal Alerts")
        indexes = [
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['is_acknowledged', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"