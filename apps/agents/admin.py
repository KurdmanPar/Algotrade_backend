# apps/agents/admin.py
from django.contrib import admin
from .models import AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric

@admin.register(AgentType)
class AgentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system_managed')
    search_fields = ('name',)

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'owner', 'is_active', 'last_activity_at')
    list_filter = ('is_active', 'type')
    raw_id_fields = ('owner', 'created_by')

@admin.register(AgentInstance)
class AgentInstanceAdmin(admin.ModelAdmin):
    list_display = ('agent', 'instance_id', 'status', 'started_at')
    list_filter = ('status',)
    raw_id_fields = ('agent',)

@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ('agent', 'version', 'is_active')
    raw_id_fields = ('agent', 'created_by')

@admin.register(AgentStatus)
class AgentStatusAdmin(admin.ModelAdmin):
    list_display = ('agent', 'state', 'last_heartbeat_at')
    raw_id_fields = ('agent',)

@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'processed', 'created_at')
    list_filter = ('processed', 'message_type', 'created_at')
    raw_id_fields = ('sender', 'receiver', 'sender_type', 'receiver_type')

@admin.register(AgentLog)
class AgentLogAdmin(admin.ModelAdmin):
    list_display = ('agent', 'level', 'message', 'created_at')
    list_filter = ('level', 'created_at')
    raw_id_fields = ('agent', 'user_context')

@admin.register(AgentMetric)
class AgentMetricAdmin(admin.ModelAdmin):
    list_display = ('agent', 'period_start', 'period_end', 'cpu_usage_avg', 'messages_sent')
    list_filter = ('period_end',)
    raw_id_fields = ('agent',)