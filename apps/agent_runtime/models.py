# apps/agent_runtime/models.py
from django.db import models
from apps.core.models import BaseModel
from apps.agents.models import Agent

class AgentTaskLog(BaseModel):
    """
    ثبت تسک‌های اجرای Agent.
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="task_logs")
    task_id = models.CharField(max_length=255, verbose_name="Celery Task ID")
    status = models.CharField(max_length=32, choices=[('PENDING', 'Pending'), ('STARTED', 'Started'), ('SUCCESS', 'Success'), ('FAILURE', 'Failure')])
    result = models.TextField(blank=True, verbose_name="Task Result or Error")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Agent Task Log"
        verbose_name_plural = "Agent Task Logs"
        indexes = [
            models.Index(fields=['agent', '-created_at']),
        ]

    def __str__(self):
        return f"Task {self.task_id} for {self.agent.name} - {self.status}"
