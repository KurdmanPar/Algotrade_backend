# apps/bots/admin.py
from django.contrib import admin
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot

@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'instrument', 'bot_type', 'status', 'mode', 'created_at')
    list_filter = ('bot_type', 'status', 'mode', 'control_type')
    raw_id_fields = ('owner', 'exchange_account', 'instrument', 'risk_profile')

@admin.register(BotStrategyConfig)
class BotStrategyConfigAdmin(admin.ModelAdmin):
    list_display = ('bot', 'strategy_version', 'is_primary', 'weight', 'is_active')
    list_filter = ('is_primary', 'is_active')
    raw_id_fields = ('bot', 'strategy_version')

@admin.register(BotLog)
class BotLogAdmin(admin.ModelAdmin):
    list_display = ('bot', 'event_type', 'message', 'created_at')
    list_filter = ('event_type',)
    raw_id_fields = ('bot',)

@admin.register(BotPerformanceSnapshot)
class BotPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('bot', 'period_start', 'period_end', 'total_pnl', 'sharpe_ratio', 'win_rate')
    list_filter = ('period_end',)
    raw_id_fields = ('bot',)
