# apps/connectors/admin.py
from django.contrib import admin
from .models import ExchangeConnectorConfig, APICredential, ExchangeAPIEndpoint, ConnectorSession, RateLimitState, ConnectorLog, ConnectorHealthCheck

@admin.register(ExchangeConnectorConfig)
class ExchangeConnectorConfigAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'api_base_url', 'rate_limit_per_minute', 'is_sandbox_mode_default')
    raw_id_fields = ('exchange',)

@admin.register(APICredential)
class APICredentialAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'is_active', 'last_used_at')
    raw_id_fields = ('exchange_account',)

@admin.register(ExchangeAPIEndpoint)
class ExchangeAPIEndpointAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'endpoint_path', 'method', 'is_sandbox_supported')
    raw_id_fields = ('exchange',)

@admin.register(ConnectorSession)
class ConnectorSessionAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'session_id', 'session_type', 'status', 'connected_at')
    list_filter = ('status', 'session_type')
    raw_id_fields = ('exchange_account',)

@admin.register(RateLimitState)
class RateLimitStateAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'endpoint_path', 'window_start_at', 'requests_count', 'is_rate_limited')
    raw_id_fields = ('exchange_account',)

@admin.register(ConnectorLog)
class ConnectorLogAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'level', 'action', 'status_code', 'created_at')
    list_filter = ('level', 'status_code', 'created_at')
    raw_id_fields = ('exchange_account',)

@admin.register(ConnectorHealthCheck)
class ConnectorHealthCheckAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'is_healthy', 'latency_ms', 'last_check_at')
    list_filter = ('is_healthy', 'last_check_at')
    raw_id_fields = ('exchange_account',)
