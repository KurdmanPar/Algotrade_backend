# apps/agents/models.py
from django.db import models
from apps.core.models import BaseModel

class AgentType(models.Model):
    """برای تعریف انواع عامل‌ها (StrategyAgent, RiskAgent, ...)"""
    name = models.CharField(max_length=64, unique=True) # StrategyAgent, RiskAgent, ExecutionAgent, ...
    description = models.TextField(blank=True)
    capabilities = models.JSONField(default=dict) # consumes, produces, ...

    def __str__(self):
        return self.name

class Agent(BaseModel):
    """برای نگهداری اطلاعات هر نمونه از یک عامل"""
    name = models.CharField(max_length=128, unique=True)
    type = models.ForeignKey("agents.AgentType", on_delete=models.PROTECT, related_name="agents")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.type.name})"

class AgentConfig(models.Model):
    """برای نگهداری پیکربندی هر عامل"""
    agent = models.OneToOneField("agents.Agent", on_delete=models.CASCADE, related_name="config")
    params = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Config for {self.agent.name}"

class AgentStatus(BaseModel):
    """برای نگهداری وضعیت لحظه‌ای هر عامل"""
    agent = models.OneToOneField("agents.Agent", on_delete=models.CASCADE, related_name="status")
    state = models.CharField(max_length=32, default="stopped") # running, paused, failed
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    def __str__(self):
        return f"Status of {self.agent.name}: {self.state}"