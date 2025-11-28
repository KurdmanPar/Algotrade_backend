# agents/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AgentType(models.Model):
    """نوع عامل (Agent Type)"""
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    capabilities = models.JSONField(default=dict)  # قابلیت‌های عامل

    def __str__(self):
        return self.name


class Agent(models.Model):
    """عامل (Agent) اصلی در سیستم"""
    name = models.CharField(max_length=128)
    type = models.ForeignKey(AgentType, on_delete=models.PROTECT, related_name="agents")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents")
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)  # تنظیمات عامل
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type.name})"


class AgentStatus(models.Model):
    """وضعیت فعلی عامل"""
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name="status")
    state = models.CharField(
        max_length=32,
        choices=[
            ("IDLE", "Idle"),
            ("RUNNING", "Running"),
            ("PAUSED", "Paused"),
            ("ERROR", "Error"),
            ("STOPPED", "Stopped")
        ],
        default="IDLE"
    )
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    metrics = models.JSONField(default=dict)  # متریک‌های عملکردی

    def __str__(self):
        return f"{self.agent.name} - {self.state}"


class AgentMessage(models.Model):
    """پیام‌های ارسالی و دریافتی بین عامل‌ها"""
    sender = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="received_messages")
    message_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    correlation_id = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.name} -> {self.receiver.name}: {self.message_type}"


# agents/models.py (ادامه)

class AgentLog(models.Model):
    """لاگ فعالیت‌های عامل"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField(max_length=16)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = models.TextField()
    extra_data = models.JSONField(default=dict)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['agent', 'timestamp']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.agent.name} - {self.level}: {self.message[:50]}"