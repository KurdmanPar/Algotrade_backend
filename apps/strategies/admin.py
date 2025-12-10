# apps/strategies/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Strategy, StrategyVersion, StrategyAssignment


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    """
    پنل ادمین برای مدیریت استراتژی‌ها.
    """
    list_display = (
        'name',
        'owner',
        'category',
        'is_active',
        'created_at'
    )
    list_filter = (
        'category',
        'is_active',
        'created_at'
    )
    search_fields = (
        'name',
        'description',
        'owner__email'
    )
    raw_id_fields = ('owner',)

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'description',
                'owner',
                'category',
                'is_active'
            )
        }),
        (_('Advanced Options'), {
            'classes': ('collapse',),
            'fields': ()
        }),
    )


@admin.register(StrategyVersion)
class StrategyVersionAdmin(admin.ModelAdmin):
    """
    پنل ادمین برای مدیریت نسخه‌های استراتژی.
    """
    list_display = (
        'strategy',
        'version',
        'is_approved_for_live',
        'created_at'
    )
    list_filter = (
        'is_approved_for_live',
        'created_at'
    )
    search_fields = (
        'strategy__name',
        'version'
    )
    raw_id_fields = ('strategy',)

    fieldsets = (
        (None, {
            'fields': (
                'strategy',
                'version',
                'is_approved_for_live'
            )
        }),
        (_('Configuration'), {
            'classes': ('collapse',),
            'fields': (
                'parameters_schema',
                'indicator_configs',
                'price_action_configs',
                'smart_money_configs',
                'ai_metrics_configs'
            )
        }),
    )


@admin.register(StrategyAssignment)
class StrategyAssignmentAdmin(admin.ModelAdmin):
    """
    پنل ادمین برای مدیریت تخصیص استراتژی‌ها به بات‌ها.
    """
    list_display = (
        'bot',
        'strategy_version',
        'weight',
        'priority',
        'is_active',
        'created_at'
    )
    list_filter = (
        'is_active',
        'priority'
    )
    search_fields = (
        'bot__name',
        'strategy_version__strategy__name'
    )
    raw_id_fields = (
        'bot',
        'strategy_version'
    )
    readonly_fields = (
        'created_at',
        'updated_at'
    )

    fieldsets = (
        (None, {
            'fields': (
                'bot',
                'strategy_version',
                'weight',
                'priority',
                'is_active'
            )
        }),
        (_('Configuration'), {
            'classes': ('collapse',),
            'fields': (
                'parameters_override'
            )
        }),
    )