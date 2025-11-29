# apps/agents/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class AgentType(BaseModel):
    name = models.CharField(max_length=64, unique=True, verbose_name=_("Agent Type Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    capabilities = models.JSONField(default=dict, verbose_name=_("Capabilities (JSON)"))
    is_system_managed = models.BooleanField(default=False, verbose_name=_("Is System Managed"))
    allowed_parameters = models.JSONField(default=dict, verbose_name=_("Allowed Parameters Schema (JSON)"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Agent Type")
        verbose_name_plural = _("Agent Types")


class Agent(BaseModel):
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Agent Name"))
    type = models.ForeignKey(
        "agents.AgentType",
        on_delete=models.PROTECT,
        related_name="agents",
        verbose_name=_("Agent Type")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_agents",
        verbose_name=_("Owner (User)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_paused_by_system = models.BooleanField(default=False, verbose_name=_("Is Paused by System"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents_created",
        verbose_name=_("Created By")
    )
    assigned_strategy_versions = models.ManyToManyField(
        "strategies.StrategyVersion",
        blank=True,
        related_name="assigned_agents",
        verbose_name=_("Assigned Strategy Versions")
    )
    last_activity_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Activity At"))

    def __str__(self):
        return f"{self.name} ({self.type.name})"

    class Meta:
        verbose_name = _("Agent")
        verbose_name_plural = _("Agents")


class AgentInstance(BaseModel):
    INSTANCE_STATUS_CHOICES = [
        ('RUNNING', _('Running')),
        ('PAUSED', _('Paused')),
        ('STOPPED', _('Stopped')),
        ('FAILED', _('Failed')),
    ]
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="instances",
        verbose_name=_("Agent")
    )
    instance_id = models.CharField(max_length=128, verbose_name=_("Instance ID"))
    status = models.CharField(max_length=16, choices=INSTANCE_STATUS_CHOICES, default='STOPPED', verbose_name=_("Status"))
    host = models.CharField(max_length=256, blank=True, verbose_name=_("Host"))
    process_id = models.IntegerField(null=True, blank=True, verbose_name=_("Process ID"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started At"))
    stopped_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Stopped At"))

    class Meta:
        verbose_name = _("Agent Instance")
        verbose_name_plural = _("Agent Instances")
        unique_together = ("agent", "instance_id")


class AgentConfig(BaseModel):
    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="config",
        verbose_name=_("Agent")
    )
    version = models.CharField(max_length=32, default="1.0.0", verbose_name=_("Config Version"))
    params = models.JSONField(default=dict, verbose_name=_("Parameters (JSON)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created By")
    )
    validation_result = models.JSONField(default=dict, blank=True, verbose_name=_("Validation Result (JSON)"))

    def __str__(self):
        return f"Config for {self.agent.name}"

    class Meta:
        verbose_name = _("Agent Config")
        verbose_name_plural = _("Agent Configs")


class AgentStatus(BaseModel):
    STATE_CHOICES = [
        ("IDLE", _("Idle")),
        ("RUNNING", _("Running")),
        ("PAUSED", _("Paused")),
        ("ERROR", _("Error")),
        ("STOPPED", _("Stopped")),
    ]
    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="status",
        verbose_name=_("Agent")
    )
    state = models.CharField(
        max_length=32,
        choices=STATE_CHOICES,
        default="IDLE",
        verbose_name=_("State")
    )
    last_heartbeat_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Heartbeat At"))
    last_error = models.TextField(blank=True, verbose_name=_("Last Error"))
    metrics = models.JSONField(default=dict, verbose_name=_("Metrics (JSON)"))
    agent_version = models.CharField(max_length=32, blank=True, verbose_name=_("Agent Version"))
    process_id = models.IntegerField(null=True, blank=True, verbose_name=_("Process ID"))

    def __str__(self):
        return f"Status of {self.agent.name}: {self.state}"

    class Meta:
        verbose_name = _("Agent Status")
        verbose_name_plural = _("Agent Statuses")


class AgentMessage(BaseModel):
    MESSAGE_PRIORITY_CHOICES = [
        (1, _('Low')),
        (2, _('Medium')),
        (3, _('High')),
        (4, _('Critical')),
    ]
    sender = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name=_("Sender Agent")
    )
    sender_type = models.ForeignKey(
        "agents.AgentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_agent_messages",  # اضافه شده
        verbose_name=_("Sender Type (Cached)")
    )
    receiver = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="received_messages",
        verbose_name=_("Receiver Agent")
    )
    receiver_type = models.ForeignKey(
        "agents.AgentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_agent_messages",  # اضافه شده
        verbose_name=_("Receiver Type (Cached)")
    )
    message_type = models.CharField(max_length=64, verbose_name=_("Message Type"))
    topic = models.CharField(max_length=128, blank=True, verbose_name=_("Topic"))
    payload = models.JSONField(default=dict, verbose_name=_("Payload (JSON)"))
    priority = models.IntegerField(choices=MESSAGE_PRIORITY_CHOICES, default=2, verbose_name=_("Priority"))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expires At"))
    is_encrypted = models.BooleanField(default=False, verbose_name=_("Is Encrypted"))
    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))
    retry_count = models.IntegerField(default=0, verbose_name=_("Retry Count"))
    processed = models.BooleanField(default=False, verbose_name=_("Is Processed"))

    class Meta:
        verbose_name = _("Agent Message")
        verbose_name_plural = _("Agent Messages")
        indexes = [
            models.Index(fields=['topic', '-created_at']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"{self.sender.name} -> {self.receiver.name}: {self.message_type}"


class AgentLog(BaseModel):
    LOG_LEVEL_CHOICES = [
        ("DEBUG", _("Debug")),
        ("INFO", _("Info")),
        ("WARNING", _("Warning")),
        ("ERROR", _("Error")),
        ("CRITICAL", _("Critical")),
    ]
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="agent_logs",  # تغییر از "logs" به "agent_logs"
        verbose_name=_("Agent")
    )
    level = models.CharField(max_length=16, choices=LOG_LEVEL_CHOICES, verbose_name=_("Log Level"))
    message = models.TextField(verbose_name=_("Log Message"))
    extra_data = models.JSONField(default=dict, blank=True, verbose_name=_("Extra Data (JSON)"))
    trace_id = models.CharField(max_length=128, blank=True, verbose_name=_("Trace ID"))
    user_context = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User Context")
    )
    resource_usage_snapshot = models.JSONField(default=dict, blank=True, verbose_name=_("Resource Usage Snapshot (JSON)"))
    agent_instance_id = models.CharField(max_length=128, blank=True, verbose_name=_("Agent Instance ID"))

    class Meta:
        verbose_name = _("Agent Log")
        verbose_name_plural = _("Agent Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', '-created_at']),
            models.Index(fields=['level']),
            models.Index(fields=['trace_id']),
        ]

    def __str__(self):
        return f"{self.agent.name} - {self.level}: {self.message[:50]}"


class AgentMetric(BaseModel):
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name=_("Agent")
    )
    period_start = models.DateTimeField(verbose_name=_("Period Start"))
    period_end = models.DateTimeField(verbose_name=_("Period End"))

    cpu_usage_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Avg CPU Usage (%)"))
    memory_usage_avg_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Avg Memory Usage (MB)"))
    disk_usage_avg_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Avg Disk Usage (MB)"))
    network_io_avg_kb = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_("Avg Network I/O (KB/s)"))

    messages_sent = models.IntegerField(default=0, verbose_name=_("Messages Sent"))
    messages_received = models.IntegerField(default=0, verbose_name=_("Messages Received"))
    errors_count = models.IntegerField(default=0, verbose_name=_("Errors Count"))
    avg_processing_time_ms = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name=_("Avg Processing Time (ms)"))

    class Meta:
        verbose_name = _("Agent Metric")
        verbose_name_plural = _("Agent Metrics")
        indexes = [
            models.Index(fields=['agent', '-period_end']),
        ]

    def __str__(self):
        return f"{self.agent.name} Metrics ({self.period_start} to {self.period_end})"