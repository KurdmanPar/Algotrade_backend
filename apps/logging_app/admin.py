# apps/logging_app/admin.py
from django.contrib import admin
from .models import SystemLog, SystemEvent, NotificationChannel, Alert, UserNotificationPreference, AuditLog

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'source', 'message', 'created_at')
    list_filter = ('level', 'source', 'created_at')
    raw_id_fields = ('user', 'agent', 'bot')

@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('category', 'severity', 'title', 'created_at')
    list_filter = ('category', 'severity', 'created_at')

@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'delivery_method', 'is_active')
    list_filter = ('delivery_method', 'is_active')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'bot', 'type', 'title', 'status', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    raw_id_fields = ('user', 'bot', 'order', 'position', 'signal', 'acknowledged_by')

@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'channel', 'is_enabled')
    raw_id_fields = ('user', 'channel')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at')
    raw_id_fields = ('user',)
