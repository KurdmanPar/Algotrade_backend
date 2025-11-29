# apps/risk/admin.py
from django.contrib import admin
from .models import RiskProfile, RiskRule, RiskEvent, RiskMetric, RiskAlert

@admin.register(RiskProfile)
class RiskProfileAdmin(admin.ModelAdmin):
    list_display = ('owner', 'bot', 'name', 'risk_model_type', 'max_drawdown_percent')
    raw_id_fields = ('owner', 'bot', 'risk_agent')

@admin.register(RiskRule)
class RiskRuleAdmin(admin.ModelAdmin):
    list_display = ('profile', 'name', 'rule_type', 'is_active', 'priority')
    list_filter = ('is_active', 'rule_type')
    raw_id_fields = ('profile', 'agent_responsible')

@admin.register(RiskEvent)
class RiskEventAdmin(admin.ModelAdmin):
    list_display = ('profile', 'bot', 'event_type', 'severity', 'message', 'created_at')
    list_filter = ('event_type', 'severity', 'created_at')
    raw_id_fields = ('profile', 'bot', 'agent', 'strategy_version', 'signal', 'order', 'position', 'resolved_by')

@admin.register(RiskMetric)
class RiskMetricAdmin(admin.ModelAdmin):
    list_display = ('profile', 'bot', 'timestamp', 'value_at_risk', 'max_drawdown')
    list_filter = ('timestamp',)
    raw_id_fields = ('profile', 'bot', 'agent')

@admin.register(RiskAlert)
class RiskAlertAdmin(admin.ModelAdmin):
    list_display = ('profile', 'bot', 'alert_type', 'severity', 'title', 'is_acknowledged', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_acknowledged', 'created_at')
    raw_id_fields = ('profile', 'bot', 'agent', 'acknowledged_by')
