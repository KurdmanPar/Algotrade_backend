# apps/signals/admin.py
from django.contrib import admin
from .models import Signal, SignalLog, SignalAlert

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('user', 'bot', 'instrument', 'direction', 'signal_type', 'status', 'confidence_score', 'generated_at')
    list_filter = ('direction', 'signal_type', 'status', 'generated_at')
    raw_id_fields = ('user', 'bot', 'strategy_version', 'agent', 'exchange_account', 'instrument', 'final_order')

@admin.register(SignalLog)
class SignalLogAdmin(admin.ModelAdmin):
    list_display = ('signal', 'old_status', 'new_status', 'created_at')
    list_filter = ('new_status', 'created_at')
    raw_id_fields = ('signal', 'changed_by_agent', 'changed_by_user')

@admin.register(SignalAlert)
class SignalAlertAdmin(admin.ModelAdmin):
    list_display = ('signal', 'alert_type', 'severity', 'title', 'is_acknowledged', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_acknowledged', 'created_at')
    raw_id_fields = ('signal', 'acknowledged_by')
