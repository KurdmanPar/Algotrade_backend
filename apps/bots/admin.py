# apps/bots/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'instrument', 'bot_type', 'status', 'mode', 'created_at')
    list_filter = ('bot_type', 'status', 'mode', 'control_type')
    search_fields = ('name', 'description', 'owner__email')
    raw_id_fields = ('owner', 'exchange_account', 'instrument', 'risk_profile')
    readonly_fields = ('created_at', 'updated_at', 'last_heartbeat_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'owner', 'instrument', 'bot_type', 'status', 'mode')
        }),
        (_('Configuration'), {
            'classes': ('collapse',),
            'fields': ('control_type', 'max_concurrent_trades', 'max_position_size',
                       'max_total_capital', 'leverage', 'desired_profit_target_percent',
                       'max_allowed_loss_percent', 'trailing_stop_config', 'schedule_config')
        }),
        (_('Risk Management'), {
            'classes': ('collapse',),
            'fields': ('risk_profile',)
        }),
        (_('Paper Trading'), {
            'classes': ('collapse',),
            'fields': ('paper_trading_balance',)
        }),
    )


@admin.register(BotStrategyConfig)
class BotStrategyConfigAdmin(admin.ModelAdmin):
    list_display = ('bot', 'strategy_version', 'primary_strategy', 'weight', 'is_active')
    list_filter = ('primary_strategy', 'is_active')
    search_fields = ('bot__name', 'strategy_version__strategy__name')
    raw_id_fields = ('bot', 'strategy_version')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('bot', 'strategy_version', 'is_primary', 'weight', 'is_active')
        }),
        (_('Configuration'), {
            'classes': ('collapse',),
            'fields': ('parameters_override',)
        }),
    )


@admin.register(BotLog)
class BotLogAdmin(admin.ModelAdmin):
    list_display = ('bot', 'event_type', 'message', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('bot__name', 'message')
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # لاگ‌ها را نمی‌توان دستی اضافه کرد


@admin.register(BotPerformanceSnapshot)
class BotPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('bot', 'period_start', 'period_end', 'total_pnl', 'sharpe_ratio', 'win_rate')
    list_filter = ('period_end',)
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # اسنپ‌شات عملکرد را نمی‌توان دستی اضافه کرد