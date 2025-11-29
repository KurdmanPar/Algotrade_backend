# apps/logging_app/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class SystemLog(BaseModel):
    LEVEL_CHOICES = [
        ("DEBUG", _("Debug")),
        ("INFO", _("Info")),
        ("WARNING", _("Warning")),
        ("ERROR", _("Error")),
        ("CRITICAL", _("Critical")),
    ]
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default="INFO", verbose_name=_("Log Level"))
    source = models.CharField(
        max_length=128,
        verbose_name=_("Source"),
        help_text=_("e.g., 'RiskAgent', 'ExecutionAgent', 'Django.Views'")
    )
    message = models.TextField(verbose_name=_("Log Message"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
        verbose_name=_("User Context")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",  # تغییر از "logs" به "system_logs"
        verbose_name=_("Agent Context (MAS)")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
        verbose_name=_("Bot Context")
    )

    context = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Context (JSON)"),
        help_text=_("e.g., {'order_id': 123, 'error_code': 'E101'}")
    )
    trace_id = models.CharField(max_length=128, blank=True, verbose_name=_("Trace ID"))
    request_id = models.CharField(max_length=128, blank=True, verbose_name=_("Request ID"))
    correlation_id = models.CharField(max_length=128, blank=True, verbose_name=_("Correlation ID"))
    severity_score = models.FloatField(default=0.0, verbose_name=_("Severity Score (0.0 - 5.0)"))
    resource_usage_snapshot = models.JSONField(default=dict, blank=True, verbose_name=_("Resource Usage Snapshot (JSON)"))

    def __str__(self):
        return f"[{self.level}] {self.source}: {self.message[:50]}"

    class Meta:
        verbose_name = _("System Log")
        verbose_name_plural = _("System Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level', '-created_at']),
            models.Index(fields=['trace_id']),
            models.Index(fields=['user', '-created_at']),
        ]


class SystemEvent(BaseModel):
    EVENT_CATEGORY_CHOICES = [
        ("SYSTEM", _("System")),
        ("AGENT", _("Agent")),
        ("BOT", _("Bot")),
        ("RISK", _("Risk")),
        ("TRADING", _("Trading")),
        ("BACKTEST", _("Backtest")),
        ("SECURITY", _("Security")),
    ]
    SEVERITY_CHOICES = [
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Critical")),
        (5, _("Emergency")),
    ]
    category = models.CharField(max_length=16, choices=EVENT_CATEGORY_CHOICES, verbose_name=_("Event Category"))
    severity = models.IntegerField(choices=SEVERITY_CHOICES, verbose_name=_("Severity"))
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))

    source_component = models.CharField(max_length=128, verbose_name=_("Source Component"))
    source_instance_id = models.CharField(max_length=128, blank=True, verbose_name=_("Source Instance ID"))

    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    class Meta:
        verbose_name = _("System Event")
        verbose_name_plural = _("System Events")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]


class NotificationChannel(BaseModel):
    DELIVERY_METHOD_CHOICES = [
        ("EMAIL", _("Email")),
        ("SMS", _("SMS")),
        ("TELEGRAM", _("Telegram")),
        ("PUSH", _("Push Notification")),
        ("WEBHOOK", _("Webhook")),
    ]
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Channel Name"))
    code = models.CharField(max_length=32, unique=True, verbose_name=_("Channel Code"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    delivery_method = models.CharField(max_length=16, choices=DELIVERY_METHOD_CHOICES, verbose_name=_("Delivery Method"))
    is_encrypted = models.BooleanField(default=False, verbose_name=_("Is Encrypted"))
    rate_limit_per_minute = models.IntegerField(default=100, verbose_name=_("Rate Limit Per Minute"))

    credentials_encrypted = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Encrypted Credentials (JSON)"),
        help_text=_("e.g., {'api_key': '...', 'bot_token': '...'}")
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration (JSON)"),
        help_text=_("e.g., {'smtp_host': '...'}")
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Notification Channel")
        verbose_name_plural = _("Notification Channels")


class Alert(BaseModel):
    ALERT_TYPE_CHOICES = [
        ("INFO", _("Information")),
        ("SUCCESS", _("Success")),
        ("WARNING", _("Warning")),
        ("ERROR", _("Error")),
        ("CRITICAL", _("Critical")),
    ]
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("SENT", _("Sent")),
        ("FAILED", _("Failed")),
        ("DELIVERED", _("Delivered")),
    ]
    PRIORITY_CHOICES = [
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Critical")),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name=_("User")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name=_("Bot")
    )
    order = models.ForeignKey(
        "trading.Order",
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name=_("Order")
    )
    position = models.ForeignKey(
        "trading.Position",
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name=_("Position")
    )
    signal = models.ForeignKey(  # اینجا related_name تغییر کرد
        "signals.Signal",
        on_delete=models.CASCADE,
        related_name="logging_app_alerts",  # تغییر از "alerts" به "logging_app_alerts"
        null=True,
        blank=True,
        verbose_name=_("Signal")
    )

    type = models.CharField(max_length=32, choices=ALERT_TYPE_CHOICES, default="INFO", verbose_name=_("Alert Type"))
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, verbose_name=_("Priority"))
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    message = models.TextField(verbose_name=_("Message"))

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING", verbose_name=_("Status"))

    channels_sent = models.ManyToManyField(
        "logging_app.NotificationChannel",
        related_name="sent_alerts",
        blank=True,
        verbose_name=_("Channels Sent")
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Payload (JSON)"),
        help_text=_("e.g., {'order_id': 123, 'price': 45000}")
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expires At"))

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

    def __str__(self):
        target = self.user.email if self.user else 'System'
        return f"{self.type}: {self.title} for {target}"

    class Meta:
        verbose_name = _("Alert")
        verbose_name_plural = _("Alerts")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['is_acknowledged', '-created_at']),
            models.Index(fields=['correlation_id']),
        ]


class UserNotificationPreference(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name=_("User")
    )
    alert_type = models.CharField(
        max_length=64,
        verbose_name=_("Alert Type"),
        help_text=_("e.g., 'ORDER_FILLED'")
    )
    channel = models.ForeignKey(
        "logging_app.NotificationChannel",
        on_delete=models.CASCADE,
        related_name="user_preferences",
        verbose_name=_("Notification Channel")
    )

    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Is Enabled"),
        help_text=_("If user wants to receive this alert type on this channel.")
    )
    is_muted = models.BooleanField(default=False, verbose_name=_("Is Muted"))
    mute_until = models.DateTimeField(null=True, blank=True, verbose_name=_("Mute Until"))
    delivery_schedule = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Delivery Schedule (JSON)"),
        help_text=_("e.g., {'days': ['Mon', 'Wed', 'Fri'], 'time_range': ['09:00', '17:00']}")
    )

    class Meta:
        verbose_name = _("User Notification Preference")
        verbose_name_plural = _("User Notification Preferences")
        unique_together = ("user", "alert_type", "channel")

    def __str__(self):
        return f"{self.user.email} - {self.alert_type} via {self.channel.name}"


class AuditLog(BaseModel):
    ACTION_CHOICES = [
        ("USER_LOGIN", _("User Login")),
        ("USER_LOGOUT", _("User Logout")),
        ("USER_PASSWORD_CHANGE", _("User Password Change")),
        ("USER_PROFILE_UPDATE", _("User Profile Update")),
        ("BOT_CREATE", _("Bot Create")),
        ("BOT_UPDATE", _("Bot Update")),
        ("BOT_DELETE", _("Bot Delete")),
        ("RISK_PROFILE_UPDATE", _("Risk Profile Update")),
        ("ORDER_PLACE", _("Order Place")),
        ("ORDER_CANCEL", _("Order Cancel")),
        ("API_KEY_CREATE", _("API Key Create")),
        ("API_KEY_DELETE", _("API Key Delete")),
        ("SECURITY_EVENT", _("Security Event")),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("User")
    )
    action = models.CharField(max_length=64, choices=ACTION_CHOICES, verbose_name=_("Action"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"{self.user.email if self.user else 'N/A'} - {self.action}"